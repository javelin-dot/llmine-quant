"""Tests for the daily research backtest loop."""

import math

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.backtest.models import (
    BacktestMetric,
    BacktestRun,
    BacktestTask,
    EquityPoint,
    WalkForwardFold,
)
from app.domains.data.models import MarketBarDaily
from app.services.daily_backtest import (
    BacktestCostConfig,
    BacktestDataError,
    DailyBacktestConfig,
    DailyBacktestEngine,
)

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
    async with session_factory() as test_session:
        yield test_session

    await engine.dispose()


async def test_daily_backtest_generates_previous_history_signal_and_buys(session):
    await _seed_bars(session, "000001.SZ", [10, 11, 12, 13])
    engine = DailyBacktestEngine(session)

    result = await engine.run(
        DailyBacktestConfig(
            universe=("000001.SZ",),
            start_date="2024-01-01",
            end_date="2024-01-04",
            initial_cash=1_000,
            strategy_params={"short_window": 2, "long_window": 3, "target_gross": 0.5},
            cost_config=ZERO_COST,
        )
    )

    assert len(result.equity_curve) == 4
    assert [trade.trade_date for trade in result.trades] == ["2024-01-04"]
    assert result.trades[0].side == "buy"
    assert result.trades[0].quantity == pytest.approx(1_000 * 0.5 / 13)
    assert result.final_cash == pytest.approx(500)
    assert result.positions[0].symbol == "000001.SZ"
    assert result.positions[0].weight == pytest.approx(0.5)


async def test_daily_backtest_respects_current_day_buy_flag(session):
    await _seed_bars(session, "000001.SZ", [10, 11, 12, 13], blocked_buy_dates={"2024-01-04"})
    engine = DailyBacktestEngine(session)

    result = await engine.run(
        DailyBacktestConfig(
            universe=("000001.SZ",),
            start_date="2024-01-01",
            end_date="2024-01-04",
            initial_cash=1_000,
            strategy_params={"short_window": 2, "long_window": 3, "target_gross": 0.5},
            cost_config=ZERO_COST,
        )
    )

    assert result.trades == ()
    assert result.positions == ()
    assert result.final_value == pytest.approx(1_000)


async def test_daily_backtest_raises_when_no_bars_found(session):
    engine = DailyBacktestEngine(session)

    with pytest.raises(BacktestDataError, match="no market bars"):
        await engine.run(
            DailyBacktestConfig(
                universe=("000001.SZ",),
                start_date="2024-01-01",
                end_date="2024-01-04",
            )
        )


async def test_daily_backtest_applies_commission_stamp_tax_and_slippage(session):
    await _seed_bars(session, "000001.SZ", [10, 11, 12, 13, 12, 11, 10])
    engine = DailyBacktestEngine(session)
    cost_config = BacktestCostConfig(
        commission_rate=0.001,
        min_commission=2,
        stamp_tax_rate=0.002,
        slippage_bps=10,
    )

    result = await engine.run(
        DailyBacktestConfig(
            universe=("000001.SZ",),
            start_date="2024-01-01",
            end_date="2024-01-07",
            initial_cash=10_000,
            strategy_params={"short_window": 2, "long_window": 3, "target_gross": 0.5},
            cost_config=cost_config,
        )
    )

    first_buy = next(trade for trade in result.trades if trade.side == "buy")
    sell_trade = next(trade for trade in result.trades if trade.side == "sell")

    assert first_buy.trade_date == "2024-01-04"
    assert first_buy.price == pytest.approx(13 * 1.001)
    assert first_buy.commission == pytest.approx(first_buy.amount * 0.001)
    assert first_buy.stamp_tax == 0
    assert first_buy.slippage == pytest.approx(first_buy.quantity * 13 * 0.001)
    assert first_buy.net_cash_flow == pytest.approx(-(first_buy.amount + first_buy.commission))

    assert sell_trade.price < 10
    assert sell_trade.stamp_tax == pytest.approx(sell_trade.amount * 0.002)
    assert sell_trade.total_cost == pytest.approx(
        sell_trade.commission + sell_trade.stamp_tax + sell_trade.slippage
    )
    assert result.total_cost == pytest.approx(sum(trade.total_cost for trade in result.trades))


