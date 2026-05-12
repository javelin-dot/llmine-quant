"""Tests for strategy generation research backtest helpers."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.data.models import MarketBarDaily
from app.domains.strategy.generation_dsl import parse_strategy_generation_spec
from app.services.strategy_generation_research import (
    discover_default_research_universe,
    spec_to_dual_ma_params,
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as test_session:
        yield test_session

    await engine.dispose()


async def test_discover_default_research_universe_requires_enough_bars(session):
    from app.core.errors import LLMException

    session.add(
        MarketBarDaily(
            symbol="000001.SZ",
            trade_date="2024-01-02",
            prev_close=None,
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            volume=1000,
            amount=10_000.0,
            adjusted_close=10.0,
            can_buy=True,
            can_sell=True,
        )
    )
    await session.commit()

    with pytest.raises(LLMException, match="No market bars"):
        await discover_default_research_universe(session, min_bars=30)


async def test_discover_and_spec_to_dual_ma_with_seeded_bars(session):
    for i in range(1, 35):
        day = i if i <= 31 else i - 31
        month = "01" if i <= 31 else "02"
        session.add(
            MarketBarDaily(
                symbol="000001.SZ",
                trade_date=f"2024-{month}-{day:02d}",
                prev_close=10.0 + i * 0.01,
                open=10.0 + i * 0.01,
                high=10.1 + i * 0.01,
                low=9.9 + i * 0.01,
                close=10.0 + i * 0.01,
                volume=1000,
                amount=10_000.0,
                adjusted_close=10.0 + i * 0.01,
                can_buy=True,
                can_sell=True,
            )
        )
    await session.commit()

    universe, start, end = await discover_default_research_universe(session, min_bars=30)
    assert universe == ("000001.SZ",)
    assert start <= end

    spec = parse_strategy_generation_spec(
        {
            "strategy_kind": "rule",
            "factors": [{"name": "m", "kind": "momentum", "params": {"window": 20}}],
            "position_rules": {"max_positions": 5, "target_gross_exposure": 0.9},
        }
    )
    params = spec_to_dual_ma_params(spec)
    assert params["short_window"] < params["long_window"]
    assert params["max_positions"] == 5
    assert params["target_gross"] == pytest.approx(0.9)
