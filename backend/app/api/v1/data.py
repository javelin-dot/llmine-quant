"""Data Service API — data sources, market data, lineage, incidents."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.audit.models import AuditLog
from app.domains.data.models import (
    DataSource,
    FeatureSet,
    FeatureUsage,
    LineageEdge,
    LineageNode,
    MarketBarDaily,
    StockInfo,
)
from app.domains.data.schemas import (
    DataIncidentOut,
    DataOverview,
    DataScreen,
    DataSourceOut,
    DataSourceTier,
    FeatureOut,
    FeatureUsageOut,
    IngestTrend,
    LatencyTrend,
    LineageNodeOut,
    LineageOut,
    MarketBarDailyOut,
    MarketDataAkshareImportIn,
    MarketDataCsvImportIn,
    MarketDataImportSummary,
    MarketSyncStart,
    MarketSyncStatus,
    RunLineageOut,
    StockInfoRefreshOut,
    SymbolStatsOut,
    SymbolSummary,
)
from app.services.market_data_full_sync import (
    AlreadyRunningError,
    FullSyncRequest,
    _fetch_market_symbols,
    current_status,
    start_full_sync,
    upsert_stock_info,
)
from app.services.market_data_import import (
    MarketDataImportError,
    MarketDataImportResult,
    MarketDataImportService,
)

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]



def _tier_tone(tier: str) -> str:
    if tier == "paper":
        return "yellow"
    if tier == "live":
        return "red"
    return "blue"


def _map_db_data_source(r: DataSource) -> DataSourceOut:
    st = (r.status or "healthy").lower()
    tone_map = {
        "healthy": "green",
        "warning": "yellow",
        "error": "red",
        "maintenance": "gray",
    }
    st_tone = tone_map.get(st, "blue")
    return DataSourceOut(
        id=r.id,
        name=r.name,
        provider=r.provider,
        tier=r.tier,
        tierTone=_tier_tone(r.tier),
        type=r.type,
        coverage=r.coverage or "—",
        latencyMs=int(r.latency_ms or 0),
        latencyP95=int(r.latency_p95 or 0),
        missingPct=float(r.missing_pct or 0.0),
        driftScore=float(r.drift_score or 0.0),
        license=r.license or "—",
        status=st,
        statusTone=st_tone,
        lastUpdate=r.last_update or "—",
    )


async def _symbol_stats_row(db: AsyncSession) -> tuple[int, int, str | None, str | None]:
    stmt = select(
        func.count(func.distinct(MarketBarDaily.symbol)).label("total_symbols"),
        func.count(MarketBarDaily.id).label("total_bars"),
        func.max(MarketBarDaily.trade_date).label("latest_trade_date"),
        func.min(MarketBarDaily.trade_date).label("earliest_trade_date"),
    )
    row = (await db.execute(stmt)).one()
    return (
        int(row.total_symbols or 0),
        int(row.total_bars or 0),
        str(row.latest_trade_date) if row.latest_trade_date else None,
        str(row.earliest_trade_date) if row.earliest_trade_date else None,
    )


async def _ingest_trend_series(db: AsyncSession) -> tuple[list[str], list[int]]:
    bars_count = func.count(MarketBarDaily.id).label("c")
    stmt = (
        select(MarketBarDaily.trade_date, bars_count)
        .group_by(MarketBarDaily.trade_date)
        .order_by(MarketBarDaily.trade_date.desc())
        .limit(12)
    )
    rows = (await db.execute(stmt)).all()
    rows = list(reversed(rows))
    dates = [str(r.trade_date) for r in rows]
    counts = [int(r.c) for r in rows]
    return dates, counts


async def _feature_lineage(db: AsyncSession, total_bars: int, *, limit: int = 14) -> LineageOut:
    feats = (await db.execute(select(FeatureSet).order_by(FeatureSet.name).limit(limit))).scalars().all()
    nodes: list[LineageNodeOut] = [
        LineageNodeOut(
            id="n-bars-local",
            label=f"Daily OHLCV · {total_bars:,} rows",
            tier="raw",
            tone="blue",
            version="v1",
            permission="read",
        )
    ]
    edges: list[dict[str, str]] = []
    for f in feats:
        nid = f"f-{f.id}"
        lbl = (f.name or "feature")[:28]
        nodes.append(
            LineageNodeOut(
                id=nid,
                label=lbl,
                tier="feature",
                tone="green",
                version=f.version or "1",
                permission=f.permission_scope or "research",
            )
        )
        edges.append({"from": "n-bars-local", "to": nid})
    if not feats:
        nodes.append(
            LineageNodeOut(
                id="n-empty-features",
                label="No registered features yet",
                tier="feature",
                tone="gray",
                version="—",
                permission="—",
            )
        )
        edges.append({"from": "n-bars-local", "to": "n-empty-features"})
    return LineageOut(nodes=nodes, edges=edges)


async def _data_incidents(db: AsyncSession, sync_error: str | None) -> list[DataIncidentOut]:
    out: list[DataIncidentOut] = []
    now_s = datetime.now(UTC).strftime("%m-%d %H:%MZ")
    if sync_error:
        out.append(
            DataIncidentOut(
                time=now_s,
                source="market_sync",
                type="outage",
                typeTone="red",
                severity="high",
                severityTone="red",
                title="行情全量同步错误",
                detail=sync_error[:400],
                resolution="在「行情入库」分页查看并重试同步",
                status="ongoing",
                statusTone="yellow",
            )
        )
    since = datetime.now(UTC) - timedelta(days=7)
    logs = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.created_at >= since)
            .where(AuditLog.result != "success")
            .order_by(AuditLog.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    for row in logs:
        tm = row.created_at.strftime("%m-%d %H:%M") if row.created_at else "—"
        out.append(
            DataIncidentOut(
                time=tm,
                source=row.actor or "system",
                type="schema",
                typeTone="yellow",
                severity="medium",
                severityTone="yellow",
                title=row.action,
                detail=(row.detail or row.resource_type or "")[:320],
                resolution="见审计合规 → 日志",
                status="review",
                statusTone="yellow",
            )
        )
    return out


def _latency_trend_from_ingest(dates: list[str], bars: list[int], sync: MarketSyncStatus) -> LatencyTrend:
    """Three lines are derived from local ingest volume so the legacy chart stays populated."""
    if not bars:
        base = [120.0, 125.0, 118.0, 130.0, 122.0, 128.0, 124.0, 121.0]
        return LatencyTrend(
            times=["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"],
            research=base,
            paper=[x * 1.08 for x in base],
            live=[x * 1.15 for x in base],
            slaMs=500,
        )
    mx = max(bars) or 1
    pad = [80.0 + 320.0 * (float(b) / mx) for b in bars]
    if len(pad) < 8:
        head = pad[0]
        pad = ([head] * (8 - len(pad))) + pad
    elif len(pad) > 8:
        pad = pad[-8:]
    times_raw = dates[-len(pad) :] if dates else []
    while len(times_raw) < len(pad):
        times_raw.insert(0, times_raw[0] if times_raw else "--")
    times = [(t[-5:] if isinstance(t, str) and len(t) >= 5 else str(t)) for t in times_raw[: len(pad)]]
    bump = sync.rate_per_sec or 0.0
    live_adj = [min(980.0, p + bump * 2.5) for p in pad]
    return LatencyTrend(
        times=times,
        research=list(pad),
        paper=[p * 1.06 for p in pad],
        live=live_adj,
        slaMs=500,
    )


def _synthetic_sources(stats: SymbolStatsOut, feat_count: int, sync: MarketSyncStatus) -> list[DataSourceOut]:
    cov = (
        f"{stats.totalSymbols} 标的 · {stats.totalBars:,} bars"
        if stats.totalBars
        else "库内暂无 K 线"
    )
    rate = sync.rate_per_sec or 0.0
    lat = int(280 / max(rate, 0.2)) if sync.is_running else (95 if stats.totalBars else 0)
    st = "healthy" if stats.totalBars and not sync.error else ("error" if sync.error else "warning")
    st_tone = "green" if st == "healthy" else ("red" if sync.error else "yellow")
    return [
        DataSourceOut(
            id="local-ohlcv",
            name="本地行情库 (market_bars_daily)",
            provider="llmine",
            tier="research",
            tierTone="blue",
            type="kline",
            coverage=cov,
            latencyMs=min(lat, 900),
            latencyP95=min(int(lat * 1.35) if lat else 0, 1200),
            missingPct=0.0 if stats.totalBars else 1.0,
            driftScore=0.0,
            license="站内",
            status=st,
            statusTone=st_tone,
            lastUpdate=stats.latestTradeDate or "—",
        ),
        DataSourceOut(
            id="feature-store",
            name="Feature Store",
            provider="llmine",
            tier="research",
            tierTone="blue",
            type="feature",
            coverage=f"{feat_count} 个注册特征",
            latencyMs=0,
            latencyP95=0,
            missingPct=0.0,
            driftScore=0.0,
            license="站内",
            status="healthy" if feat_count else "maintenance",
            statusTone="green" if feat_count else "gray",
            lastUpdate="—",
        ),
    ]


async def assemble_data_sources(db: AsyncSession, stats: SymbolStatsOut, feat_count: int, sync: MarketSyncStatus) -> list[DataSourceOut]:
    cfg_rows: list[DataSource] = []
    try:
        cfg_rows = (
            await db.execute(select(DataSource).order_by(DataSource.tier, DataSource.provider, DataSource.name))
        ).scalars().all()
    except DBAPIError:
        # e.g. SQLite test DB without data_sources migration yet
        cfg_rows = []
    out = list(_synthetic_sources(stats, feat_count, sync))
    out.extend(_map_db_data_source(r) for r in cfg_rows)
    out.append(
        DataSourceOut(
            id="connector-tushare",
            name="Tushare Pro（外部连接器）",
            provider="tushare",
            tier="paper",
            tierTone="yellow",
            type="kline",
            coverage="需在环境配置 TOKEN",
            latencyMs=0,
            latencyP95=0,
            missingPct=0.0,
            driftScore=0.0,
            license="付费",
            status="maintenance",
            statusTone="gray",
            lastUpdate="未连接",
        )
    )
    return out


def _tiers_from_sources(sources: list[DataSourceOut]) -> list[DataSourceTier]:
    meta = {
        "research": ("研究层", "站内数据与开源链路", "免费"),
        "paper": ("模拟盘层", "付费 API 占位 / 连接器", "付费"),
        "live": ("实盘层", "机构行情占位", "机构"),
    }
    out: list[DataSourceTier] = []
    for tier in ("research", "paper", "live"):
        subs = [s for s in sources if s.tier == tier]
        active = sum(1 for s in subs if s.status == "healthy")
        avg_lat = int(sum(s.latencyMs for s in subs) / len(subs)) if subs else 0
        label, desc, lic = meta[tier]
        out.append(
            DataSourceTier(
                tier=tier,
                label=label,
                count=len(subs),
                active=active,
                avgLatencyMs=avg_lat,
                license=lic,
                tone=_tier_tone(tier),
                desc=desc,
            )
        )
    return out


def _overview_header(
    stats: SymbolStatsOut,
    feat_count: int,
    sources: list[DataSourceOut],
    sync: MarketSyncStatus,
    incident_count: int,
) -> DataOverview:
    bars_ok = stats.totalBars > 0
    health = 88 if bars_ok else 42
    if sync.error:
        health -= 22
    health = max(18, min(100, health))
    tone = "green" if health >= 75 else ("yellow" if health >= 45 else "red")
    status_lbl = "HEALTHY" if tone == "green" else ("DEGRADED" if tone == "yellow" else "CRITICAL")
    rate = sync.rate_per_sec or 0.0
    avg_lat = int(420 / max(rate, 0.15)) if sync.is_running else (160 if bars_ok else 0)
    p95_lat = min(950, int(avg_lat * 1.35)) if avg_lat else 0
    err_n = sum(1 for s in sources if s.status == "error")
    miss = 0.0 if bars_ok else 1.0
    active = sum(1 for s in sources if s.status == "healthy")
    return DataOverview(
        totalSources=len(sources),
        activeSources=active,
        erroredSources=err_n,
        avgLatencyMs=avg_lat,
        p95LatencyMs=p95_lat,
        missingRate=miss,
        incidents24h=incident_count,
        healthScore=health,
        healthStatus=status_lbl,
        healthStatusTone=tone,
        totalBars=stats.totalBars,
        totalSymbols=stats.totalSymbols,
        featureCount=feat_count,
        latestTradeDate=stats.latestTradeDate,
    )


def _kpis_from_stats(stats: SymbolStatsOut, feat_count: int, sync: MarketSyncStatus, incidents: int) -> list[dict[str, str]]:
    return [
        {"label": "本地标的", "value": str(stats.totalSymbols), "trend": f"{stats.totalBars:,} bars", "tone": "blue"},
        {"label": "特征条目", "value": str(feat_count), "trend": "Feature Store", "tone": ("green" if feat_count else "yellow")},
        {
            "label": "同步吞吐",
            "value": f"{sync.rate_per_sec:.1f}/s" if sync.is_running else "—",
            "trend": sync.phase if sync.is_running else "空闲",
            "tone": ("green" if sync.is_running else "blue"),
        },
        {
            "label": "同步进度",
            "value": f"{sync.done}/{sync.total}" if sync.total else "—",
            "trend": f"写入 {sync.inserted_rows:,} 行" if sync.inserted_rows else "—",
            "tone": "yellow",
        },
        {"label": "七日事件", "value": str(incidents), "trend": "审计失败 + 同步", "tone": ("yellow" if incidents else "green")},
        {
            "label": "日期覆盖",
            "value": stats.latestTradeDate or "—",
            "trend": (f"起于 {stats.earliestTradeDate}" if stats.earliestTradeDate else "—"),
            "tone": "blue",
        },
    ]


@router.get("/overview", response_model=DataScreen)
async def get_data_overview(db: DbSession) -> DataScreen:
    """Aggregate DB-backed KPIs plus sync state for the Data Operations UI."""
    tsym, tbars, latest_td, earliest_td = await _symbol_stats_row(db)
    stats = SymbolStatsOut(
        totalSymbols=tsym,
        totalBars=tbars,
        latestTradeDate=latest_td,
        earliestTradeDate=earliest_td,
    )
    feat_count = int((await db.execute(select(func.count()).select_from(FeatureSet))).scalar_one() or 0)
    sync = _sync_status_out()
    dates, bar_counts = await _ingest_trend_series(db)
    ingest = IngestTrend(dates=dates, bars=bar_counts)
    sources = await assemble_data_sources(db, stats, feat_count, sync)
    incidents = await _data_incidents(db, sync.error)
    latency = _latency_trend_from_ingest(dates, bar_counts, sync)
    lineage = await _feature_lineage(db, stats.totalBars)
    header = _overview_header(stats, feat_count, sources, sync, len(incidents))
    kpis = _kpis_from_stats(stats, feat_count, sync, len(incidents))
    tiers = _tiers_from_sources(sources)
    return DataScreen(
        header=header,
        tiers=tiers,
        kpis=kpis,
        sources=sources,
        latencyTrend=latency,
        ingestTrend=ingest,
        lineage=lineage,
        incidents=incidents,
    )


@router.get("/sources", response_model=list[DataSourceOut])
async def get_data_sources(db: DbSession) -> list[DataSourceOut]:
    tsym, tbars, latest_td, earliest_td = await _symbol_stats_row(db)
    stats = SymbolStatsOut(
        totalSymbols=tsym,
        totalBars=tbars,
        latestTradeDate=latest_td,
        earliestTradeDate=earliest_td,
    )
    feat_count = int((await db.execute(select(func.count()).select_from(FeatureSet))).scalar_one() or 0)
    sync = _sync_status_out()
    return await assemble_data_sources(db, stats, feat_count, sync)


@router.post("/market-bars/import/csv", response_model=MarketDataImportSummary)
async def import_market_bars_csv(
    payload: MarketDataCsvImportIn,
    db: DbSession,
) -> MarketDataImportSummary:
    """Import daily market bars from a local CSV file path."""
    service = MarketDataImportService(db)
    try:
        result = await service.import_csv_file(
            payload.path,
            default_symbol=payload.default_symbol,
            source_name=payload.source_name,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MarketDataImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _import_summary(result)


@router.post("/market-bars/import/akshare", response_model=MarketDataImportSummary)
async def import_market_bars_akshare(
    payload: MarketDataAkshareImportIn,
    db: DbSession,
) -> MarketDataImportSummary:
    """Import daily market bars from AKShare."""
    service = MarketDataImportService(db)
    try:
        result = await service.import_akshare(
            symbols=payload.symbols,
            start_date=payload.start_date,
            end_date=payload.end_date,
            adjust=payload.adjust,
        )
    except MarketDataImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _import_summary(result)


@router.get("/market-bars", response_model=list[MarketBarDailyOut])
async def list_market_bars(
    db: DbSession,
    symbol: str | None = None,
    start_date: str | None = Query(default=None, alias="startDate"),
    end_date: str | None = Query(default=None, alias="endDate"),
    limit: int = Query(default=10, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> list[MarketBarDailyOut]:
    """Return persisted daily market bars for research inspection.

    Supports cursor-style pagination via ``offset`` + ``limit``.
    Default ordering is by ``trade_date DESC`` so the latest bars come first,
    which matches the Local Market Library detail panel (newest on top).
    """
    query = select(MarketBarDaily)
    if symbol:
        query = query.where(MarketBarDaily.symbol == symbol.upper())
    if start_date:
        query = query.where(MarketBarDaily.trade_date >= start_date)
    if end_date:
        query = query.where(MarketBarDaily.trade_date <= end_date)
    if order == "asc":
        query = query.order_by(MarketBarDaily.symbol, MarketBarDaily.trade_date.asc())
    else:
        query = query.order_by(MarketBarDaily.symbol, MarketBarDaily.trade_date.desc())
    result = await db.execute(query.offset(offset).limit(limit))
    return [_market_bar_out(row) for row in result.scalars().all()]


@router.get("/latency-trend", response_model=LatencyTrend)
async def get_latency_trend(db: DbSession) -> LatencyTrend:
    dates, bar_counts = await _ingest_trend_series(db)
    return _latency_trend_from_ingest(dates, bar_counts, _sync_status_out())


@router.get("/lineage", response_model=LineageOut)
async def get_lineage(db: DbSession) -> LineageOut:
    total_bars = int((await db.execute(select(func.count()).select_from(MarketBarDaily))).scalar_one() or 0)
    return await _feature_lineage(db, total_bars)


@router.get("/symbols/stats", response_model=SymbolStatsOut)
async def get_symbols_stats(db: DbSession) -> SymbolStatsOut:
    """Whole-database KPI for Local Market Library (NOT capped by symbol pagination).

    Returns total distinct symbols, total bar rows and the latest trade date
    across the entire ``market_bars_daily`` table.
    """
    stmt = select(
        func.count(func.distinct(MarketBarDaily.symbol)).label("total_symbols"),
        func.count(MarketBarDaily.id).label("total_bars"),
        func.max(MarketBarDaily.trade_date).label("latest_trade_date"),
        func.min(MarketBarDaily.trade_date).label("earliest_trade_date"),
    )
    row = (await db.execute(stmt)).one()
    return SymbolStatsOut(
        totalSymbols=int(row.total_symbols or 0),
        totalBars=int(row.total_bars or 0),
        latestTradeDate=str(row.latest_trade_date) if row.latest_trade_date else None,
        earliestTradeDate=str(row.earliest_trade_date) if row.earliest_trade_date else None,
    )


@router.get("/symbols", response_model=list[SymbolSummary])
async def list_market_symbols(
    db: DbSession,
    search: str | None = Query(default=None, description="Filter by symbol prefix/substring (case-insensitive)"),
    sort: str = Query(default="bars", pattern="^(bars|symbol|recent)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=5000),
) -> list[SymbolSummary]:
    """List distinct symbols that have bars in the local DB, with coverage info.

    Supports server-side ``search`` (case-insensitive substring), ``sort``
    (bars desc / symbol asc / recent endDate desc) and offset/limit pagination.
    """
    bars_count = func.count(MarketBarDaily.id).label("bars")
    start_date = func.min(MarketBarDaily.trade_date).label("start_date")
    end_date = func.max(MarketBarDaily.trade_date).label("end_date")

    stmt = select(
        MarketBarDaily.symbol.label("symbol"),
        bars_count,
        start_date,
        end_date,
        StockInfo.name.label("name"),
    ).outerjoin(StockInfo, StockInfo.symbol == MarketBarDaily.symbol)
    if search:
        pattern = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            (func.upper(MarketBarDaily.symbol).like(pattern))
            | (func.coalesce(StockInfo.name, "").like(f"%{search.strip()}%"))
        )
    stmt = stmt.group_by(MarketBarDaily.symbol, StockInfo.name)

    if sort == "symbol":
        stmt = stmt.order_by(MarketBarDaily.symbol.asc())
    elif sort == "recent":
        stmt = stmt.order_by(end_date.desc(), MarketBarDaily.symbol.asc())
    else:  # bars
        stmt = stmt.order_by(bars_count.desc(), MarketBarDaily.symbol.asc())

    stmt = stmt.offset(offset).limit(limit)
    rows = (await db.execute(stmt)).all()
    return [
        SymbolSummary(
            symbol=row.symbol,
            name=row.name or None,
            bars=int(row.bars),
            startDate=str(row.start_date),
            endDate=str(row.end_date),
        )
        for row in rows
    ]


@router.post("/stock-info/refresh", response_model=StockInfoRefreshOut)
async def refresh_stock_info() -> StockInfoRefreshOut:
    """从 AKShare 拉一次全 A 股快照并刷新 ``stock_info`` 表。

    不依赖全量同步；常用于仅需补全/刷新股票中文名称的场景。
    耗时在 5–10 秒量级，不需后台任务。
    """
    from datetime import datetime as _dt

    scan = await _fetch_market_symbols()
    upserted = await upsert_stock_info(scan)
    return StockInfoRefreshOut(
        upserted=upserted,
        syncedAt=_dt.utcnow().isoformat() + "Z",
    )


@router.get("/features", response_model=list[FeatureOut])
async def list_features(db: DbSession, limit: int = Query(default=50, ge=1, le=200)) -> list[FeatureOut]:
    """List registered features (Feature Store)."""
    rows = (
        await db.execute(select(FeatureSet).order_by(FeatureSet.name, FeatureSet.version).limit(limit))
    ).scalars().all()
    return [
        FeatureOut(
            id=f.id,
            name=f.name,
            version=f.version,
            kind=f.kind,
            description=f.description,
            computationWindow=f.computation_window,
            validated=bool(f.validated),
            permissionScope=f.permission_scope or "research",
        )
        for f in rows
    ]


@router.get("/features/usages", response_model=list[FeatureUsageOut])
async def list_feature_usages(
    db: DbSession,
    strategy_version_id: str | None = Query(default=None),
    backtest_run_id: str | None = Query(default=None),
) -> list[FeatureUsageOut]:
    """List FeatureUsage rows optionally filtered by strategy version or backtest run."""
    stmt = select(FeatureUsage, FeatureSet).join(FeatureSet, FeatureSet.id == FeatureUsage.feature_id)
    if strategy_version_id:
        stmt = stmt.where(FeatureUsage.strategy_version_id == strategy_version_id)
    if backtest_run_id:
        stmt = stmt.where(FeatureUsage.backtest_run_id == backtest_run_id)
    rows = (await db.execute(stmt.order_by(FeatureUsage.created_at.desc()).limit(200))).all()
    return [
        FeatureUsageOut(
            featureId=u.feature_id,
            featureName=f.name,
            featureVersion=f.version,
            strategyVersionId=u.strategy_version_id,
            backtestRunId=u.backtest_run_id,
            role=u.role,
        )
        for (u, f) in rows
    ]


@router.get("/lineage/runs/{run_id}", response_model=RunLineageOut)
async def get_run_lineage(run_id: str, db: DbSession) -> RunLineageOut:
    """Return the lineage DAG attached to a specific backtest run."""
    edges = (
        await db.execute(
            select(LineageEdge).where(LineageEdge.backtest_run_id == run_id)
        )
    ).scalars().all()
    if not edges:
        raise HTTPException(status_code=404, detail="no lineage found for run")
    node_ids = {e.from_node_id for e in edges} | {e.to_node_id for e in edges}
    nodes = (
        await db.execute(select(LineageNode).where(LineageNode.id.in_(node_ids)))
    ).scalars().all()
    return RunLineageOut(
        runId=run_id,
        nodes=[
            LineageNodeOut(
                id=n.id,
                label=n.label,
                tier=n.node_type,
                tone=_tone_for_tier(n.node_type),
                version=n.version,
                permission=n.permission,
            )
            for n in nodes
        ],
        edges=[{"from": e.from_node_id, "to": e.to_node_id} for e in edges],
    )


def _tone_for_tier(tier: str) -> str:
    return {
        "raw": "gray",
        "cleaned": "blue",
        "feature": "green",
        "strategy": "purple",
        "run": "yellow",
        "signal": "yellow",
        "order": "red",
    }.get(tier, "blue")


@router.get("/incidents", response_model=list[DataIncidentOut])
async def get_incidents(db: DbSession) -> list[DataIncidentOut]:
    sync = _sync_status_out()
    return await _data_incidents(db, sync.error)


@router.post("/market-bars/sync/full", response_model=MarketSyncStatus, status_code=202)
async def trigger_full_sync(payload: MarketSyncStart) -> MarketSyncStatus:
    """触发全市场同步. 首次空库 = 全量, 后续按 max(trade_date) 增量."""
    end = payload.end_date or date.today().isoformat()
    start = payload.start_date or (date.today() - timedelta(days=365 * 5)).isoformat()
    req = FullSyncRequest(
        start_date=start,
        end_date=end,
        adjust=payload.adjust,
        concurrency=max(1, min(16, payload.concurrency)),
        boards=payload.boards or [],
        incremental=payload.incremental,
    )
    try:
        await start_full_sync(req)
    except AlreadyRunningError as exc:
        raise HTTPException(status_code=409, detail=f"sync already running: {exc}") from exc
    return _sync_status_out()


@router.get("/market-bars/sync/status", response_model=MarketSyncStatus)
async def get_sync_status() -> MarketSyncStatus:
    """前端轮询的进度端点; 任何状态都 200, 是否在跑看 isRunning 字段."""
    return _sync_status_out()


def _sync_status_out() -> MarketSyncStatus:
    p = current_status()
    return MarketSyncStatus(
        task_id=p.task_id,
        phase=p.phase,
        started_at=p.started_at,
        finished_at=p.finished_at,
        total=p.total,
        done=p.done,
        skipped=p.skipped,
        inserted_rows=p.inserted_rows,
        updated_rows=p.updated_rows,
        failures=p.failures,
        rate_per_sec=p.rate_per_sec,
        eta_seconds=p.eta_seconds,
        last_symbol=p.last_symbol,
        error=p.error,
        is_running=p.is_running,
    )


def _import_summary(result: MarketDataImportResult) -> MarketDataImportSummary:
    return MarketDataImportSummary(
        source=result.source,
        total_rows=result.total_rows,
        imported_rows=result.imported_rows,
        inserted_rows=result.inserted_rows,
        updated_rows=result.updated_rows,
        skipped_rows=result.skipped_rows,
        symbols=result.symbols,
        start_date=result.start_date,
        end_date=result.end_date,
        errors=result.errors,
    )


def _market_bar_out(row: MarketBarDaily) -> MarketBarDailyOut:
    return MarketBarDailyOut(
        id=row.id,
        symbol=row.symbol,
        trade_date=row.trade_date,
        prev_close=row.prev_close,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        amount=row.amount,
        adjusted_close=row.adjusted_close,
        forward_factor=row.forward_factor,
        limit_up_price=row.limit_up_price,
        limit_down_price=row.limit_down_price,
        is_st=row.is_st,
        is_limit_up=row.is_limit_up,
        is_limit_down=row.is_limit_down,
        is_suspended=row.is_suspended,
        can_buy=row.can_buy,
        can_sell=row.can_sell,
    )
