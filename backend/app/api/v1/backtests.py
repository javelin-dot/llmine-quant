"""Backtest Service API — backtest tasks, runs, reports, equity curves."""

from datetime import date as _date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.backtest.models import (
    BacktestMetric,
    BacktestRun,
    BacktestTask,
    BacktestTrade,
    EquityPoint,
)
from app.domains.backtest.models import (
    SensitivityRun as SensitivityRunModel,
)
from app.domains.backtest.models import (
    WalkForwardFold as WalkForwardFoldModel,
)
from app.domains.backtest.schemas import (
    BacktestComparisonRow,
    BacktestCostIn,
    BacktestCreateIn,
    BacktestEquityPointOut,
    BacktestLabCheckOut,
    BacktestMetricOut,
    BacktestPromotionGateOut,
    BacktestReportOut,
    BacktestScreen,
    BacktestTaskListItem,
    BacktestTaskResultOut,
    BacktestTradeOut,
    ConfidenceTower,
    EquityCurve,
    Kpi,
    OverfitAssessmentOut,
    OverfitComponentOut,
    ParameterHeatmap,
    SensitivityCreateIn,
    SensitivityResultOut,
    SensitivityRunOut,
    StressScenario,
    UniverseCandidate,
    UniverseSuggestIn,
    UniverseSuggestOut,
    WalkForwardCreateIn,
    WalkForwardFoldOut,
    WalkForwardResultOut,
)
from app.domains.data.models import FeatureSet, FeatureUsage, LineageEdge, MarketBarDaily
from app.services.daily_backtest import BacktestCostConfig, BacktestDataError, DailyBacktestConfig, DailyBacktestEngine
from app.services.overfitting import assess_overfitting
from app.services.sensitivity import run_sensitivity_analysis

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]

_KPIS: list[Kpi] = []

_EQUITY_CURVE = EquityCurve(label="", inSample=[], outSample=[], drawdown=[])

_CONFIDENCE = ConfidenceTower(score=0, label="—", features=[])

_WALK_FORWARD = {"folds": []}

_COMPARISON: list[BacktestComparisonRow] = []

_SCENARIOS: list[StressScenario] = []

_HEATMAP = ParameterHeatmap(
    xLabel="",
    yLabel="",
    xTicks=[],
    yTicks=[],
    cells=[],
    bestX=0,
    bestY=0,
)


_UNIVERSE_SUGGEST_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "selected": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["symbol", "reason"],
            },
        },
        "excluded": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["symbol", "reason"],
            },
        },
        "rationale": {"type": "string"},
        "diversity_note": {"type": "string"},
    },
    "required": ["selected", "excluded", "rationale"],
}

_UNIVERSE_SYSTEM_PROMPT = """你是量化交易股票池构建（Universe Construction）专家助手。
你的任务是从可用的市场数据标的中，根据量化策略类型筛选出最适合回测的标的池。

核心原则：
1. 避免过拟合：不要因为某标的历史表现好就选择它，要基于数据质量和策略适配性
2. 数据完整性优先：K线数量多、连续性强的标的优于数据稀疏的标的
3. 策略适配性：不同策略类型（趋势/动量/均值回归）对标的特征有不同偏好
4. 多样性：避免过度集中在单一行业或相似特征的标的

你必须返回严格的JSON格式，不得包含任何markdown或注释。"""


