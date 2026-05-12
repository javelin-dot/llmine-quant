"""Minimal controlled strategy runtime interface."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class SignalSide(StrEnum):
    """Supported strategy signal directions."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class Position:
    """Current portfolio position for one symbol."""

    symbol: str
    quantity: float = 0.0
    market_value: float = 0.0
    weight: float = 0.0
    available_quantity: float | None = None


@dataclass(frozen=True, slots=True)
class StrategyBar:
    """Daily bar snapshot exposed to strategies."""

    symbol: str
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float | None = None
    adjusted_close: float | None = None
    can_buy: bool = True
    can_sell: bool = True
    is_suspended: bool = False
    is_limit_up: bool = False
    is_limit_down: bool = False

    @property
    def valuation_price(self) -> float:
        """Return the preferred price for signal and portfolio valuation."""
        return self.adjusted_close or self.close


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """Runtime context passed into every strategy lifecycle method."""

    trade_date: str
    universe: tuple[str, ...]
    portfolio_value: float
    cash: float
    positions: Mapping[str, Position] = field(default_factory=dict)
    strategy_id: str | None = None
    run_id: str | None = None
    params: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.trade_date:
            raise ValueError("trade_date is required")
        if self.portfolio_value <= 0:
            raise ValueError("portfolio_value must be positive")
        if self.cash < 0:
            raise ValueError("cash cannot be negative")
        object.__setattr__(self, "universe", tuple(self.universe))
        object.__setattr__(self, "positions", MappingProxyType(dict(self.positions)))
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class StrategyState:
    """Mutable strategy memory represented as an immutable payload per run step."""

    initialized: bool = True
    warmup_complete: bool = True
    memory: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory", MappingProxyType(dict(self.memory)))


@dataclass(frozen=True, slots=True)
class StrategySignal:
    """A strategy signal before portfolio construction."""

    symbol: str
    side: SignalSide
    score: float = 0.0
    confidence: float = 1.0
    target_weight: float | None = None
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("signal symbol is required")
        _validate_finite(self.score, "score")
        _validate_finite(self.confidence, "confidence")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.target_weight is not None:
            _validate_weight(self.target_weight, "target_weight")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class TargetPosition:
    """Target portfolio weight for one symbol after rebalance."""

    symbol: str
    weight: float
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("target symbol is required")
        _validate_weight(self.weight, "weight")


@dataclass(frozen=True, slots=True)
class RebalancePlan:
    """Portfolio target produced by a strategy for one trade date."""

    trade_date: str
    targets: tuple[TargetPosition, ...]
    cash_weight: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        targets = tuple(self.targets)
        seen: set[str] = set()
        for target in targets:
            if target.symbol in seen:
                raise ValueError(f"duplicate target symbol: {target.symbol}")
            seen.add(target.symbol)
        _validate_weight(self.cash_weight, "cash_weight")
        gross_weight = sum(abs(target.weight) for target in targets) + self.cash_weight
        if gross_weight > 1.000001:
            raise ValueError("target gross weight cannot exceed 1.0")
        object.__setattr__(self, "targets", targets)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def weight_for(self, symbol: str) -> float:
        """Return the target weight for a symbol, or zero when absent."""
        for target in self.targets:
            if target.symbol == symbol:
                return target.weight
        return 0.0


@dataclass(frozen=True, slots=True)
class StrategyRunResult:
    """Full output of one strategy run step."""

    state: StrategyState
    signals: tuple[StrategySignal, ...]
    rebalance: RebalancePlan


class BaseStrategy(ABC):
    """Minimal strategy lifecycle contract used by backtests and paper trading."""

    name: str = "base"
    version: str = "0.1.0"

    def initialize(self, context: StrategyContext) -> StrategyState:
        """Initialize strategy state before the first run step."""
        return StrategyState(memory={"strategy": self.name, "trade_date": context.trade_date})

    @abstractmethod
    def generate_signals(
        self,
        context: StrategyContext,
        bars: Sequence[StrategyBar],
        state: StrategyState,
    ) -> Sequence[StrategySignal]:
        """Generate raw buy/sell/hold signals for the current trade date."""
        raise NotImplementedError

    @abstractmethod
    def rebalance(
        self,
        context: StrategyContext,
        signals: Sequence[StrategySignal],
        state: StrategyState,
    ) -> RebalancePlan:
        """Convert signals into target portfolio weights."""
        raise NotImplementedError


class StrategyRunner:
    """Execute a strategy through initialize -> generate_signals -> rebalance."""

    def __init__(self, strategy: BaseStrategy) -> None:
        self.strategy = strategy
        self.state: StrategyState | None = None

    def initialize(self, context: StrategyContext) -> StrategyState:
        """Initialize and retain strategy state."""
        self.state = self.strategy.initialize(context)
        return self.state

    def run_daily(
        self,
        context: StrategyContext,
        bars: Sequence[StrategyBar],
    ) -> StrategyRunResult:
        """Run one daily strategy step."""
        state = self.state or self.initialize(context)
        signals = tuple(self.strategy.generate_signals(context, tuple(bars), state))
        plan = self.strategy.rebalance(context, signals, state)
        self.state = state
        return StrategyRunResult(state=state, signals=signals, rebalance=plan)


def _validate_weight(value: float, field_name: str) -> None:
    _validate_finite(value, field_name)
    if not 0 <= value <= 1:
        raise ValueError(f"{field_name} must be between 0 and 1")


def _validate_finite(value: float, field_name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
