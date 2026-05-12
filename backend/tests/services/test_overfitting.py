"""Tests for overfit scoring on top of IS/OOS, walk-forward and sensitivity data."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.backtest.models import BacktestMetric
from app.domains.data.models import MarketBarDaily
from app.services.daily_backtest import (
    BacktestCostConfig,
    DailyBacktestConfig,
    DailyBacktestEngine,
)
from app.services.overfitting import assess_overfitting
from app.services.sensitivity import run_sensitivity_analysis

ZERO_COST = BacktestCostConfig(
    commission_rate=0, min_commission=0, stamp_tax_rate=0, slippage_bps=0
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _seed(session, symbol: str, n: int) -> None:
    for i in range(1, n + 1):
        close = 10.0 + i * 0.1 + (0.25 if i % 6 == 0 else 0.0)
        session.add(
            MarketBarDaily(
                symbol=symbol,
                trade_date=f"2024-01-{i:02d}" if i <= 31 else f"2024-02-{i - 31:02d}",
                prev_close=close - 0.1 if i > 1 else None,
                open=close, high=close + 0.05, low=close - 0.05, close=close,
                volume=1000, amount=close * 1000, adjusted_close=close,
                can_buy=True, can_sell=True,
            )
        )
    await session.commit()


async def test_assess_overfitting_combines_all_signals(session):
    """With IS/OOS + walk-forward + sensitivity present, all four components contribute."""
    await _seed(session, "000001.SZ", 32)
    engine = DailyBacktestEngine(session)
    config = DailyBacktestConfig(
        universe=("000001.SZ",),
        start_date="2024-01-01",
        end_date="2024-02-01",
        initial_cash=1_000,
        strategy_params={"short_window": 3, "long_window": 8, "target_gross": 0.5},
        cost_config=ZERO_COST,
        in_sample_end_date="2024-01-20",
    )
    baseline, _folds = await engine.run_walk_forward(config, folds=3, train_ratio=0.7)
    assert baseline.run_id is not None
    await run_sensitivity_analysis(engine, config, parent_run_id=baseline.run_id)

    assessment = await assess_overfitting(session, baseline.run_id)
    component_names = {c.name for c in assessment.components}
    assert "sharpe_decay" in component_names
    assert "drawdown_consistency" in component_names
    assert "walk_forward_continuity" in component_names
    assert "param_stability" in component_names

    assert 0 <= assessment.score <= 100
    assert assessment.level in {"low", "medium", "high"}

    # Persisted on the "all" segment row.
    metric = (
        await session.execute(
            select(BacktestMetric).where(
                BacktestMetric.run_id == baseline.run_id, BacktestMetric.segment == "all"
            )
        )
    ).scalar_one()
    assert metric.overfit_level == assessment.level
    assert metric.oos_score is not None


async def test_assess_overfitting_partial_signals_when_no_split(session):
    """A plain backtest (no split / no walk-forward / no sensitivity) still produces a result."""
    await _seed(session, "000001.SZ", 20)
    engine = DailyBacktestEngine(session)
    baseline = await engine.run_and_persist(
        DailyBacktestConfig(
            universe=("000001.SZ",),
            start_date="2024-01-01",
            end_date="2024-01-20",
            initial_cash=1_000,
            strategy_params={"short_window": 3, "long_window": 5, "target_gross": 0.5},
            cost_config=ZERO_COST,
        )
    )
    assert baseline.run_id is not None
    # With nothing but the baseline metrics, the assessment has no components.
    assessment = await assess_overfitting(session, baseline.run_id)
    assert assessment.components == []
    assert assessment.level == "high"
    assert assessment.score == 0
