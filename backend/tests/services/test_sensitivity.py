"""Tests for sensitivity analysis service."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.backtest.models import SensitivityRun
from app.domains.data.models import MarketBarDaily
from app.services.daily_backtest import (
    BacktestCostConfig,
    DailyBacktestConfig,
    DailyBacktestEngine,
)
from app.services.sensitivity import run_sensitivity_analysis

ZERO_COST = BacktestCostConfig(
    commission_rate=0,
    min_commission=0,
    stamp_tax_rate=0,
    slippage_bps=0,
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as s:
        yield s
    await engine.dispose()


async def _seed_bars(session, symbol: str, n: int) -> None:
    for i in range(1, n + 1):
        close = 10.0 + i * 0.15 + (0.3 if i % 5 == 0 else 0.0)
        session.add(
            MarketBarDaily(
                symbol=symbol,
                trade_date=f"2024-01-{i:02d}" if i <= 31 else f"2024-02-{i - 31:02d}",
                prev_close=close - 0.15 if i > 1 else None,
                open=close,
                high=close + 0.05,
                low=close - 0.05,
                close=close,
                volume=1000,
                amount=close * 1000,
                adjusted_close=close,
                can_buy=True,
                can_sell=True,
            )
        )
    await session.commit()


async def test_sensitivity_writes_baseline_and_param_and_slippage_variants(session):
    await _seed_bars(session, "000001.SZ", 30)
    engine = DailyBacktestEngine(session)
    config = DailyBacktestConfig(
        universe=("000001.SZ",),
        start_date="2024-01-01",
        end_date="2024-01-30",
        initial_cash=1_000,
        strategy_params={"short_window": 3, "long_window": 8, "target_gross": 0.5},
        cost_config=ZERO_COST,
    )
    baseline = await engine.run_and_persist(config)
    assert baseline.run_id is not None

    summaries = await run_sensitivity_analysis(engine, config, parent_run_id=baseline.run_id)
    # baseline + 8 param variants + ≤ 4 slippage variants
    assert any(s.is_baseline for s in summaries)
    assert any(s.kind == "param" and not s.is_baseline for s in summaries)
    assert any(s.kind == "slippage" for s in summaries)

    rows = (
        await session.execute(
            select(SensitivityRun).where(SensitivityRun.parent_run_id == baseline.run_id)
        )
    ).scalars().all()
    assert len(rows) == len(summaries)
    assert sum(1 for r in rows if r.is_baseline) == 1
    assert {r.kind for r in rows} >= {"param", "slippage"}
