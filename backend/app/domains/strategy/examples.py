"""Built-in controlled strategies used by research backtests."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.domains.strategy.runtime import (
    BaseStrategy,
    RebalancePlan,
    SignalSide,
    StrategyBar,
    StrategyContext,
    StrategySignal,
    StrategyState,
    TargetPosition,
)


@dataclass(frozen=True, slots=True)
class DualMovingAverageConfig:
    """Parameters for the built-in dual moving average strategy."""

    short_window: int = 5
    long_window: int = 20
    max_positions: int = 5
    target_gross: float = 0.95

    def __post_init__(self) -> None:
        if self.short_window <= 0:
            raise ValueError("short_window must be positive")
        if self.long_window <= self.short_window:
            raise ValueError("long_window must be greater than short_window")
        if self.max_positions <= 0:
            raise ValueError("max_positions must be positive")
        if not 0 <= self.target_gross <= 1:
            raise ValueError("target_gross must be between 0 and 1")

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> DualMovingAverageConfig:
        """Build config from API/backtest params."""
        return cls(
            short_window=int(params.get("short_window", params.get("shortWindow", 5))),
            long_window=int(params.get("long_window", params.get("longWindow", 20))),
            max_positions=int(params.get("max_positions", params.get("maxPositions", 5))),
            target_gross=float(params.get("target_gross", params.get("targetGross", 0.95))),
        )


class DualMovingAverageStrategy(BaseStrategy):
    """A-share long-only dual moving average example strategy."""

    name = "dual-moving-average"
    version = "0.1.0"

    def __init__(self, config: DualMovingAverageConfig | None = None) -> None:
        self.config = config or DualMovingAverageConfig()

    def initialize(self, context: StrategyContext) -> StrategyState:
        """Store immutable parameters in strategy state."""
        return StrategyState(
            memory={
                "strategy": self.name,
                "short_window": self.config.short_window,
                "long_window": self.config.long_window,
                "max_positions": self.config.max_positions,
                "target_gross": self.config.target_gross,
                "start_date": context.trade_date,
            }
        )

    def generate_signals(
        self,
        context: StrategyContext,
        bars: tuple[StrategyBar, ...],
        state: StrategyState,
    ) -> tuple[StrategySignal, ...]:
        """Generate BUY when short MA is above long MA, otherwise SELL/HOLD."""
        history = _history_by_symbol(bars, context.trade_date)
        signals: list[StrategySignal] = []

        for symbol in context.universe:
            symbol_history = history.get(symbol, [])
            if len(symbol_history) < self.config.long_window:
                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        side=SignalSide.HOLD,
                        confidence=0.2,
                        reason="insufficient moving average history",
                    )
                )
                continue

            latest = symbol_history[-1]
            if latest.is_suspended:
                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        side=SignalSide.HOLD,
                        confidence=0.0,
                        target_weight=context.positions.get(symbol, None).weight
                        if symbol in context.positions
                        else None,
                        reason="suspended",
                    )
                )
                continue

            closes = [bar.valuation_price for bar in symbol_history]
            short_ma = _mean(closes[-self.config.short_window :])
            long_ma = _mean(closes[-self.config.long_window :])
            spread = short_ma / long_ma - 1
            confidence = min(1.0, 0.5 + abs(spread) * 10)

            if spread > 0 and latest.can_buy:
                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        side=SignalSide.BUY,
                        score=spread,
                        confidence=confidence,
                        reason=f"short_ma {short_ma:.4f} above long_ma {long_ma:.4f}",
                    )
                )
            elif symbol in context.positions and context.positions[symbol].weight > 0 and not latest.can_sell:
                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        side=SignalSide.HOLD,
                        score=spread,
                        confidence=confidence,
                        target_weight=context.positions[symbol].weight,
                        reason="cannot sell under current A-share trading flag",
                    )
                )
            elif symbol in context.positions and context.positions[symbol].weight > 0:
                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        side=SignalSide.SELL,
                        score=spread,
                        confidence=confidence,
                        target_weight=0.0,
                        reason=f"short_ma {short_ma:.4f} not above long_ma {long_ma:.4f}",
                    )
                )
            else:
                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        side=SignalSide.HOLD,
                        score=spread,
                        confidence=confidence,
                        reason=f"short_ma {short_ma:.4f} not above long_ma {long_ma:.4f}",
                    )
                )

        return tuple(signals)

    def rebalance(
        self,
        context: StrategyContext,
        signals: tuple[StrategySignal, ...],
        state: StrategyState,
    ) -> RebalancePlan:
        """Convert positive MA signals into equal-weight target positions."""
        hold_targets = [
            TargetPosition(symbol=signal.symbol, weight=signal.target_weight, reason=signal.reason)
            for signal in signals
            if signal.side == SignalSide.HOLD and signal.target_weight is not None and signal.target_weight > 0
        ]
        hold_weight = sum(target.weight for target in hold_targets)
        remaining_gross = max(0.0, self.config.target_gross - hold_weight)

        buy_signals = sorted(
            (signal for signal in signals if signal.side == SignalSide.BUY),
            key=lambda signal: (signal.score, signal.confidence),
            reverse=True,
        )[: self.config.max_positions]
        buy_weight = remaining_gross / len(buy_signals) if buy_signals else 0.0
        buy_targets = [
            TargetPosition(symbol=signal.symbol, weight=buy_weight, reason=signal.reason)
            for signal in buy_signals
            if buy_weight > 0
        ]
        targets = tuple(hold_targets + buy_targets)
        used_weight = sum(target.weight for target in targets)
        return RebalancePlan(
            trade_date=context.trade_date,
            targets=targets,
            cash_weight=max(0.0, 1 - used_weight),
            metadata={
                "strategy": self.name,
                "short_window": self.config.short_window,
                "long_window": self.config.long_window,
            },
        )


BUILTIN_STRATEGIES: dict[str, type[BaseStrategy]] = {
    "dual_ma": DualMovingAverageStrategy,
    "dual-moving-average": DualMovingAverageStrategy,
}


def create_builtin_strategy(name: str, params: dict[str, Any] | None = None) -> BaseStrategy:
    """Instantiate a built-in controlled strategy by name."""
    strategy_cls = BUILTIN_STRATEGIES.get(name)
    if strategy_cls is None:
        raise ValueError(f"unknown built-in strategy: {name}")
    if strategy_cls is DualMovingAverageStrategy:
        return DualMovingAverageStrategy(DualMovingAverageConfig.from_params(params or {}))
    return strategy_cls()


def _history_by_symbol(bars: tuple[StrategyBar, ...], trade_date: str) -> dict[str, list[StrategyBar]]:
    history: dict[str, list[StrategyBar]] = defaultdict(list)
    for bar in bars:
        if bar.trade_date <= trade_date:
            history[bar.symbol].append(bar)
    for symbol_history in history.values():
        symbol_history.sort(key=lambda bar: bar.trade_date)
    return history


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)