@router.post("/universe/suggest", response_model=UniverseSuggestOut)
async def suggest_universe(payload: UniverseSuggestIn, db: DbSession) -> UniverseSuggestOut:
    """AI-powered universe builder using the three-step stock selection method.

    1. Liquidity (流动性):  index pool membership + data depth + avg turnover.
    2. Volatility (波动):   annualized volatility band.
    3. Momentum (动量):     trailing return over a lookback window.

    Each parameter is enforced server-side, so changing any criterion produces
    a different candidate / selection list. The LLM picks the final pool from
    the filtered candidates and explains every choice.
    """
    import asyncio as _asyncio
    import math

    from app.integrations.llm.factory import get_llm_provider

    # ── Build raw candidate list from the requested index pool ───────────
    # Supported pools:
    #   csi300 / csi500 / csi1000 — index constituents w/ weights (via AKShare)
    #   both                       — CSI 300 + CSI 500 union
    #   all                        — every A-share spot (no weights)
    # Then we apply board (exchange-board) and sector (industry) filters as
    # independent dimensions so universes like "ChiNext ∩ 半导体" are expressible.

    # Code-prefix → board mapping (raw 6-digit code, no suffix).
    board_prefixes: dict[str, tuple[str, ...]] = {
        "main":    ("600", "601", "603", "605", "000", "001", "002"),
        "star":    ("688", "689"),
        "chinext": ("300", "301"),
        "bse":     ("43", "83", "87", "92", "8"),
    }
    requested_boards = {b for b in payload.boards if b in board_prefixes}
    requested_board_prefixes: tuple[str, ...] = tuple(
        p for b in requested_boards for p in board_prefixes[b]
    )

    def _exchange_suffix(code: str) -> str:
        # BSE codes (43/83/87/92/starts-with-8 except 600 are SH).
        if code.startswith(("43", "83", "87", "92")):
            return "BJ"
        if code.startswith("8") and not code.startswith(("80",)):  # 8xx → BSE
            return "BJ"
        if code.startswith(("60", "68", "9", "11", "13")):
            return "SH"
        return "SZ"

    def _passes_board(raw_code: str) -> bool:
        if not requested_board_prefixes:
            return True
        return raw_code.startswith(requested_board_prefixes)

    candidates_raw: list[dict] = []
    seen: set[str] = set()

    def _push(symbol: str, name: str, weight: float, label: str) -> None:
        if not symbol or symbol in seen:
            return
        raw_code = symbol.split(".")[0]
        if not _passes_board(raw_code):
            return
        seen.add(symbol)
        candidates_raw.append({
            "symbol": symbol,
            "name": name,
            "weight": weight,
            "index": label,
            "bars": 0,
            "start_date": "",
            "end_date": "",
            "coverage_days": 0,
            "has_local_data": False,
            "avg_turnover": 0.0,
            "volatility": 0.0,
            "momentum": 0.0,
        })

    pool_codes: list[str]
    if payload.index_pool == "csi300":
        pool_codes = ["000300"]
    elif payload.index_pool == "csi500":
        pool_codes = ["000905"]
    elif payload.index_pool == "csi1000":
        pool_codes = ["000852"]
    elif payload.index_pool == "all":
        pool_codes = []  # full-market path below
    else:  # "both" — CSI 300 + 500
        pool_codes = ["000300", "000905"]

    try:
        import akshare as ak

        if payload.index_pool == "all":
            # `stock_zh_a_spot_em` returns the whole A-share market (~5k rows).
            # It has no weight column — that's fine for full-market scans.
            df = await _asyncio.to_thread(ak.stock_zh_a_spot_em)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    sym_code = str(row.get("代码", "")).strip()
                    if not sym_code:
                        continue
                    name = str(row.get("名称", ""))
                    _push(f"{sym_code}.{_exchange_suffix(sym_code)}", name, 0.0, "all")
        elif pool_codes:
            index_dfs = await _asyncio.gather(
                *[_asyncio.to_thread(ak.index_stock_cons_weight_csindex, symbol=code)
                  for code in pool_codes],
                return_exceptions=True,
            )
            index_label = {"000300": "csi300", "000905": "csi500", "000852": "csi1000"}
            for code, df in zip(pool_codes, index_dfs, strict=False):
                if isinstance(df, Exception) or df is None or df.empty:
                    continue
                for _, row in df.iterrows():
                    sym_code = str(row.get("成分券代码", "")).strip()
                    exch = str(row.get("交易所", "")).strip()
                    if not sym_code:
                        continue
                    suffix = "SH" if "上海" in exch else "SZ" if "深圳" in exch else _exchange_suffix(sym_code)
                    symbol = f"{sym_code}.{suffix}"
                    weight = float(row.get("权重", 0) or 0)
                    name = str(row.get("成分券名称", ""))
                    _push(symbol, name, weight, index_label.get(code, code))

        # Sector intersection (申万行业): if the user picked sectors, fetch each
        # board's constituents and intersect with candidates_raw.
        if payload.sectors and candidates_raw:
            sector_dfs = await _asyncio.gather(
                *[_asyncio.to_thread(ak.stock_board_industry_cons_em, symbol=s)
                  for s in payload.sectors],
                return_exceptions=True,
            )
            sector_codes: set[str] = set()
            for df in sector_dfs:
                if isinstance(df, Exception) or df is None or df.empty:
                    continue
                for _, row in df.iterrows():
                    c = str(row.get("代码", "")).strip()
                    if c:
                        sector_codes.add(c)
            if sector_codes:
                candidates_raw = [
                    c for c in candidates_raw
                    if c["symbol"].split(".")[0] in sector_codes
                ]
            else:
                # All sector fetches failed or were empty — clear pool so the
                # UI surfaces a clear "sector data unavailable" empty state.
                candidates_raw = []
    except Exception:  # noqa: BLE001
        pass  # fall through to DB-only mode below

    # ── Pull bar stats & price/volume series for momentum/volatility ──────
    # Single grouped query for aggregate stats:
    agg_rows = (
        await db.execute(
            select(
                MarketBarDaily.symbol,
                func.count(MarketBarDaily.id).label("bars"),
                func.min(MarketBarDaily.trade_date).label("start_date"),
                func.max(MarketBarDaily.trade_date).label("end_date"),
                func.avg(MarketBarDaily.amount).label("avg_amount"),
            )
            .group_by(MarketBarDaily.symbol)
        )
    ).all()
    db_stats: dict[str, dict] = {}
    for row in agg_rows:
        try:
            cov = (_date.fromisoformat(row.end_date) - _date.fromisoformat(row.start_date)).days
        except Exception:
            cov = int(row.bars)
        db_stats[row.symbol] = {
            "bars": int(row.bars),
            "start_date": row.start_date,
            "end_date": row.end_date,
            "coverage_days": cov,
            "avg_turnover": float(row.avg_amount or 0.0),
        }

    # If no AKShare data, build candidates directly from DB symbols. Honor
    # the board filter even in this fallback path.
    if not candidates_raw:
        for sym, stats in db_stats.items():
            raw_code = sym.split(".")[0]
            if not _passes_board(raw_code):
                continue
            candidates_raw.append({
                "symbol": sym, "name": "", "weight": 0.0, "index": "db",
                "has_local_data": True, "volatility": 0.0, "momentum": 0.0,
                **stats,
            })

    for c in candidates_raw:
        if c["symbol"] in db_stats:
            c.update(db_stats[c["symbol"]], has_local_data=True)

    # ── Compute volatility + momentum per data-ready symbol ───────────────
    ready_symbols = [c["symbol"] for c in candidates_raw if c["has_local_data"]]
    if ready_symbols:
        bar_rows = (
            await db.execute(
                select(
                    MarketBarDaily.symbol,
                    MarketBarDaily.trade_date,
                    MarketBarDaily.close,
                )
                .where(MarketBarDaily.symbol.in_(ready_symbols))
                .order_by(MarketBarDaily.symbol, MarketBarDaily.trade_date)
            )
        ).all()
        series: dict[str, list[tuple[str, float]]] = {}
        for row in bar_rows:
            if row.close is None or row.close <= 0:
                continue
            series.setdefault(row.symbol, []).append((row.trade_date, float(row.close)))

        for c in candidates_raw:
            pts = series.get(c["symbol"]) or []
            if len(pts) < 2:
                continue
            # Annualized volatility from daily log returns (use the last
            # `momentum_window_days` worth of bars so the user can probe
            # different windows).
            window = max(payload.momentum_window_days, 20)
            tail = pts[-min(len(pts), window + 1):]
            rets: list[float] = []
            for i in range(1, len(tail)):
                p0, p1 = tail[i - 1][1], tail[i][1]
                if p0 > 0 and p1 > 0:
                    rets.append(math.log(p1 / p0))
            if rets:
                mean = sum(rets) / len(rets)
                var = sum((r - mean) ** 2 for r in rets) / max(len(rets) - 1, 1)
                c["volatility"] = math.sqrt(var) * math.sqrt(252)
                c["momentum"] = (tail[-1][1] / tail[0][1]) - 1.0

    # ── Apply three-step filter ──────────────────────────────────────────
    if not candidates_raw:
        return UniverseSuggestOut(
            symbols=[], candidates=[], diversityScore=0.0, coverageDays=0,
            recommendation="未能获取市场标的列表（AKShare 网络异常）且本地无行情数据，请检查网络或先通过「行情与合规」屏（侧边栏 Control 区）导入行情。",
        )

    eligible_candidates: list[dict] = []
    rejected_preview: list[dict] = []
    # Bottleneck histogram — tells the user which step rejected the most.
    drop_bucket: dict[str, int] = {
        "no_data": 0, "bars": 0, "turnover": 0,
        "vol_low": 0, "vol_high": 0, "mom_low": 0, "mom_high": 0,
    }
    for c in candidates_raw:
        if not c["has_local_data"]:
            c["drop_reason"] = "本地无历史行情数据"
            c["drop_step"] = "no_data"
            drop_bucket["no_data"] += 1
            rejected_preview.append(c)
            continue
        if int(c.get("bars") or 0) < payload.min_bars:
            c["drop_reason"] = f"K线 {c['bars']} 根 < 最少 {payload.min_bars} 根"
            c["drop_step"] = "bars"
            drop_bucket["bars"] += 1
            rejected_preview.append(c)
            continue
        if float(c.get("avg_turnover") or 0) < payload.min_avg_turnover_cny:
            c["drop_reason"] = (
                f"日均成交额 {c['avg_turnover'] / 1e8:.2f}亿 < 门槛 "
                f"{payload.min_avg_turnover_cny / 1e8:.2f}亿"
            )
            c["drop_step"] = "turnover"
            drop_bucket["turnover"] += 1
            rejected_preview.append(c)
            continue
        vol = float(c.get("volatility") or 0)
        if vol < payload.min_volatility:
            c["drop_reason"] = f"年化波动 {vol * 100:.1f}% < 下限 {payload.min_volatility * 100:.1f}%"
            c["drop_step"] = "vol_low"
            drop_bucket["vol_low"] += 1
            rejected_preview.append(c)
            continue
        if vol > payload.max_volatility:
            c["drop_reason"] = f"年化波动 {vol * 100:.1f}% > 上限 {payload.max_volatility * 100:.1f}%"
            c["drop_step"] = "vol_high"
            drop_bucket["vol_high"] += 1
            rejected_preview.append(c)
            continue
        mom = float(c.get("momentum") or 0)
        if mom < payload.min_momentum:
            c["drop_reason"] = (
                f"近 {payload.momentum_window_days} 日动量 {mom * 100:.1f}% < 下限 "
                f"{payload.min_momentum * 100:.1f}%"
            )
            c["drop_step"] = "mom_low"
            drop_bucket["mom_low"] += 1
            rejected_preview.append(c)
            continue
        if mom > payload.max_momentum:
            c["drop_reason"] = (
                f"近 {payload.momentum_window_days} 日动量 {mom * 100:.1f}% > 上限 "
                f"{payload.max_momentum * 100:.1f}%"
            )
            c["drop_step"] = "mom_high"
            drop_bucket["mom_high"] += 1
            rejected_preview.append(c)
            continue
        eligible_candidates.append(c)

    def _bottleneck_hint() -> str:
        """Return a one-sentence diagnosis of the dominant rejection reason."""
        if not rejected_preview:
            return ""
        worst = max(drop_bucket.items(), key=lambda kv: kv[1])
        if worst[1] == 0:
            return ""
        bucket_label = {
            "no_data":  "本地无历史行情数据 — 在「行情与合规」屏（侧边栏 Control 区）同步对应标的",
            "bars":     f"K 线数不足 — 降低「最少 K 线」门槛（当前 {payload.min_bars}）",
            "turnover": f"日均成交额不达标 — 降低门槛（当前 {payload.min_avg_turnover_cny / 1e8:.2f} 亿）",
            "vol_low":  f"波动率偏低 — 调低下限（当前 {payload.min_volatility * 100:.0f}%）",
            "vol_high": f"波动率偏高 — 调高上限（当前 {payload.max_volatility * 100:.0f}%）",
            "mom_low":  f"动量偏低 — 调低下限（当前 {payload.min_momentum * 100:.0f}%）",
            "mom_high": f"动量偏高 — 调高上限（当前 {payload.max_momentum * 100:.0f}%）",
        }[worst[0]]
        pct = worst[1] * 100 // max(len(rejected_preview), 1)
        return f"最大瓶颈：{pct}% 因「{bucket_label}」被剔除"

    # Rank eligibles per strategy family so changing strategy_family also
    # changes ordering (and therefore the LLM context + heuristic fallback).
    if payload.strategy_family == "momentum":
        eligible_candidates.sort(key=lambda c: -float(c.get("momentum") or 0))
    elif payload.strategy_family == "mean_reversion":
        eligible_candidates.sort(key=lambda c: -float(c.get("volatility") or 0))
    else:  # trend / default
        eligible_candidates.sort(
            key=lambda c: (-float(c.get("avg_turnover") or 0), -c.get("weight", 0))
        )

    target_count = min(payload.max_symbols, len(eligible_candidates))
    if target_count == 0:
        preview = [
            UniverseCandidate(
                symbol=c["symbol"],
                name=c.get("name") or None,
                bars=c.get("bars") or 0,
                startDate=c.get("start_date") or "—",
                endDate=c.get("end_date") or "—",
                coverageDays=c.get("coverage_days") or 0,
                selected=False,
                reason=c.get("drop_reason"),
                avgTurnover=c.get("avg_turnover"),
                volatility=c.get("volatility"),
                momentum=c.get("momentum"),
                dropReason=c.get("drop_reason"),
            )
            for c in rejected_preview[:60]
        ]
        bottleneck = _bottleneck_hint()
        return UniverseSuggestOut(
            symbols=[],
            candidates=preview,
            totalPool=len(candidates_raw),
            totalEligible=0,
            totalRejected=len(rejected_preview),
            diversityScore=0.0,
            coverageDays=0,
            recommendation=(
                f"三步筛选未保留任何标的（候选 {len(candidates_raw)} / 被拒 {len(rejected_preview)}）。"
                + (f" {bottleneck}。" if bottleneck else "")
                + " 请放宽对应阈值，"
                "或先在「行情与合规」屏（侧边栏 Control 区）导入更多行情。"
            ),
        )

    # ── LLM picks final pool from filtered candidates ────────────────────
    strategy_desc = {
        "trend": "趋势跟踪（双均线）：偏好流动性高、波动适中、动量正向的趋势标的",
        "momentum": "横截面动量：偏好近期动量靠前、流动性充足、波动可控的标的",
        "mean_reversion": "均值回归：偏好波动较大、近期超跌或超涨的标的",
    }.get(payload.strategy_family, f"量化策略（{payload.strategy_family}）")

    context_symbols = eligible_candidates[:60]
    extra = len(eligible_candidates) - len(context_symbols)

    def _row_line(c: dict) -> str:
        return (
            f"  {c['symbol']} {c.get('name', '')}: "
            f"指数权重{c.get('weight', 0):.3f}%, "
            f"K线{c['bars']}根, "
            f"日均成交额 {(c.get('avg_turnover') or 0) / 1e8:.2f}亿, "
            f"年化波动 {(c.get('volatility') or 0) * 100:.1f}%, "
            f"近{payload.momentum_window_days}日动量 {(c.get('momentum') or 0) * 100:.1f}%"
        )

    symbol_table = "\n".join(_row_line(c) for c in context_symbols)

    prompt = f"""以下是已通过【三步选股法】筛选的候选标的（共 {len(eligible_candidates)} 个）。
每一行包含流动性、波动率、动量等关键指标：

{symbol_table}
{"（另有 " + str(extra) + " 个标的未展示）" if extra else ""}

筛选条件（用户已设定）：
- 指数池：{payload.index_pool}
- 最少 K 线：{payload.min_bars} 根
- 日均成交额下限：{payload.min_avg_turnover_cny / 1e8:.2f} 亿元
- 年化波动率区间：[{payload.min_volatility * 100:.1f}%, {payload.max_volatility * 100:.1f}%]
- 近 {payload.momentum_window_days} 日动量区间：[{payload.min_momentum * 100:.1f}%, {payload.max_momentum * 100:.1f}%]

策略构建需求：
- 策略类型：{strategy_desc}
- 目标标的数：{target_count} 个（不得超过此数量）
- 多样性要求：{"是，避免过度集中在单一行业" if payload.diversify else "否"}

只能从上方候选池中选择；这些标的均已通过三步过滤。
对每个选中标的，给出 1-2 句理由（聚焦行业分散性、策略适配性、关键指标），禁止基于"过去涨得多"推荐。
对主要排除标的给出 1 句理由。最后给出整体股票池构建逻辑（2-3 句）。"""

    llm_result: dict | None = None
    ai_model: str | None = None
    try:
        provider = get_llm_provider()
        raw = await provider.generate_structured(
            prompt=prompt,
            output_schema=_UNIVERSE_SUGGEST_SCHEMA,
            system_prompt=_UNIVERSE_SYSTEM_PROMPT,
            temperature=0.3,
        )
        llm_result = raw
        ai_model = provider.model or provider.name
    except Exception:
        llm_result = None

    symbol_map = {c["symbol"]: c for c in eligible_candidates}
    reason_map: dict[str, str] = {}
    selected_symbols: list[str] = []
    ai_rationale: str | None = None

    if llm_result and isinstance(llm_result.get("selected"), list) and llm_result["selected"]:
        for item in llm_result["selected"]:
            sym = item.get("symbol", "")
            if sym in symbol_map and sym not in selected_symbols and len(selected_symbols) < target_count:
                selected_symbols.append(sym)
                reason_map[sym] = item.get("reason", "AI 推荐入选")
        for item in (llm_result.get("excluded") or []):
            sym = item.get("symbol", "")
            if sym and sym not in reason_map:
                reason_map[sym] = item.get("reason", "AI 未推荐")
        ai_rationale = llm_result.get("rationale") or llm_result.get("diversity_note")
    else:
        for c in eligible_candidates:
            if len(selected_symbols) >= target_count:
                break
            selected_symbols.append(c["symbol"])
            reason_map[c["symbol"]] = (
                f"按三步排序入选：K线 {c['bars']} 根 / 日均成交 "
                f"{(c.get('avg_turnover') or 0) / 1e8:.2f}亿 / 波动 "
                f"{(c.get('volatility') or 0) * 100:.1f}% / 动量 "
                f"{(c.get('momentum') or 0) * 100:.1f}%"
            )
        ai_model = None

    # Deterministically fill to target_count from the ranked eligibles.
    for c in eligible_candidates:
        if len(selected_symbols) >= target_count:
            break
        if c["symbol"] in selected_symbols:
            continue
        selected_symbols.append(c["symbol"])
        reason_map.setdefault(
            c["symbol"],
            f"按当前排序补齐：动量 {(c.get('momentum') or 0) * 100:.1f}% / "
            f"波动 {(c.get('volatility') or 0) * 100:.1f}%",
        )

    selected_set = set(selected_symbols)

    def _candidate_out(c: dict, selected: bool, reason: str | None) -> UniverseCandidate:
        return UniverseCandidate(
            symbol=c["symbol"],
            name=c.get("name") or None,
            bars=c.get("bars") or 0,
            startDate=c.get("start_date") or "—",
            endDate=c.get("end_date") or "—",
            coverageDays=c.get("coverage_days") or 0,
            selected=selected,
            reason=reason,
            avgTurnover=c.get("avg_turnover"),
            volatility=c.get("volatility"),
            momentum=c.get("momentum"),
            dropReason=c.get("drop_reason"),
        )

    candidates: list[UniverseCandidate] = []
    for c in eligible_candidates:
        candidates.append(
            _candidate_out(c, c["symbol"] in selected_set, reason_map.get(c["symbol"]))
        )
    # Show top rejected so the user can see why a stock didn't make it.
    # For full-market scans there can be thousands of rejected candidates; cap
    # at 50 to keep the UI responsive while still surfacing the rejection mix.
    rejected_cap = 50 if payload.index_pool == "all" else 20
    for c in rejected_preview[:rejected_cap]:
        candidates.append(_candidate_out(c, False, c.get("drop_reason")))

    n = len(selected_symbols)
    if n > 0:
        sel_meta = [symbol_map[s] for s in selected_symbols]
        avg_weight = sum(c.get("weight", 0) for c in sel_meta) / n
        diversity_score = round(
            min(n / payload.max_symbols, 1.0) * 0.5
            + (1 - min(avg_weight / 5.0, 1.0)) * 0.5,
            2,
        )
        start_dates = [c.get("start_date") for c in sel_meta if c.get("start_date")]
        end_dates = [c.get("end_date") for c in sel_meta if c.get("end_date")]
        coverage_days = (
            max(
                (_date.fromisoformat(max(end_dates))
                 - _date.fromisoformat(min(start_dates))).days,
                0,
            )
            if start_dates and end_dates else 0
        )
    else:
        diversity_score = 0.0
        coverage_days = 0

    no_data_count = sum(
        1 for c in rejected_preview if c.get("drop_reason") == "本地无历史行情数据"
    )
    rec = ai_rationale or (
        f"按三步选股法保留 {n} 个标的（全市场候选 {len(candidates_raw)} / "
        f"通过三步 {len(eligible_candidates)} / 被拒 {len(rejected_preview)}"
        + (f"，其中 {no_data_count} 个本地无数据" if no_data_count else "")
        + "）。可调整流动性 / 波动 / 动量阈值再生成。"
        if n > 0 else (
            f"全市场候选 {len(candidates_raw)}，其中 {no_data_count} 个本地无数据。"
            "请放宽筛选条件，或先在「行情与合规」屏（侧边栏 Control 区）同步更多行情。"
            if no_data_count else "未能生成推荐，请放宽筛选条件或导入更多行情数据。"
        )
    )

    return UniverseSuggestOut(
        symbols=selected_symbols,
        candidates=candidates,
        totalPool=len(candidates_raw),
        totalEligible=len(eligible_candidates),
        totalRejected=len(rejected_preview),
        diversityScore=diversity_score,
        coverageDays=coverage_days,
        recommendation=rec,
        aiRationale=ai_rationale,
        aiModel=ai_model,
    )


