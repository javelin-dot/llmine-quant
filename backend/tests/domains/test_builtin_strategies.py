"""Tests for built-in controlled strategies."""

import pytest

from app.domains.strategy.examples import (
    DualMovingAverageConfig,
    DualMovingAverageStrategy,
    create_builtin_strategy,
)
from app.domains.strategy.runtime import Position, SignalSide, StrategyBar, StrategyContext, StrategyRunner


def _bars(symbol: str, closes: list[float]) -> tuple[StrategyBar, ...]:
    return tuple(
        StrategyBar(
            symbol=symbol,
            trade_date=f"2024-01-{day:02d}",
            open=close,
            high=close + 0.2,
            low=close - 0.2,
            close=close,
            volume=1000,
        )
        for day, close in enumerate(closes, start=1)
    )


def test_dual_moving_average_generates_buy_and_equal_weight_target():
    strategy = DualMovingAverageStrategy(
        DualMovingAverageConfig(short_window=2, long_window=3, max_positions=2, target_gross=0.8)
    )
    runner = StrategyRunner(strategy)
    context = StrategyContext(
        trade_date="2024-01-04",
        universe=("000001.SZ", "600000.SH"),
        portfolio_value=1_000_000,
        cash=1_000_000,
    )
    bars = _bars("000001.SZ", [10, 10.2, 10.6, 11.0]) + _bars("600000.SH", [20, 19.8, 19.4, 19.0])

    result = runner.run_daily(context, bars)

    buy_signals = [signal for signal in result.signals if signal.side == SignalSide.BUY]
    assert [signal.symbol for signal in buy_signals] == ["000001.SZ"]
    assert result.rebalance.weight_for("000001.SZ") == 0.8
    assert result.rebalance.weight_for("600000.SH") == 0.0
    assert result.rebalance.cash_weight == pytest.approx(0.2)


def test_dual_moving_average_holds_when_history_is_insufficient():
    strategy = DualMovingAverageStrategy(DualMovingAverageConfig(short_window=2, long_window=5))
    runner = StrategyRunner(strategy)
    context = StrategyContext(
        trade_date="2024-01-03",
        universe=("000001.SZ",),
        portfolio_value=1_000_000,
        cash=1_000_000,
    )

    result = runner.run_daily(context, _bars("000001.SZ", [10, 10.2, 10.4]))

    assert result.signals[0].side == SignalSide.HOLD
    assert result.signals[0].reason == "insufficient moving average history"
    assert result.rebalance.targets == ()
    assert result.rebalance.cash_weight == 1.0


def test_dual_moving_average_preserves_position_when_cannot_sell():
    strategy = DualMovingAverageStrategy(DualMovingAverageConfig(short_window=2, long_window=3, target_gross=0.8))
    runner = StrategyRunner(strategy)
    context = StrategyContext(
        trade_date="2024-01-04",
        universe=("000001.SZ",),
        portfolio_value=1_000_000,
        cash=500_000,
        positions={"000001.SZ": Position(symbol="000001.SZ", weight=0.5, market_value=500_000)},
    )
    bars = list(_bars("000001.SZ", [10, 9.8, 9.6, 9.4]))
    bars[-1] = StrategyBar(
        symbol="000001.SZ",
        trade_date="2024-01-04",
        open=9.4,
        high=9.6,
        low=9.2,
        close=9.4,
        volume=1000,
        can_sell=False,
        is_limit_down=True,
    )

    result = runner.run_daily(context, tuple(bars))

    assert result.signals[0].side == SignalSide.HOLD
    assert result.rebalance.weight_for("000001.SZ") == 0.5


def test_builtin_strategy_factory_validates_name_and_params():
    strategy = create_builtin_strategy("dual_ma", {"shortWindow": 2, "longWindow": 4})

    assert isinstance(strategy, DualMovingAverageStrategy)

    with pytest.raises(ValueError, match="unknown built-in strategy"):
        create_builtin_strategy("does-not-exist")

    with pytest.raises(ValueError, match="long_window"):
        create_builtin_strategy("dual_ma", {"shortWindow": 5, "longWindow": 5})
