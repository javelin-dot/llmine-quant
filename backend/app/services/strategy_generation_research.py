"""Research backtest helpers for AI strategy generation (Phase 2 — real backtest path)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import LLMException
from app.domains.data.models import MarketBarDaily
from app.domains.strategy.generation_dsl import StrategyGenerationSpec


def spec_to_dual_ma_params(spec: StrategyGenerationSpec) -> dict[str, Any]:
    """Map a validated DSL document to ``dual_ma`` built-in parameters (controlled proxy).

    Generated Python is not executed in the research engine yet; we use the built-in
    dual moving average with windows inferred from momentum-style factors when present.
    """
    short_w, long_w = 5, 20
    max_pos = min(spec.position_rules.max_positions, 20)
    max_pos = max(1, max_pos)
    target_gross = float(min(0.99, max(0.1, spec.position_rules.target_gross_exposure)))

    for factor in spec.factors:
        if factor.kind == "momentum":
            raw = factor.params.get("window", factor.params.get("lookback", factor.params.get("days", 20)))
            try:
                w = int(float(raw))
            except (TypeError, ValueError):
                w = 20
            w = max(3, min(w, 120))
            short_w = max(2, min(w // 4, w - 1))
            long_w = max(short_w + 1, min(w, 120))
            break
        if factor.kind in ("value", "quality", "volatility", "size"):
            short_w, long_w = 5, max(25, min(40, long_w))
            break

    return {
        "short_window": short_w,
        "long_window": long_w,
        "max_positions": max_pos,
        "target_gross": target_gross,
    }


async def discover_default_research_universe(
    session: AsyncSession,
    *,
    min_bars: int = 30,
) -> tuple[tuple[str, ...], str, str]:
    """Pick one symbol with enough daily bars and return (universe, start_date, end_date)."""
    stmt = (
        select(MarketBarDaily.symbol, func.count(MarketBarDaily.id).label("n"))
        .group_by(MarketBarDaily.symbol)
        .having(func.count(MarketBarDaily.id) >= min_bars)
        .order_by(func.count(MarketBarDaily.id).desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        raise LLMException(
            "No market bars in database for research backtest "
            f"(need at least {min_bars} rows for one symbol). "
            "Import data via POST /api/v1/data/market-bars/import/csv or scripts first."
        )
    symbol = row[0]
    bounds = (
        await session.execute(
            select(func.min(MarketBarDaily.trade_date), func.max(MarketBarDaily.trade_date)).where(
                MarketBarDaily.symbol == symbol
            )
        )
    ).one()
    start, end = bounds[0], bounds[1]
    if not start or not end:
        raise LLMException("Could not resolve trade date range for research backtest.")
    return (symbol,), str(start), str(end)