async def test_daily_backtest_calculates_core_metrics(session):
    await _seed_bars(session, "000001.SZ", [10, 11, 12, 13, 14])
    engine = DailyBacktestEngine(session)

    result = await engine.run(
        DailyBacktestConfig(
            universe=("000001.SZ",),
            start_date="2024-01-01",
            end_date="2024-01-05",
            initial_cash=1_000,
            strategy_params={"short_window": 2, "long_window": 3, "target_gross": 0.5},
            cost_config=ZERO_COST,
        )
    )

    values = [1_000] + [point.value for point in result.equity_curve]
    daily_returns = [
        values[index] / values[index - 1] - 1
        for index in range(1, len(values))
    ]
    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((daily_return - mean_return) ** 2 for daily_return in daily_returns) / (
        len(daily_returns) - 1
    )
    average_equity = sum(point.value for point in result.equity_curve) / len(result.equity_curve)

    assert result.metrics.cumulative_return == pytest.approx(result.final_value / 1_000 - 1)
    assert result.metrics.annual_return == pytest.approx((result.final_value / 1_000) ** (252 / 5) - 1)
    assert result.metrics.max_drawdown == 0
    assert result.metrics.sharpe_ratio == pytest.approx(mean_return / math.sqrt(variance) * math.sqrt(252))
    assert result.metrics.win_rate == 1.0
    assert result.metrics.turnover == pytest.approx(sum(trade.amount for trade in result.trades) / average_equity)


async def test_daily_backtest_persists_task_run_metrics_and_equity_points(session):
    await _seed_bars(session, "000001.SZ", [10, 11, 12, 13, 14])
    engine = DailyBacktestEngine(session)

    result = await engine.run_and_persist(
        DailyBacktestConfig(
            universe=("000001.SZ",),
            start_date="2024-01-01",
            end_date="2024-01-05",
            initial_cash=1_000,
            strategy_params={"short_window": 2, "long_window": 3, "target_gross": 0.5},
            cost_config=ZERO_COST,
        )
    )

    task = await session.get(BacktestTask, result.task_id)
    run = await session.get(BacktestRun, result.run_id)
    metric = (
        await session.execute(select(BacktestMetric).where(BacktestMetric.run_id == result.run_id))
    ).scalar_one()
    equity_points = (
        await session.execute(
            select(EquityPoint)
            .where(EquityPoint.run_id == result.run_id)
            .order_by(EquityPoint.trade_date)
        )
    ).scalars().all()

    assert task is not None
    assert task.status == "completed"
    assert task.strategy_version_id == "dual_ma"
    assert run is not None
    assert run.task_id == task.id
    assert run.status == "completed"
    assert run.started_at is not None
    assert run.ended_at is not None
    assert metric.cumulative_return == pytest.approx(result.metrics.cumulative_return)
    assert metric.annual_return == pytest.approx(result.metrics.annual_return)
    assert metric.max_drawdown == result.metrics.max_drawdown
    assert metric.sharpe_ratio == pytest.approx(result.metrics.sharpe_ratio)
    assert metric.win_rate == result.metrics.win_rate
    assert metric.turnover == pytest.approx(result.metrics.turnover)
    assert [point.trade_date for point in equity_points] == [point.trade_date for point in result.equity_curve]
    assert [point.value for point in equity_points] == pytest.approx([point.value for point in result.equity_curve])


