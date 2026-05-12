"""Tests for the paper-trading end-of-day engine."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.data.models import MarketBarDaily
from app.domains.execution.paper_models import (
    PaperAccount,
    PaperFill,
    PaperNavPoint,
    PaperOrder,
    PaperPosition,
    PaperPreTradeCheck,
    PaperRiskBreach,
)
from app.services.paper_trading import PaperTradingEngine


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _seed_bars(session, symbol: str, n: int, *, base: float = 10.0) -> list[str]:
    dates: list[str] = []
    for i in range(1, n + 1):
        date = f"2024-01-{i:02d}" if i <= 31 else f"2024-02-{i - 31:02d}"
        close = base + i * 0.1
        session.add(
            MarketBarDaily(
                symbol=symbol,
                trade_date=date,
                prev_close=close - 0.1 if i > 1 else None,
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
        dates.append(date)
    await session.commit()
    return dates


async def _seed_universe(session, symbols: list[str], n: int) -> list[str]:
    """Seed `n` days of trending bars for each symbol in ``symbols``."""
    dates: list[str] = []
    for sym_idx, symbol in enumerate(symbols):
        base = 10.0 + sym_idx * 0.5
        seeded = await _seed_bars(session, symbol, n, base=base)
        if not dates:
            dates = seeded
    return dates


async def _make_account(session, name: str = "paper-1", cash: float = 100_000.0) -> PaperAccount:
    account = PaperAccount(
        name=name,
        owner_id="tester",
        market="A",
        initial_cash=cash,
        cash=cash,
        peak_nav=cash,
        status="active",
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


async def test_eod_cycle_creates_buy_order_fills_at_close_and_updates_nav(session):
    """With a 12-symbol universe the per-symbol weight stays under the 10% cap."""
    symbols = [f"00000{i}.SZ" for i in range(1, 13)]
    dates = await _seed_universe(session, symbols, 25)
    account = await _make_account(session)
    engine = PaperTradingEngine(session)

    # Run the EOD cycle on the latest seeded date
    summary = await engine.run_end_of_day(account.id, dates[-1])

    assert summary.orders_created >= 1
    assert summary.orders_filled >= 1
    assert summary.nav is not None
    assert summary.nav > 0

    # NAV row exists
    nav = (
        await session.execute(
            select(PaperNavPoint).where(PaperNavPoint.account_id == account.id)
        )
    ).scalar_one()
    assert nav.nav == pytest.approx(summary.nav)
    assert nav.cash <= account.initial_cash  # cash partially deployed
    assert nav.market_value > 0

    # At least one position created
    positions = (
        await session.execute(
            select(PaperPosition).where(
                PaperPosition.account_id == account.id, PaperPosition.quantity > 0
            )
        )
    ).scalars().all()
    assert positions
    assert all(p.quantity > 0 for p in positions)

    # Fills recorded with cost details
    fills = (
        await session.execute(select(PaperFill).where(PaperFill.account_id == account.id))
    ).scalars().all()
    assert fills
    assert all(f.commission > 0 for f in fills)  # default cost config applied
    assert all(f.side == "buy" for f in fills)

    # last_processed_date bumped
    await session.refresh(account)
    assert account.last_processed_date == dates[-1]


async def test_eod_is_idempotent_when_called_twice_for_same_date(session):
    symbols = [f"00000{i}.SZ" for i in range(1, 13)]
    dates = await _seed_universe(session, symbols, 25)
    account = await _make_account(session)
    engine = PaperTradingEngine(session)

    first = await engine.run_end_of_day(account.id, dates[-1])
    second = await engine.run_end_of_day(account.id, dates[-1])

    assert first.orders_created >= 1
    assert second.orders_created == 0  # idempotency guard

    fills_first = (
        await session.execute(select(PaperFill).where(PaperFill.account_id == account.id))
    ).scalars().all()
    assert fills_first  # first run produced fills, second was a no-op


async def test_pre_trade_check_rejects_over_single_name_cap(session):
    dates = await _seed_bars(session, "000001.SZ", 25)
    # Tiny account so a 95% gross target busts the 10% single-name cap.
    account = await _make_account(session, cash=100_000.0)
    engine = PaperTradingEngine(session)

    summary = await engine.run_end_of_day(account.id, dates[-1])

    # The order will be rejected by the single_name_cap rule.
    rejected_orders = (
        await session.execute(
            select(PaperOrder).where(
                PaperOrder.account_id == account.id, PaperOrder.status == "rejected"
            )
        )
    ).scalars().all()
    checks = (
        await session.execute(
            select(PaperPreTradeCheck).where(PaperPreTradeCheck.account_id == account.id)
        )
    ).scalars().all()

    assert summary.orders_rejected >= 1
    assert rejected_orders
    assert any(c.rule == "single_name_cap" and c.status == "fail" for c in checks)


async def test_eod_with_no_market_bars_is_a_noop(session):
    account = await _make_account(session)
    engine = PaperTradingEngine(session)
    summary = await engine.run_end_of_day(account.id, "2024-12-31")
    assert summary.orders_created == 0
    assert summary.nav is None  # no NAV written
    await session.refresh(account)
    assert account.last_processed_date is None  # date NOT bumped


async def test_breach_recorded_when_drawdown_exceeds_threshold(session):
    """Simulate a sharp drop after positions are built; expect daily-loss / drawdown breach."""
    symbols = [f"00000{i}.SZ" for i in range(1, 13)]
    dates = await _seed_universe(session, symbols, 25)

    crash_date = "2024-01-26"
    for sym_idx, symbol in enumerate(symbols):
        base = 10.0 + sym_idx * 0.5
        prev_close = base + 25 * 0.1
        crash_close = prev_close * 0.7  # ~ -30% crash
        session.add(
            MarketBarDaily(
                symbol=symbol,
                trade_date=crash_date,
                prev_close=prev_close,
                open=crash_close, high=crash_close + 0.05, low=crash_close - 0.05, close=crash_close,
                volume=1000, amount=crash_close * 1000, adjusted_close=crash_close,
                can_buy=True, can_sell=True,
            )
        )
    await session.commit()
    dates.append(crash_date)

    account = await _make_account(session, cash=100_000.0)
    engine = PaperTradingEngine(session)

    # Build a position on day 8 first.
    await engine.run_end_of_day(account.id, dates[-2])
    # Then the crash day — NAV will plunge.
    summary = await engine.run_end_of_day(account.id, crash_date)

    breaches = (
        await session.execute(
            select(PaperRiskBreach).where(PaperRiskBreach.account_id == account.id)
        )
    ).scalars().all()
    # Either daily_loss or max_drawdown should fire on this magnitude.
    assert summary.breaches >= 1
    assert breaches
    assert any(b.rule in {"daily_loss", "max_drawdown"} for b in breaches)
