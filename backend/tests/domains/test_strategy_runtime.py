"""Tests for the minimal strategy runtime interface."""

import pytest

from app.domains.strategy.runtime import (
    BaseStrategy,
    RebalancePlan,
    SignalSide,
    StrategyBar,
    StrategyContext,
    StrategyRunner,
    StrategySignal,
    StrategyState,
    TargetPosition,
)


class BuyBestCloseStrategy(BaseStrategy):
    name = "buy-best-close"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def initialize(self, context: StrategyContext) -> StrategyState:
        self.calls.append("initialize")
        return StrategyState(memory={"start": context.trade_date})

    def generate_signals(
        self,
        context: StrategyContext,
        bars: tuple[StrategyBar, ...],
        state: StrategyState,
    ) -> tuple[StrategySignal, ...]:
        self.calls.append("generate_signals")
        tradable = [bar for bar in bars if bar.can_buy and not bar.is_suspended]
        best = max(tradable, key=lambda bar: bar.valuation_price)
        return (
            StrategySignal(
                symbol=best.symbol,
                side=SignalSide.BUY,
                score=best.valuation_price,
                confidence=0.8,
                target_weight=0.6,
                reason="highest close",
            ),
        )

    def rebalance(
        self,
        context: StrategyContext,
        signals: tuple[StrategySignal, ...],
        state: StrategyState,
    ) -> RebalancePlan:
        self.calls.append("rebalance")
        targets = tuple(
            TargetPosition(symbol=signal.symbol, weight=signal.target_weight or 0.0, reason=signal.reason)
            for signal in signals
        )
        return RebalancePlan(trade_date=context.trade_date, targets=targets, cash_weight=0.4)


def test_strategy_runner_executes_lifecycle_in_order():
    strategy = BuyBestCloseStrategy()
    runner = StrategyRunner(strategy)
    context = StrategyContext(
        trade_date="2024-01-03",
        universe=("000001.SZ", "600000.SH"),
        portfolio_value=1_000_000,
        cash=1_000_000,
    )
    bars = (
        StrategyBar(symbol="000001.SZ", trade_date="2024-01-03", open=10, high=11, low=9, close=10, volume=100),
        StrategyBar(symbol="600000.SH", trade_date="2024-01-03", open=20, high=21, low=19, close=20, volume=100),
    )

    result = runner.run_daily(context, bars)

    assert strategy.calls == ["initialize", "generate_signals", "rebalance"]
    assert result.state.memory["start"] == "2024-01-03"
    assert result.signals[0].symbol == "600000.SH"
    assert result.signals[0].side == SignalSide.BUY
    assert result.rebalance.weight_for("600000.SH") == 0.6
    assert result.rebalance.cash_weight == 0.4


def test_context_and_rebalance_validate_invalid_inputs():
    with pytest.raises(ValueError, match="portfolio_value"):
        StrategyContext(trade_date="2024-01-03", universe=(), portfolio_value=0, cash=0)

    with pytest.raises(ValueError, match="duplicate target symbol"):
        RebalancePlan(
            trade_date="2024-01-03",
            targets=(
                TargetPosition(symbol="000001.SZ", weight=0.4),
                TargetPosition(symbol="000001.SZ", weight=0.1),
            ),
        )

    with pytest.raises(ValueError, match="gross weight"):
        RebalancePlan(
            trade_date="2024-01-03",
            targets=(TargetPosition(symbol="000001.SZ", weight=0.8),),
            cash_weight=0.3,
        )