async def test_daily_backtest_splits_in_sample_and_out_of_sample(session):
    """When `in_sample_end_date` is set, IS/OOS metrics + phase tags are persisted."""
    await _seed_bars(session, "000001.SZ", [10, 11, 12, 13, 14, 13.5, 14.5, 15.5])
    engine = DailyBacktestEngine(session)

    result = await engine.run_and_persist(
        DailyBacktestConfig(
            universe=("000001.SZ",),
            start_date="2024-01-01",
            end_date="2024-01-08",
            initial_cash=1_000,
            strategy_params={"short_window": 2, "long_window": 3, "target_gross": 0.5},
            cost_config=ZERO_COST,
            in_sample_end_date="2024-01-04",
        )
    )

    # Runtime result carries IS / OOS metrics
    assert result.in_sample_end_date == "2024-01-04"
    assert result.is_metrics is not None
    assert result.oos_metrics is not None

    # 3 BacktestMetric rows persisted: all / is / oos
    metric_rows = (
        await session.execute(select(BacktestMetric).where(BacktestMetric.run_id == result.run_id))
    ).scalars().all()
    by_segment = {m.segment: m for m in metric_rows}
    assert set(by_segment) == {"all", "is", "oos"}
    assert by_segment["is"].cumulative_return == pytest.approx(result.is_metrics.cumulative_return)
    assert by_segment["oos"].cumulative_return == pytest.approx(result.oos_metrics.cumulative_return)

    # EquityPoint.phase reflects the split
    points = (
        await session.execute(
            select(EquityPoint)
            .where(EquityPoint.run_id == result.run_id)
            .order_by(EquityPoint.trade_date)
        )
    ).scalars().all()
    phases = {p.trade_date: p.phase for p in points}
    assert phases["2024-01-01"] == "is"
    assert phases["2024-01-04"] == "is"
    assert phases["2024-01-05"] == "oos"
    assert phases["2024-01-08"] == "oos"


async def test_walk_forward_generates_and_persists_folds(session):
    """Walk-forward produces N fold rows linked to the parent run."""
    closes = [10 + i * 0.1 for i in range(20)]
    await _seed_bars(session, "000001.SZ", closes)
    engine = DailyBacktestEngine(session)

    result, summaries = await engine.run_walk_forward(
        DailyBacktestConfig(
            universe=("000001.SZ",),
            start_date="2024-01-01",
            end_date="2024-01-20",
            initial_cash=1_000,
            strategy_params={"short_window": 2, "long_window": 3, "target_gross": 0.5},
            cost_config=ZERO_COST,
        ),
        folds=4,
        train_ratio=0.7,
    )

    assert result.run_id is not None
    assert len(summaries) == 4

    rows = (
        await session.execute(
            select(WalkForwardFold)
            .where(WalkForwardFold.run_id == result.run_id)
            .order_by(WalkForwardFold.fold_index)
        )
    ).scalars().all()
    assert [r.fold_index for r in rows] == [0, 1, 2, 3]
    for r in rows:
        # Train window must precede test window
        assert r.train_start <= r.train_end < r.test_start <= r.test_end
        assert r.train_return is not None
        assert r.test_return is not None


async def test_walk_forward_rejects_too_few_bars(session):
    await _seed_bars(session, "000001.SZ", [10, 11, 12, 13])
    engine = DailyBacktestEngine(session)
    with pytest.raises(BacktestDataError, match="walk-forward"):
        await engine.run_walk_forward(
            DailyBacktestConfig(
                universe=("000001.SZ",),
                start_date="2024-01-01",
                end_date="2024-01-04",
                initial_cash=1_000,
                strategy_params={"short_window": 2, "long_window": 3, "target_gross": 0.5},
                cost_config=ZERO_COST,
            ),
            folds=4,
        )


async def test_daily_backtest_rejects_invalid_in_sample_end_date():
    """Split must be inside [start_date, end_date)."""
    with pytest.raises(ValueError, match="in_sample_end_date"):
        DailyBacktestConfig(
            universe=("000001.SZ",),
            start_date="2024-01-01",
            end_date="2024-01-05",
            in_sample_end_date="2024-01-05",  # equals end_date — no OOS days
        )

    with pytest.raises(ValueError, match="in_sample_end_date"):
        DailyBacktestConfig(
            universe=("000001.SZ",),
            start_date="2024-01-02",
            end_date="2024-01-05",
            in_sample_end_date="2024-01-01",  # before start_date
        )


async def _seed_bars(
    session,
    symbol: str,
    closes: list[float],
    *,
    blocked_buy_dates: set[str] | None = None,
) -> None:
    blocked_buy_dates = blocked_buy_dates or set()
    for index, close in enumerate(closes, start=1):
        trade_date = f"2024-01-{index:02d}"
        session.add(
            MarketBarDaily(
                symbol=symbol,
                trade_date=trade_date,
                prev_close=closes[index - 2] if index > 1 else None,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=1000,
                amount=close * 1000,
                adjusted_close=close,
                is_limit_up=trade_date in blocked_buy_dates,
                can_buy=trade_date not in blocked_buy_dates,
                can_sell=True,
            )
        )
    await session.commit()