@router.get("/universe/sectors")
async def list_universe_sectors() -> list[dict[str, str | int]]:
    """Return the available 申万 industry-board names for the universe builder.

    Cached in-process for 10 minutes — the list rarely changes and the AKShare
    call is ~1-2s.
    """
    import asyncio as _asyncio
    import time as _time

    cache: dict = getattr(list_universe_sectors, "_cache", {})
    now = _time.time()
    if cache and now - cache.get("ts", 0) < 600:
        return cache["items"]
    try:
        import akshare as ak
        df = await _asyncio.to_thread(ak.stock_board_industry_name_em)
        if df is None or df.empty:
            return []
        items: list[dict[str, str | int]] = []
        for _, row in df.iterrows():
            name = str(row.get("板块名称", "")).strip()
            if not name:
                continue
            items.append({
                "name": name,
                "count": int(row.get("公司家数", 0) or 0),
            })
        items.sort(key=lambda x: -int(x["count"]))
        list_universe_sectors._cache = {"ts": now, "items": items}  # type: ignore[attr-defined]
        return items
    except Exception:  # noqa: BLE001
        return []


@router.get("/overview", response_model=BacktestScreen)
async def get_backtest_overview(db: DbSession) -> BacktestScreen:
    """Return the complete Backtest Lab screen data."""
    return BacktestScreen(
        kpis=_KPIS,
        equityCurves=_EQUITY_CURVE,
        confidence=_CONFIDENCE,
        walkForward=_WALK_FORWARD,
        comparison=_COMPARISON,
        scenarios=_SCENARIOS,
        parameterHeatmap=_HEATMAP,
    )


