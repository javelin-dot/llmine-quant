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


class MomentumStrategy(BaseStrategy):
    """Cross-sectional momentum: rank by recent N-day return, buy top performers."""

    name = "momentum"
    version = "0.1.0"

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.lookback: int = int(p.get("lookback", 20))
        self.skip: int = int(p.get("skip", 1))
        self.max_positions: int = int(p.get("max_positions", 5))
        self.target_gross: float = float(p.get("target_gross", 0.95))

    def initialize(self, context: StrategyContext) -> StrategyState:
        return StrategyState(memory={"strategy": self.name, "lookback": self.lookback})

    def generate_signals(
        self,
        context: StrategyContext,
        bars: tuple[StrategyBar, ...],
        state: StrategyState,
    ) -> tuple[StrategySignal, ...]:
        history = _history_by_symbol(bars, context.trade_date)
        needed = self.lookback + self.skip + 1
        signals: list[StrategySignal] = []
        for symbol in context.universe:
            sym_hist = history.get(symbol, [])
            if len(sym_hist) < needed:
                signals.append(StrategySignal(symbol=symbol, side=SignalSide.HOLD, confidence=0.1, reason="history too short"))
                continue
            latest = sym_hist[-1]
            if latest.is_suspended:
                signals.append(StrategySignal(symbol=symbol, side=SignalSide.HOLD, confidence=0.0, reason="suspended"))
                continue
            end_price = sym_hist[-(self.skip + 1)].valuation_price
            start_price = sym_hist[-(self.lookback + self.skip + 1)].valuation_price if len(sym_hist) > self.lookback + self.skip else sym_hist[0].valuation_price
            momentum = end_price / start_price - 1 if start_price > 0 else 0.0
            signals.append(
                StrategySignal(
                    symbol=symbol,
                    side=SignalSide.BUY if momentum > 0 and latest.can_buy else SignalSide.SELL,
                    score=momentum,
                    confidence=min(1.0, 0.5 + abs(momentum) * 3),
                    reason=f"momentum {momentum:.3f} over {self.lookback}d",
                )
            )
        return tuple(signals)

    def rebalance(
        self,
        context: StrategyContext,
        signals: tuple[StrategySignal, ...],
        state: StrategyState,
    ) -> RebalancePlan:
        buys = sorted((s for s in signals if s.side == SignalSide.BUY), key=lambda s: s.score or 0.0, reverse=True)[: self.max_positions]
        weight = self.target_gross / len(buys) if buys else 0.0
        targets = tuple(TargetPosition(symbol=s.symbol, weight=weight, reason=s.reason) for s in buys)
        used = sum(t.weight for t in targets)
        return RebalancePlan(trade_date=context.trade_date, targets=targets, cash_weight=max(0.0, 1 - used))


class MeanReversionStrategy(BaseStrategy):
    """Short-term mean reversion: buy oversold symbols based on z-score of daily returns."""

    name = "mean_reversion"
    version = "0.1.0"

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.lookback: int = int(p.get("lookback", 20))
        self.z_threshold: float = float(p.get("z_threshold", 1.5))
        self.max_positions: int = int(p.get("max_positions", 10))
        self.target_gross: float = float(p.get("target_gross", 0.90))

    def initialize(self, context: StrategyContext) -> StrategyState:
        return StrategyState(memory={"strategy": self.name})

    def generate_signals(
        self,
        context: StrategyContext,
        bars: tuple[StrategyBar, ...],
        state: StrategyState,
    ) -> tuple[StrategySignal, ...]:
        import math as _math
        history = _history_by_symbol(bars, context.trade_date)
        signals: list[StrategySignal] = []
        for symbol in context.universe:
            sym_hist = history.get(symbol, [])
            if len(sym_hist) < self.lookback + 1:
                signals.append(StrategySignal(symbol=symbol, side=SignalSide.HOLD, confidence=0.1, reason="history too short"))
                continue
            latest = sym_hist[-1]
            if latest.is_suspended:
                signals.append(StrategySignal(symbol=symbol, side=SignalSide.HOLD, confidence=0.0, reason="suspended"))
                continue
            window = sym_hist[-(self.lookback + 1):]
            prices = [b.valuation_price for b in window]
            daily_rets = [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices))]
            if not daily_rets:
                signals.append(StrategySignal(symbol=symbol, side=SignalSide.HOLD, confidence=0.1, reason="no returns"))
                continue
            mean = sum(daily_rets) / len(daily_rets)
            var = sum((r - mean) ** 2 for r in daily_rets) / len(daily_rets)
            std = _math.sqrt(var) if var > 0 else 0.0
            today_ret = daily_rets[-1]
            z = (today_ret - mean) / std if std > 0 else 0.0
            if z < -self.z_threshold and latest.can_buy:
                signals.append(StrategySignal(symbol=symbol, side=SignalSide.BUY, score=-z, confidence=min(1.0, abs(z) / 3), reason=f"z={z:.2f} oversold"))
            elif symbol in context.positions and z > self.z_threshold * 0.5:
                signals.append(StrategySignal(symbol=symbol, side=SignalSide.SELL, score=z, confidence=0.6, target_weight=0.0, reason=f"z={z:.2f} recovered"))
            else:
                hold_w = context.positions[symbol].weight if symbol in context.positions else None
                signals.append(StrategySignal(symbol=symbol, side=SignalSide.HOLD, confidence=0.3, target_weight=hold_w, reason=f"z={z:.2f} neutral"))
        return tuple(signals)

    def rebalance(
        self,
        context: StrategyContext,
        signals: tuple[StrategySignal, ...],
        state: StrategyState,
    ) -> RebalancePlan:
        hold_targets = [TargetPosition(symbol=s.symbol, weight=s.target_weight, reason=s.reason) for s in signals if s.side == SignalSide.HOLD and s.target_weight is not None and s.target_weight > 0]
        hold_weight = sum(t.weight for t in hold_targets)
        remaining = max(0.0, self.target_gross - hold_weight)
        buys = sorted((s for s in signals if s.side == SignalSide.BUY), key=lambda s: s.score or 0.0, reverse=True)[: self.max_positions]
        buy_w = remaining / len(buys) if buys else 0.0
        buy_targets = [TargetPosition(symbol=s.symbol, weight=buy_w, reason=s.reason) for s in buys if buy_w > 0]
        targets = tuple(hold_targets + buy_targets)
        used = sum(t.weight for t in targets)
        return RebalancePlan(trade_date=context.trade_date, targets=targets, cash_weight=max(0.0, 1 - used))


BUILTIN_STRATEGIES: dict[str, type[BaseStrategy]] = {
    "dual_ma": DualMovingAverageStrategy,
    "dual-moving-average": DualMovingAverageStrategy,
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
}


def create_builtin_strategy(name: str, params: dict[str, Any] | None = None) -> BaseStrategy:
    """Instantiate a built-in controlled strategy by name."""
    strategy_cls = BUILTIN_STRATEGIES.get(name)
    if strategy_cls is None:
        raise ValueError(f"unknown built-in strategy: {name}")
    if strategy_cls is DualMovingAverageStrategy:
        return DualMovingAverageStrategy(DualMovingAverageConfig.from_params(params or {}))
    if strategy_cls is MomentumStrategy:
        return MomentumStrategy(params)
    if strategy_cls is MeanReversionStrategy:
        return MeanReversionStrategy(params)
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
