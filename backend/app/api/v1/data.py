"""Data Service API — data sources, market data, lineage, incidents."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.data.models import (
    FeatureSet,
    FeatureUsage,
    LineageEdge,
    LineageNode,
    MarketBarDaily,
)
from app.domains.data.schemas import (
    BiasGate,
    DataIncidentOut,
    DataOverview,
    DataScreen,
    DataSourceOut,
    DataSourceTier,
    FeatureOut,
    FeatureUsageOut,
    LatencyTrend,
    LineageNodeOut,
    LineageOut,
    MarketBarDailyOut,
    MarketDataAkshareImportIn,
    MarketDataCsvImportIn,
    MarketDataImportSummary,
    RunLineageOut,
)
from app.services.market_data_import import (
    MarketDataImportError,
    MarketDataImportResult,
    MarketDataImportService,
)

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


_HEADER = DataOverview(
    totalSources=12,
    activeSources=10,
    erroredSources=2,
    avgLatencyMs=180,
    p95LatencyMs=420,
    missingRate=0.0008,
    incidents24h=1,
    healthScore=88,
    healthStatus="HEALTHY",
    healthStatusTone="green",
)

_TIERS = [
    DataSourceTier(tier="research", label="研究层", count=6, active=5, avgLatencyMs=150, license="免费", tone="blue", desc="AKShare / Baostock 基础行情"),
    DataSourceTier(tier="paper", label="模拟盘层", count=4, active=4, avgLatencyMs=200, license="付费", tone="yellow", desc="Tushare Pro 增强数据"),
    DataSourceTier(tier="live", label="实盘层", count=2, active=1, avgLatencyMs=300, license="机构", tone="red", desc="Wind / 券商直连"),
]

_SOURCES = [
    DataSourceOut(
        id="ds-001", name="AKShare 日线", provider="akshare", tier="research", tierTone="blue",
        type="kline", coverage="沪深A股", latencyMs=120, latencyP95=350, missingPct=0.001,
        driftScore=0.02, license="免费", status="healthy", statusTone="green", lastUpdate="2 min ago"
    ),
    DataSourceOut(
        id="ds-002", name="Tushare Pro 日线", provider="tushare", tier="paper", tierTone="yellow",
        type="kline", coverage="沪深A股+科创板", latencyMs=180, latencyP95=420, missingPct=0.0005,
        driftScore=0.01, license="付费", status="healthy", statusTone="green", lastUpdate="1 min ago"
    ),
    DataSourceOut(
        id="ds-003", name="Wind 机构数据", provider="wind", tier="live", tierTone="red",
        type="kline", coverage="全市场", latencyMs=280, latencyP95=520, missingPct=0.0002,
        driftScore=0.01, license="机构", status="warning", statusTone="yellow", lastUpdate="5 min ago"
    ),
    DataSourceOut(
        id="ds-004", name="AKShare 财务数据", provider="akshare", tier="research", tierTone="blue",
        type="fundamental", coverage="沪深A股", latencyMs=200, latencyP95=600, missingPct=0.002,
        driftScore=0.03, license="免费", status="healthy", statusTone="green", lastUpdate="10 min ago"
    ),
]

_LATENCY_TREND = LatencyTrend(
    times=["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"],
    research=[120, 130, 125, 140, 135, 150, 145, 130],
    paper=[180, 200, 190, 210, 205, 220, 215, 195],
    live=[280, 300, 290, 310, 305, 320, 315, 295],
    slaMs=500,
)

_BIAS_GATES = [
    BiasGate(title="未来函数检测", desc="检查特征计算是否使用未来数据", status="pass", statusTone="green", lastCheck="10 min ago", note="无异常"),
    BiasGate(title="幸存者偏差", desc="检查是否排除已退市股票", status="pass", statusTone="green", lastCheck="15 min ago", note="ST/退市标记完整"),
    BiasGate(title="数据完整性", desc="检查关键字段缺失率", status="pass", statusTone="green", lastCheck="5 min ago", note="缺失率 < 0.1%"),
    BiasGate(title="数据及时性", desc="检查行情延迟是否在 SLA 内", status="watch", statusTone="yellow", lastCheck="1 min ago", note="Wind 数据源延迟偏高"),
    BiasGate(title="数据一致性", desc="交叉验证多源数据一致性", status="pass", statusTone="green", lastCheck="20 min ago", note="偏差 < 0.1%"),
]

_LINEAGE = LineageOut(
    nodes=[
        LineageNodeOut(id="n1", label="AKShare Raw", tier="raw", tone="blue", version="v2.1.0", permission="read"),
        LineageNodeOut(id="n2", label="Cleaned Bars", tier="raw", tone="blue", version="v1.3.0", permission="read"),
        LineageNodeOut(id="n3", label="Feature Set", tier="feature", tone="green", version="v4.2.0", permission="read"),
        LineageNodeOut(id="n4", label="MA Strategy", tier="model", tone="purple", version="v1.0.0", permission="execute"),
        LineageNodeOut(id="n5", label="Signal", tier="signal", tone="yellow", version="v1.0.0", permission="read"),
        LineageNodeOut(id="n6", label="Order Draft", tier="order", tone="red", version="v1.0.0", permission="write"),
    ],
    edges=[{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}, {"from": "n4", "to": "n5"}, {"from": "n5", "to": "n6"}],
)

_INCIDENTS = [
    DataIncidentOut(
        time="09:15", source="Wind 机构数据", type="latency", typeTone="yellow",
        severity="medium", severityTone="yellow", title="Wind API 延迟升高",
        detail="P95 延迟达到 520ms，超出 SLA 阈值 500ms", resolution="已通知 Wind 技术支持",
        status="ongoing", statusTone="yellow"
    ),
]

_KPIS = [
    {"label": "数据源", "value": "12", "trend": "+1", "tone": "blue"},
    {"label": "P95 延迟", "value": "420ms", "trend": "+15%", "tone": "yellow"},
    {"label": "缺失率", "value": "0.08%", "trend": "-0.02%", "tone": "green"},
    {"label": "漂移分", "value": "0.02", "trend": "+0.01", "tone": "green"},
    {"label": "事件", "value": "1", "trend": "+1", "tone": "yellow"},
]


@router.get("/overview", response_model=DataScreen)
async def get_data_overview(db: DbSession) -> DataScreen:
    """Return the complete Data Operations screen data."""
    return DataScreen(
        header=_HEADER,
        tiers=_TIERS,
        kpis=_KPIS,
        sources=_SOURCES,
        latencyTrend=_LATENCY_TREND,
        biasGate=_BIAS_GATES,
        lineage=_LINEAGE,
        incidents=_INCIDENTS,
    )


@router.get("/sources", response_model=list[DataSourceOut])
async def get_data_sources(db: DbSession) -> list[DataSourceOut]:
    """Return all data sources."""
    return _SOURCES


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
    limit: int = Query(default=1000, ge=1, le=5000),
) -> list[MarketBarDailyOut]:
    """Return persisted daily market bars for research inspection."""
    query = select(MarketBarDaily)
    if symbol:
        query = query.where(MarketBarDaily.symbol == symbol.upper())
    if start_date:
        query = query.where(MarketBarDaily.trade_date >= start_date)
    if end_date:
        query = query.where(MarketBarDaily.trade_date <= end_date)
    result = await db.execute(query.order_by(MarketBarDaily.symbol, MarketBarDaily.trade_date).limit(limit))
    return [_market_bar_out(row) for row in result.scalars().all()]


@router.get("/latency-trend", response_model=LatencyTrend)
async def get_latency_trend() -> LatencyTrend:
    """Return latency trend data."""
    return _LATENCY_TREND


@router.get("/lineage", response_model=LineageOut)
async def get_lineage() -> LineageOut:
    """Return data lineage DAG."""
    return _LINEAGE


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
async def get_incidents() -> list[DataIncidentOut]:
    """Return data incidents."""
    return _INCIDENTS


@router.get("/bias-gates", response_model=list[BiasGate])
async def get_bias_gates() -> list[BiasGate]:
    """Return bias gate checks."""
    return _BIAS_GATES


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