@router.post("/", response_model=BacktestTaskResultOut)
async def create_backtest_task(
    payload: BacktestCreateIn,
    db: DbSession,
) -> BacktestTaskResultOut:
    """Create, execute and persist a research backtest task."""
    engine = DailyBacktestEngine(db)
    try:
        result = await engine.run_and_persist(
            _daily_backtest_config(payload),
            strategy_version_id=payload.strategy_id,
        )
    except (BacktestDataError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _result_out(result)


@router.post("/sensitivity", response_model=SensitivityResultOut)
async def create_sensitivity_analysis(
    payload: SensitivityCreateIn,
    db: DbSession,
) -> SensitivityResultOut:
    """Run baseline backtest + small parameter and slippage sweep."""
    engine = DailyBacktestEngine(db)
    config = DailyBacktestConfig(
        universe=tuple(payload.universe),
        start_date=payload.start_date,
        end_date=payload.end_date,
        strategy_name=payload.strategy_name,
        initial_cash=payload.initial_cash,
        strategy_params=payload.strategy_params,
        cost_config=_cost_config(payload.cost_config),
        in_sample_end_date=payload.in_sample_end_date,
    )
    try:
        baseline = await engine.run_and_persist(
            config, strategy_version_id=payload.strategy_id
        )
        assert baseline.run_id is not None
        summaries = await run_sensitivity_analysis(
            engine, config, parent_run_id=baseline.run_id, baseline_result=baseline
        )
    except (BacktestDataError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SensitivityResultOut(
        task_id=baseline.task_id or "",
        run_id=baseline.run_id,
        runs=[
            SensitivityRunOut(
                kind=s.kind,
                label=s.label,
                is_baseline=s.is_baseline,
                cumulative_return=s.metrics.cumulative_return,
                annual_return=s.metrics.annual_return,
                max_drawdown=s.metrics.max_drawdown,
                sharpe_ratio=s.metrics.sharpe_ratio,
                win_rate=s.metrics.win_rate,
                turnover=s.metrics.turnover,
            )
            for s in summaries
        ],
    )


@router.post("/walk-forward", response_model=WalkForwardResultOut)
async def create_walk_forward_backtest(
    payload: WalkForwardCreateIn,
    db: DbSession,
) -> WalkForwardResultOut:
    """Run a walk-forward analysis and persist folds + parent backtest."""
    engine = DailyBacktestEngine(db)
    config = DailyBacktestConfig(
        universe=tuple(payload.universe),
        start_date=payload.start_date,
        end_date=payload.end_date,
        strategy_name=payload.strategy_name,
        initial_cash=payload.initial_cash,
        strategy_params=payload.strategy_params,
        cost_config=_cost_config(payload.cost_config),
        in_sample_end_date=payload.in_sample_end_date,
    )
    try:
        result, summaries = await engine.run_walk_forward(
            config,
            folds=payload.folds,
            train_ratio=payload.train_ratio,
            strategy_version_id=payload.strategy_id,
        )
    except (BacktestDataError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return WalkForwardResultOut(
        task_id=result.task_id or "",
        run_id=result.run_id or "",
        aggregate=BacktestMetricOut(
            cumulative_return=result.metrics.cumulative_return,
            annual_return=result.metrics.annual_return,
            max_drawdown=result.metrics.max_drawdown,
            sharpe_ratio=result.metrics.sharpe_ratio,
            win_rate=result.metrics.win_rate,
            turnover=result.metrics.turnover,
        ),
        folds=[
            WalkForwardFoldOut(
                fold_index=s.fold_index,
                train_start=s.train_start,
                train_end=s.train_end,
                test_start=s.test_start,
                test_end=s.test_end,
                train_return=s.train_metrics.cumulative_return,
                test_return=s.test_metrics.cumulative_return,
                train_sharpe=s.train_metrics.sharpe_ratio,
                test_sharpe=s.test_metrics.sharpe_ratio,
                train_max_dd=s.train_metrics.max_drawdown,
                test_max_dd=s.test_metrics.max_drawdown,
            )
            for s in summaries
        ],
    )


@router.get("/{task_id}", response_model=BacktestTaskResultOut)
async def get_backtest_task(task_id: str, db: DbSession) -> BacktestTaskResultOut:
    """Get a persisted backtest task and its latest run result."""
    task = await db.get(BacktestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="backtest task not found")

    run = (
        await db.execute(
            select(BacktestRun)
            .where(BacktestRun.task_id == task.id)
            .order_by(BacktestRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        return BacktestTaskResultOut(task_id=task.id, status=task.status)

    metrics = (
        await db.execute(select(BacktestMetric).where(BacktestMetric.run_id == run.id))
    ).scalars().all()
    equity_points = (
        await db.execute(
            select(EquityPoint)
            .where(EquityPoint.run_id == run.id)
            .order_by(EquityPoint.trade_date)
        )
    ).scalars().all()
    return _persisted_result_out(
        task, run, list(metrics), list(equity_points), _split_date_from_task(task)
    )


@router.get("/", response_model=list[BacktestTaskListItem])
async def list_backtest_tasks(db: DbSession, limit: int = 20) -> list[BacktestTaskListItem]:
    """List recent backtest tasks with summary metrics for the workbench history panel."""
    import json as _json

    task_rows = (
        await db.execute(
            select(BacktestTask)
            .where(BacktestTask.deleted_at.is_(None))
            .order_by(BacktestTask.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    items: list[BacktestTaskListItem] = []
    for t in task_rows:
        config_payload: dict = {}
        if t.config:
            try:
                config_payload = _json.loads(t.config)
            except Exception:  # noqa: BLE001
                config_payload = {}
        run = (
            await db.execute(
                select(BacktestRun)
                .where(BacktestRun.task_id == t.id)
                .order_by(BacktestRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        metric = None
        if run is not None:
            metric = (
                await db.execute(
                    select(BacktestMetric).where(
                        BacktestMetric.run_id == run.id, BacktestMetric.segment == "all"
                    )
                )
            ).scalar_one_or_none()
        items.append(
            BacktestTaskListItem(
                task_id=t.id,
                run_id=run.id if run else None,
                status=t.status,
                strategy_version_id=t.strategy_version_id,
                strategy_name=config_payload.get("strategy_name"),
                start_date=config_payload.get("start_date"),
                end_date=config_payload.get("end_date"),
                in_sample_end_date=config_payload.get("in_sample_end_date"),
                universe=list(config_payload.get("universe", [])),
                cumulative_return=metric.cumulative_return if metric else None,
                sharpe_ratio=metric.sharpe_ratio if metric else None,
                max_drawdown=metric.max_drawdown if metric else None,
                overfit_level=metric.overfit_level if metric else None,
                created_at=t.created_at.isoformat() if t.created_at else "",
            )
        )
    return items


@router.get("/{task_id}/trades", response_model=list[BacktestTradeOut])
async def get_backtest_trades(
    task_id: str,
    db: DbSession,
    limit: int = 500,
) -> list[BacktestTradeOut]:
    """Return persisted trades for a backtest task — each carries the rule reason."""
    task = await db.get(BacktestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="backtest task not found")
    run = (
        await db.execute(
            select(BacktestRun)
            .where(BacktestRun.task_id == task.id)
            .order_by(BacktestRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        return []
    trades = (
        await db.execute(
            select(BacktestTrade)
            .where(BacktestTrade.run_id == run.id)
            .order_by(BacktestTrade.trade_date.asc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        BacktestTradeOut(
            trade_date=t.trade_date,
            symbol=t.symbol,
            side=t.side,
            quantity=t.quantity,
            price=t.price,
            amount=t.amount,
            target_weight=t.target_weight,
            total_cost=t.total_cost,
            net_cash_flow=t.net_cash_flow,
            reason=t.reason,
        )
        for t in trades
    ]


@router.get("/{task_id}/report", response_model=BacktestReportOut)
async def get_backtest_report(task_id: str, db: DbSession) -> BacktestReportOut:
    """Unified Phase 3 report — IS/OOS + walk-forward + sensitivity + overfit + trades + lineage."""
    task = await db.get(BacktestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="backtest task not found")
    summary = await get_backtest_task(task_id, db)
    run_id = summary.run_id

    folds: list[WalkForwardFoldOut] = []
    sens: list[SensitivityRunOut] = []
    overfit: OverfitAssessmentOut | None = None
    trades: list[BacktestTradeOut] = []
    feature_rows: list[dict[str, str | None]] = []
    lineage_node_count = 0
    lineage_edge_count = 0
    config_payload = _config_from_task(task)

    if run_id:
        fold_rows = (
            await db.execute(
                select(WalkForwardFoldModel)
                .where(WalkForwardFoldModel.run_id == run_id)
                .order_by(WalkForwardFoldModel.fold_index)
            )
        ).scalars().all()
        folds = [
            WalkForwardFoldOut(
                fold_index=f.fold_index,
                train_start=f.train_start,
                train_end=f.train_end,
                test_start=f.test_start,
                test_end=f.test_end,
                train_return=f.train_return or 0.0,
                test_return=f.test_return or 0.0,
                train_sharpe=f.train_sharpe or 0.0,
                test_sharpe=f.test_sharpe or 0.0,
                train_max_dd=f.train_max_dd or 0.0,
                test_max_dd=f.test_max_dd or 0.0,
            )
            for f in fold_rows
        ]

        sens_rows = (
            await db.execute(
                select(SensitivityRunModel).where(SensitivityRunModel.parent_run_id == run_id)
            )
        ).scalars().all()
        sens = [
            SensitivityRunOut(
                kind=s.kind,
                label=s.label,
                is_baseline=bool(s.is_baseline),
                cumulative_return=s.cumulative_return or 0.0,
                annual_return=s.annual_return or 0.0,
                max_drawdown=s.max_drawdown or 0.0,
                sharpe_ratio=s.sharpe_ratio or 0.0,
                win_rate=s.win_rate or 0.0,
                turnover=s.turnover or 0.0,
            )
            for s in sens_rows
        ]

        # Re-compute (and persist) overfit so the report is always fresh.
        assessment = await assess_overfitting(db, run_id)
        overfit = OverfitAssessmentOut(
            score=assessment.score,
            level=assessment.level,
            components=[
                OverfitComponentOut(name=c.name, score=c.score, detail=c.detail)
                for c in assessment.components
            ],
        )

        trade_rows = (
            await db.execute(
                select(BacktestTrade)
                .where(BacktestTrade.run_id == run_id)
                .order_by(BacktestTrade.trade_date.asc())
            )
        ).scalars().all()
        trades = [
            BacktestTradeOut(
                trade_date=t.trade_date,
                symbol=t.symbol,
                side=t.side,
                quantity=t.quantity,
                price=t.price,
                amount=t.amount,
                target_weight=t.target_weight,
                total_cost=t.total_cost,
                net_cash_flow=t.net_cash_flow,
                reason=t.reason,
            )
            for t in trade_rows
        ]

        usage_rows = (
            await db.execute(
                select(FeatureUsage, FeatureSet)
                .join(FeatureSet, FeatureSet.id == FeatureUsage.feature_id)
                .where(FeatureUsage.backtest_run_id == run_id)
            )
        ).all()
        feature_rows = [
            {
                "featureId": u.feature_id,
                "featureName": f.name,
                "featureVersion": f.version,
                "role": u.role,
            }
            for (u, f) in usage_rows
        ]

        edge_rows = (
            await db.execute(select(LineageEdge).where(LineageEdge.backtest_run_id == run_id))
        ).scalars().all()
        lineage_edge_count = len(edge_rows)
        lineage_node_count = len({e.from_node_id for e in edge_rows} | {e.to_node_id for e in edge_rows})

    lab_checklist = _lab_checklist(summary, config_payload, folds, sens, overfit, trades)
    promotion_gate = _promotion_gate(lab_checklist)

    return BacktestReportOut(
        task_id=task_id,
        run_id=run_id,
        summary=summary,
        walk_forward_folds=folds,
        sensitivity_runs=sens,
        overfit=overfit,
        trades=trades,
        feature_usage=feature_rows,
        lineage_node_count=lineage_node_count,
        lineage_edge_count=lineage_edge_count,
        lab_checklist=lab_checklist,
        promotion_gate=promotion_gate,
    )


@router.get("/{task_id}/overfit", response_model=OverfitAssessmentOut)
async def get_overfit_assessment(task_id: str, db: DbSession) -> OverfitAssessmentOut:
    """Compute (or recompute) the overfitting score for a backtest task."""
    task = await db.get(BacktestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="backtest task not found")
    run = (
        await db.execute(
            select(BacktestRun)
            .where(BacktestRun.task_id == task.id)
            .order_by(BacktestRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="no run found for task")

    assessment = await assess_overfitting(db, run.id)
    return OverfitAssessmentOut(
        score=assessment.score,
        level=assessment.level,
        components=[
            OverfitComponentOut(name=c.name, score=c.score, detail=c.detail)
            for c in assessment.components
        ],
    )


def _split_date_from_task(task: BacktestTask) -> str | None:
    return _config_from_task(task).get("in_sample_end_date")


def _config_from_task(task: BacktestTask) -> dict:
    import json as _json

    if not task.config:
        return {}
    try:
        payload = _json.loads(task.config)
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _lab_checklist(
    summary: BacktestTaskResultOut,
    config_payload: dict,
    folds: list[WalkForwardFoldOut],
    sensitivity_runs: list[SensitivityRunOut],
    overfit: OverfitAssessmentOut | None,
    trades: list[BacktestTradeOut],
) -> list[BacktestLabCheckOut]:
    """Translate raw artefacts into a research-readiness checklist.

    This is intentionally computed, not persisted: it is product guidance over
    immutable backtest artefacts, so thresholds can evolve without migrations.
    """

    metric = summary.metrics
    equity_days = len(summary.equity_curve)
    universe_size = len(config_payload.get("universe") or [])
    cost_config = config_payload.get("cost_config") or {}

    checks: list[BacktestLabCheckOut] = []
    checks.append(
        _check(
            "data_coverage",
            "数据覆盖",
            "pass" if equity_days >= 120 and universe_size >= 5 else "warn",
            f"{universe_size} 个标的，{equity_days} 个交易日；生产研究建议至少覆盖 5 个标的和 120 个交易日。",
        )
    )
    checks.append(
        _check(
            "oos_split",
            "样本外验证",
            "pass" if summary.out_sample_metrics is not None else "fail",
            "已配置 IS/OOS 切分。" if summary.out_sample_metrics is not None else "缺少样本外切分，无法判断策略是否只适配历史样本。",
        )
    )
    checks.append(
        _check(
            "walk_forward",
            "滚动验证",
            "pass" if len(folds) >= 3 else "warn",
            f"已完成 {len(folds)} 折 Walk-Forward；主流研究流程通常要求 3 折以上。",
        )
    )
    variant_count = len([r for r in sensitivity_runs if not r.is_baseline])
    checks.append(
        _check(
            "sensitivity",
            "参数/成本敏感性",
            "pass" if variant_count >= 3 else "warn",
            f"已完成 {variant_count} 个扰动变体；需要观察参数、滑点变化后收益是否剧烈塌陷。",
        )
    )
    checks.append(
        _check(
            "overfit",
            "过拟合风险",
            "pass" if overfit and overfit.level == "low" else "warn" if overfit and overfit.level == "medium" else "fail",
            f"当前评分 {overfit.score}/100，等级 {overfit.level}。" if overfit else "尚未形成过拟合评分。",
        )
    )
    if metric is None:
        risk_status = "fail"
        risk_detail = "缺少核心绩效指标。"
    elif metric.sharpe_ratio >= 1 and metric.max_drawdown >= -0.2:
        risk_status = "pass"
        risk_detail = f"Sharpe {metric.sharpe_ratio:.2f}，最大回撤 {metric.max_drawdown:.1%}，满足基础风控门槛。"
    elif metric.sharpe_ratio >= 0.5 and metric.max_drawdown >= -0.3:
        risk_status = "warn"
        risk_detail = f"Sharpe {metric.sharpe_ratio:.2f}，最大回撤 {metric.max_drawdown:.1%}，只适合继续研究。"
    else:
        risk_status = "fail"
        risk_detail = f"Sharpe {metric.sharpe_ratio:.2f}，最大回撤 {metric.max_drawdown:.1%}，不应晋级。"
    checks.append(_check("risk_reward", "收益风险比", risk_status, risk_detail))
    checks.append(
        _check(
            "trade_evidence",
            "交易证据",
            "pass" if trades else "warn",
            f"记录 {len(trades)} 笔模拟成交；可回放触发原因和成本。" if trades else "没有成交，收益曲线可能只是空仓现金曲线。",
        )
    )
    zero_cost = all(float(cost_config.get(k, 0) or 0) == 0 for k in ("commission_rate", "stamp_tax_rate", "slippage_bps"))
    checks.append(
        _check(
            "cost_model",
            "成本假设",
            "warn" if zero_cost else "pass",
            "当前使用零交易成本，仅适合调试。" if zero_cost else "已计入佣金、印花税或滑点假设。",
        )
    )
    return checks


def _promotion_gate(checks: list[BacktestLabCheckOut]) -> BacktestPromotionGateOut:
    hard_fail_ids = {"oos_split", "overfit", "risk_reward"}
    hard_fails = [c for c in checks if c.status == "fail" and c.id in hard_fail_ids]
    fails = [c for c in checks if c.status == "fail"]
    warns = [c for c in checks if c.status == "warn"]
    readiness_score = max(0, round(100 - len(fails) * 22 - len(warns) * 9))

    if hard_fails:
        decision = "block"
        label = "禁止晋级"
    elif fails or warns:
        decision = "review"
        label = "研究复核"
    else:
        decision = "pass"
        label = "可进入模拟盘"

    reasons = [f"{c.label}: {c.detail}" for c in hard_fails or fails or warns[:3]]
    next_actions = _next_actions(checks)
    return BacktestPromotionGateOut(
        decision=decision,
        label=label,
        readiness_score=readiness_score,
        reasons=reasons,
        next_actions=next_actions,
    )


def _next_actions(checks: list[BacktestLabCheckOut]) -> list[str]:
    suggestions = {
        "data_coverage": "扩大股票池与历史区间，覆盖不同市场状态。",
        "oos_split": "设置 IS/OOS 切分日，优先查看样本外收益和回撤。",
        "walk_forward": "运行 Walk-Forward，确认滚动训练/测试窗口表现一致。",
        "sensitivity": "运行敏感性扫描，检查参数和滑点扰动后的稳定性。",
        "overfit": "降低参数自由度或补充样本外证据后重新评估。",
        "risk_reward": "收紧仓位、止损或过滤条件，先把回撤和 Sharpe 拉回门槛。",
        "trade_evidence": "检查策略信号是否产生真实成交，避免空仓曲线误判。",
        "cost_model": "使用接近真实账户的佣金、印花税、滑点配置。",
    }
    return [suggestions[c.id] for c in checks if c.status != "pass" and c.id in suggestions][:4]


def _check(id_: str, label: str, status: str, detail: str) -> BacktestLabCheckOut:
    return BacktestLabCheckOut(id=id_, label=label, status=status, detail=detail)


def _daily_backtest_config(payload: BacktestCreateIn) -> DailyBacktestConfig:
    return DailyBacktestConfig(
        universe=tuple(payload.universe),
        start_date=payload.start_date,
        end_date=payload.end_date,
        strategy_name=payload.strategy_name,
        initial_cash=payload.initial_cash,
        strategy_params=payload.strategy_params,
        cost_config=_cost_config(payload.cost_config),
        in_sample_end_date=payload.in_sample_end_date,
    )


def _cost_config(payload: BacktestCostIn) -> BacktestCostConfig:
    return BacktestCostConfig(
        commission_rate=payload.commission_rate,
        min_commission=payload.min_commission,
        stamp_tax_rate=payload.stamp_tax_rate,
        slippage_bps=payload.slippage_bps,
    )


def _result_out(result) -> BacktestTaskResultOut:
    def _runtime_metrics(m) -> BacktestMetricOut:
        return BacktestMetricOut(
            cumulative_return=m.cumulative_return,
            annual_return=m.annual_return,
            max_drawdown=m.max_drawdown,
            sharpe_ratio=m.sharpe_ratio,
            win_rate=m.win_rate,
            turnover=m.turnover,
            calmar_ratio=getattr(m, "calmar_ratio", 0.0),
            sortino_ratio=getattr(m, "sortino_ratio", 0.0),
            volatility=getattr(m, "volatility", 0.0),
            profit_factor=getattr(m, "profit_factor", 0.0),
        )

    split_date = result.in_sample_end_date

    def _phase_for(date_str: str) -> str:
        return "oos" if split_date is not None and date_str > split_date else "is"

    return BacktestTaskResultOut(
        task_id=result.task_id or "",
        status="completed",
        run_id=result.run_id,
        metrics=_runtime_metrics(result.metrics),
        in_sample_metrics=_runtime_metrics(result.is_metrics) if result.is_metrics else None,
        out_sample_metrics=_runtime_metrics(result.oos_metrics) if result.oos_metrics else None,
        in_sample_end_date=split_date,
        equity_curve=[
            BacktestEquityPointOut(
                trade_date=point.trade_date,
                value=point.value,
                drawdown=point.drawdown,
                phase=_phase_for(point.trade_date),
            )
            for point in result.equity_curve
        ],
        monthly_returns=dict(result.monthly_returns),
    )


def _persisted_result_out(
    task: BacktestTask,
    run: BacktestRun,
    metrics: list[BacktestMetric],
    equity_points: list[EquityPoint],
    in_sample_end_date: str | None,
) -> BacktestTaskResultOut:
    by_segment: dict[str, BacktestMetric] = {m.segment: m for m in metrics}
    return BacktestTaskResultOut(
        task_id=task.id,
        status=task.status,
        run_id=run.id,
        metrics=_metric_out(by_segment.get("all")) if "all" in by_segment else None,
        in_sample_metrics=_metric_out(by_segment.get("is")) if "is" in by_segment else None,
        out_sample_metrics=_metric_out(by_segment.get("oos")) if "oos" in by_segment else None,
        in_sample_end_date=in_sample_end_date,
        equity_curve=[
            BacktestEquityPointOut(
                trade_date=point.trade_date,
                value=point.value,
                drawdown=point.drawdown,
                phase=point.phase or "is",
            )
            for point in equity_points
        ],
    )


def _metric_out(metric: BacktestMetric | None) -> BacktestMetricOut | None:
    if metric is None:
        return None
    return BacktestMetricOut(
        cumulative_return=metric.cumulative_return or 0.0,
        annual_return=metric.annual_return or 0.0,
        max_drawdown=metric.max_drawdown or 0.0,
        sharpe_ratio=metric.sharpe_ratio or 0.0,
        win_rate=metric.win_rate or 0.0,
        turnover=metric.turnover or 0.0,
        calmar_ratio=getattr(metric, "calmar_ratio", None) or 0.0,
        sortino_ratio=getattr(metric, "sortino_ratio", None) or 0.0,
        volatility=getattr(metric, "volatility", None) or 0.0,
        profit_factor=getattr(metric, "profit_factor", None) or 0.0,
    )
