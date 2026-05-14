"""Daily research backtest loop for controlled built-in strategies."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_class import now_utc
from app.domains.backtest.models import (
    BacktestMetric,
    BacktestRun,
    BacktestTask,
    BacktestTrade,
    EquityPoint,
    WalkForwardFold,
)
from app.domains.data.models import MarketBarDaily
from app.domains.strategy.examples import create_builtin_strategy
from app.domains.strategy.runtime import Position, StrategyBar, StrategyContext, StrategyRunner


class BacktestDataError(ValueError):
    """Raised when a backtest cannot load enough market data."""


@dataclass(frozen=True, slots=True)
class BacktestCostConfig:
    """Research trading cost assumptions."""

    commission_rate: float = 0.0003
    min_commission: float = 5.0
    stamp_tax_rate: float = 0.001
    slippage_bps: float = 1.0

    def __post_init__(self) -> None:
        for field_name in ("commission_rate", "min_commission", "stamp_tax_rate", "slippage_bps"):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} cannot be negative")
        if self.slippage_bps >= 10_000:
            raise ValueError("slippage_bps must be lower than 10000")

    @property
    def slippage_rate(self) -> float:
        """Return slippage as a decimal rate."""
        return self.slippage_bps / 10_000


@dataclass(frozen=True, slots=True)
class ExecutedTrade:
    """A filled simulated trade."""

    trade_date: str
    symbol: str
    side: str
    quantity: float
    price: float
    amount: float
    target_weight: float
    commission: float = 0.0
    stamp_tax: float = 0.0
    slippage: float = 0.0
    total_cost: float = 0.0
    net_cash_flow: float = 0.0
    reason: str = ""


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    """End-of-day position valuation."""

    symbol: str
    quantity: float
    price: float
    market_value: float
    weight: float


@dataclass(frozen=True, slots=True)
class DailyEquityPoint:
    """End-of-day equity curve point."""

    trade_date: str
    value: float
    cash: float
    drawdown: float
    positions: tuple[PositionSnapshot, ...]


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    """Core performance metrics for a completed backtest."""

    cumulative_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    turnover: float
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    volatility: float = 0.0
    profit_factor: float = 0.0


@dataclass(frozen=True, slots=True)
class WalkForwardFoldSummary:
    """One walk-forward fold's train/test metrics (in-memory representation)."""

    fold_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_metrics: "BacktestMetrics"
    test_metrics: "BacktestMetrics"


@dataclass(frozen=True, slots=True)
class DailyBacktestResult:
    """Result of a completed daily backtest loop."""

    strategy_name: str
    start_date: str
    end_date: str
    initial_cash: float
    final_value: float
    final_cash: float
    total_cost: float
    metrics: BacktestMetrics
    equity_curve: tuple[DailyEquityPoint, ...]
    trades: tuple[ExecutedTrade, ...]
    positions: tuple[PositionSnapshot, ...]
    task_id: str | None = None
    run_id: str | None = None
    in_sample_end_date: str | None = None
    is_metrics: BacktestMetrics | None = None
    oos_metrics: BacktestMetrics | None = None
    monthly_returns: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DailyBacktestConfig:
    """Configuration for a daily research backtest.

    ``in_sample_end_date`` (inclusive) splits the run into IS / OOS segments.
    When omitted, the full range is treated as in-sample.
    """

    universe: tuple[str, ...]
    start_date: str
    end_date: str
    strategy_name: str = "dual_ma"
    initial_cash: float = 1_000_000.0
    strategy_params: Mapping[str, Any] = field(default_factory=dict)
    cost_config: BacktestCostConfig = field(default_factory=BacktestCostConfig)
    in_sample_end_date: str | None = None

    def __post_init__(self) -> None:
        if not self.universe:
            raise ValueError("universe is required")
        if not self.start_date or not self.end_date:
            raise ValueError("start_date and end_date are required")
        if self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if self.in_sample_end_date is not None:
            if self.in_sample_end_date < self.start_date or self.in_sample_end_date >= self.end_date:
                raise ValueError(
                    "in_sample_end_date must be within [start_date, end_date) "
                    "so the OOS segment has at least one day"
                )

        object.__setattr__(self, "universe", tuple(symbol.upper() for symbol in self.universe))
        object.__setattr__(self, "strategy_params", dict(self.strategy_params))


class DailyBacktestEngine:
    """Run a minimal daily backtest from persisted daily bars."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self, config: DailyBacktestConfig) -> DailyBacktestResult:
        """Execute the backtest loop for the supplied config."""
        bars = await self._load_bars(config)
        if not bars:
            raise BacktestDataError("no market bars found for the requested universe and date range")

        bars_by_date = _group_bars_by_date(bars)
        trade_dates = sorted(bars_by_date)
        strategy = create_builtin_strategy(config.strategy_name, dict(config.strategy_params))
        runner = StrategyRunner(strategy)

        cash = config.initial_cash
        quantities: dict[str, float] = {}
        last_prices: dict[str, float] = {}
        history: list[MarketBarDaily] = []
        equity_curve: list[DailyEquityPoint] = []
        trades: list[ExecutedTrade] = []
        peak_value = config.initial_cash

        for trade_date in trade_dates:
            today_bars = {bar.symbol: bar for bar in bars_by_date[trade_date]}
            for symbol, bar in today_bars.items():
                last_prices[symbol] = _valuation_price(bar)

            portfolio_value = _portfolio_value(cash, quantities, last_prices)
            context = StrategyContext(
                trade_date=trade_date,
                universe=config.universe,
                portfolio_value=portfolio_value,
                cash=cash,
                positions=_strategy_positions(quantities, last_prices, portfolio_value),
                params=config.strategy_params,
            )
            run_result = runner.run_daily(context, [_to_strategy_bar(bar) for bar in history])

            cash = _execute_rebalance(
                trade_date=trade_date,
                cash=cash,
                quantities=quantities,
                today_bars=today_bars,
                last_prices=last_prices,
                target_weights={target.symbol: target.weight for target in run_result.rebalance.targets},
                target_reasons={target.symbol: target.reason for target in run_result.rebalance.targets},
                cost_config=config.cost_config,
                trades=trades,
            )

            value = _portfolio_value(cash, quantities, last_prices)
            peak_value = max(peak_value, value)
            equity_curve.append(
                DailyEquityPoint(
                    trade_date=trade_date,
                    value=value,
                    cash=cash,
                    drawdown=value / peak_value - 1 if peak_value > 0 else 0.0,
                    positions=_position_snapshots(quantities, last_prices, value),
                )
            )
            history.extend(bars_by_date[trade_date])

        final_positions = equity_curve[-1].positions if equity_curve else ()
        metrics = _calculate_metrics(
            initial_cash=config.initial_cash,
            equity_curve=equity_curve,
            trades=trades,
        )

        is_metrics, oos_metrics = _segment_metrics(
            initial_cash=config.initial_cash,
            equity_curve=equity_curve,
            trades=trades,
            in_sample_end_date=config.in_sample_end_date,
        )

        monthly_rets = _monthly_returns(equity_curve, config.initial_cash)

        return DailyBacktestResult(
            strategy_name=strategy.name,
            start_date=trade_dates[0],
            end_date=trade_dates[-1],
            initial_cash=config.initial_cash,
            final_value=equity_curve[-1].value,
            final_cash=cash,
            total_cost=sum(trade.total_cost for trade in trades),
            metrics=metrics,
            equity_curve=tuple(equity_curve),
            trades=tuple(trades),
            positions=final_positions,
            in_sample_end_date=config.in_sample_end_date,
            is_metrics=is_metrics,
            oos_metrics=oos_metrics,
            monthly_returns=monthly_rets,
        )

    async def run_and_persist(
        self,
        config: DailyBacktestConfig,
        *,
        strategy_version_id: str | None = None,
        priority: int = 3,
    ) -> DailyBacktestResult:
        """Execute a backtest and persist task, run, metrics and equity curve."""
        task = BacktestTask(
            strategy_version_id=strategy_version_id or config.strategy_name,
            config=_json_dumps(_config_payload(config)),
            status="running",
            priority=priority,
        )
        self.session.add(task)
        await self.session.flush()

        run = BacktestRun(
            task_id=task.id,
            params=_json_dumps(
                {
                    "strategy_params": dict(config.strategy_params),
                    "cost_config": asdict(config.cost_config),
                }
            ),
            started_at=now_utc().isoformat(),
            status="running",
        )
        self.session.add(run)
        await self.session.flush()

        try:
            result = await self.run(config)
        except Exception:
            task.status = "failed"
            run.status = "failed"
            run.ended_at = now_utc().isoformat()
            await self.session.commit()
            raise

        self.session.add(_metric_row(run.id, "all", result.metrics))
        if result.is_metrics is not None:
            self.session.add(_metric_row(run.id, "is", result.is_metrics))
        if result.oos_metrics is not None:
            self.session.add(_metric_row(run.id, "oos", result.oos_metrics))

        split_date = config.in_sample_end_date
        for point in result.equity_curve:
            phase = "is"
            if split_date is not None and point.trade_date > split_date:
                phase = "oos"
            self.session.add(
                EquityPoint(
                    run_id=run.id,
                    trade_date=point.trade_date,
                    value=point.value,
                    drawdown=point.drawdown,
                    phase=phase,
                )
            )

        for trade in result.trades:
            self.session.add(
                BacktestTrade(
                    run_id=run.id,
                    trade_date=trade.trade_date,
                    symbol=trade.symbol,
                    side=trade.side,
                    quantity=trade.quantity,
                    price=trade.price,
                    amount=trade.amount,
                    target_weight=trade.target_weight,
                    commission=trade.commission,
                    stamp_tax=trade.stamp_tax,
                    slippage=trade.slippage,
                    total_cost=trade.total_cost,
                    net_cash_flow=trade.net_cash_flow,
                    reason=trade.reason or None,
                )
            )

        task.status = "completed"
        run.status = "completed"
        run.ended_at = now_utc().isoformat()
        await self.session.commit()

        return replace(result, task_id=task.id, run_id=run.id)

    async def run_walk_forward(
        self,
        config: DailyBacktestConfig,
        *,
        folds: int = 4,
        train_ratio: float = 0.7,
        strategy_version_id: str | None = None,
    ) -> tuple[DailyBacktestResult, list["WalkForwardFoldSummary"]]:
        """Run a single full-range backtest then slice it into ``folds`` train/test windows.

        For now we re-use the same parameters across folds (no per-fold optimisation),
        so this is best understood as a fold-based OOS report. Each fold:
            - train window = first ``train_ratio`` of the fold's slice
            - test window  = remaining
        and metrics are computed on the existing equity curve.
        """
        if folds < 2:
            raise ValueError("walk-forward requires at least 2 folds")
        if not 0.1 <= train_ratio < 1.0:
            raise ValueError("train_ratio must be in [0.1, 1.0)")

        result = await self.run_and_persist(config, strategy_version_id=strategy_version_id)
        assert result.run_id is not None

        points = list(result.equity_curve)
        if len(points) < folds * 2:
            raise BacktestDataError(
                f"need at least {folds * 2} bars for {folds}-fold walk-forward, got {len(points)}"
            )

        fold_size = len(points) // folds
        summaries: list[WalkForwardFoldSummary] = []
        for i in range(folds):
            window_start = i * fold_size
            window_end = (i + 1) * fold_size if i < folds - 1 else len(points)
            window = points[window_start:window_end]
            split = max(1, min(len(window) - 1, int(len(window) * train_ratio)))
            train = window[:split]
            test = window[split:]
            train_baseline = points[window_start - 1].value if window_start > 0 else config.initial_cash
            train_metrics = _calculate_metrics(
                initial_cash=train_baseline,
                equity_curve=_rebase_drawdowns(train, baseline=train_baseline),
                trades=[t for t in result.trades if train[0].trade_date <= t.trade_date <= train[-1].trade_date],
            )
            test_baseline = train[-1].value
            test_metrics = _calculate_metrics(
                initial_cash=test_baseline,
                equity_curve=_rebase_drawdowns(test, baseline=test_baseline),
                trades=[t for t in result.trades if test[0].trade_date <= t.trade_date <= test[-1].trade_date],
            )
            summary = WalkForwardFoldSummary(
                fold_index=i,
                train_start=train[0].trade_date,
                train_end=train[-1].trade_date,
                test_start=test[0].trade_date,
                test_end=test[-1].trade_date,
                train_metrics=train_metrics,
                test_metrics=test_metrics,
            )
            summaries.append(summary)
            self.session.add(
                WalkForwardFold(
                    run_id=result.run_id,
                    fold_index=i,
                    train_start=summary.train_start,
                    train_end=summary.train_end,
                    test_start=summary.test_start,
                    test_end=summary.test_end,
                    train_return=train_metrics.cumulative_return,
                    test_return=test_metrics.cumulative_return,
                    train_sharpe=train_metrics.sharpe_ratio,
                    test_sharpe=test_metrics.sharpe_ratio,
                    train_max_dd=train_metrics.max_drawdown,
                    test_max_dd=test_metrics.max_drawdown,
                    train_params_json=json.dumps(dict(config.strategy_params), ensure_ascii=False),
                )
            )
        await self.session.commit()
        return result, summaries

    async def _load_bars(self, config: DailyBacktestConfig) -> list[MarketBarDaily]:
        result = await self.session.execute(
            select(MarketBarDaily)
            .where(
                MarketBarDaily.symbol.in_(config.universe),
                MarketBarDaily.trade_date >= config.start_date,
                MarketBarDaily.trade_date <= config.end_date,
            )
            .order_by(MarketBarDaily.trade_date, MarketBarDaily.symbol)
        )
        return list(result.scalars().all())


def _config_payload(config: DailyBacktestConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "universe": list(config.universe),
        "start_date": config.start_date,
        "end_date": config.end_date,
        "strategy_name": config.strategy_name,
        "initial_cash": config.initial_cash,
        "strategy_params": dict(config.strategy_params),
        "cost_config": asdict(config.cost_config),
    }
    if config.in_sample_end_date is not None:
        payload["in_sample_end_date"] = config.in_sample_end_date
    return payload


def _metric_row(run_id: str, segment: str, metrics: BacktestMetrics) -> BacktestMetric:
    return BacktestMetric(
        run_id=run_id,
        segment=segment,
        cumulative_return=metrics.cumulative_return,
        annual_return=metrics.annual_return,
        max_drawdown=metrics.max_drawdown,
        sharpe_ratio=metrics.sharpe_ratio,
        win_rate=metrics.win_rate,
        turnover=metrics.turnover,
    )


def _segment_metrics(
    *,
    initial_cash: float,
    equity_curve: Sequence[DailyEquityPoint],
    trades: Sequence[ExecutedTrade],
    in_sample_end_date: str | None,
) -> tuple[BacktestMetrics | None, BacktestMetrics | None]:
    """Compute IS / OOS metrics when a split date is provided.

    For OOS, peg the baseline to the equity value at the split boundary so the
    OOS cumulative return is measured from the OOS start (not the IS start).
    """
    if in_sample_end_date is None or not equity_curve:
        return (None, None)

    is_points = [p for p in equity_curve if p.trade_date <= in_sample_end_date]
    oos_points = [p for p in equity_curve if p.trade_date > in_sample_end_date]
    if not is_points or not oos_points:
        return (None, None)

    is_trades = [t for t in trades if t.trade_date <= in_sample_end_date]
    oos_trades = [t for t in trades if t.trade_date > in_sample_end_date]

    # IS segment uses the original initial_cash baseline.
    is_metrics = _calculate_metrics(
        initial_cash=initial_cash,
        equity_curve=_rebase_drawdowns(is_points),
        trades=is_trades,
    )

    # OOS baseline = last IS equity value, so cumulative / drawdown start fresh.
    oos_baseline = is_points[-1].value
    if oos_baseline <= 0:
        return (is_metrics, None)
    oos_metrics = _calculate_metrics(
        initial_cash=oos_baseline,
        equity_curve=_rebase_drawdowns(oos_points, baseline=oos_baseline),
        trades=oos_trades,
    )
    return (is_metrics, oos_metrics)


def _rebase_drawdowns(
    points: Sequence[DailyEquityPoint], *, baseline: float | None = None
) -> list[DailyEquityPoint]:
    """Recompute drawdown relative to the running peak of the supplied window."""
    rebased: list[DailyEquityPoint] = []
    peak = baseline if baseline is not None else (points[0].value if points else 0.0)
    for point in points:
        peak = max(peak, point.value)
        dd = point.value / peak - 1 if peak > 0 else 0.0
        rebased.append(
            DailyEquityPoint(
                trade_date=point.trade_date,
                value=point.value,
                cash=point.cash,
                drawdown=dd,
                positions=point.positions,
            )
        )
    return rebased


def _json_dumps(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _group_bars_by_date(bars: Sequence[MarketBarDaily]) -> dict[str, list[MarketBarDaily]]:
    grouped: dict[str, list[MarketBarDaily]] = defaultdict(list)
    for bar in bars:
        grouped[bar.trade_date].append(bar)
    return dict(grouped)


def _execute_rebalance(
    *,
    trade_date: str,
    cash: float,
    quantities: dict[str, float],
    today_bars: Mapping[str, MarketBarDaily],
    last_prices: Mapping[str, float],
    target_weights: Mapping[str, float],
    target_reasons: Mapping[str, str],
    cost_config: BacktestCostConfig,
    trades: list[ExecutedTrade],
) -> float:
    portfolio_value = _portfolio_value(cash, quantities, last_prices)
    tradable_symbols = sorted(set(quantities) | set(target_weights))

    for symbol in tradable_symbols:
        bar = today_bars.get(symbol)
        if bar is None or not bar.can_sell:
            continue
        current_quantity = quantities.get(symbol, 0.0)
        target_quantity = _target_quantity(symbol, target_weights, portfolio_value, last_prices)
        sell_quantity = max(0.0, current_quantity - target_quantity)
        if sell_quantity <= 0:
            continue
        mark_price = _valuation_price(bar)
        price = _execution_price(mark_price, "sell", cost_config)
        amount = sell_quantity * price
        commission = _commission(amount, cost_config)
        stamp_tax = amount * cost_config.stamp_tax_rate
        net_cash_flow = amount - commission - stamp_tax
        if net_cash_flow <= 0:
            continue
        slippage = sell_quantity * (mark_price - price)
        cash += net_cash_flow
        quantities[symbol] = current_quantity - sell_quantity
        trades.append(
            ExecutedTrade(
                trade_date=trade_date,
                symbol=symbol,
                side="sell",
                quantity=sell_quantity,
                price=price,
                amount=amount,
                target_weight=target_weights.get(symbol, 0.0),
                commission=commission,
                stamp_tax=stamp_tax,
                slippage=slippage,
                total_cost=commission + stamp_tax + slippage,
                net_cash_flow=net_cash_flow,
                reason=target_reasons.get(symbol, ""),
            )
        )

    portfolio_value = _portfolio_value(cash, quantities, last_prices)
    for symbol in tradable_symbols:
        bar = today_bars.get(symbol)
        if bar is None or not bar.can_buy:
            continue
        current_quantity = quantities.get(symbol, 0.0)
        target_quantity = _target_quantity(symbol, target_weights, portfolio_value, last_prices)
        buy_quantity = max(0.0, target_quantity - current_quantity)
        mark_price = _valuation_price(bar)
        price = _execution_price(mark_price, "buy", cost_config)
        affordable_quantity = _max_affordable_buy_quantity(cash, price, cost_config)
        buy_quantity = min(buy_quantity, affordable_quantity)
        if buy_quantity <= 0:
            continue
        amount = buy_quantity * price
        commission = _commission(amount, cost_config)
        net_cash_flow = -(amount + commission)
        slippage = buy_quantity * (price - mark_price)
        cash += net_cash_flow
        quantities[symbol] = current_quantity + buy_quantity
        trades.append(
            ExecutedTrade(
                trade_date=trade_date,
                symbol=symbol,
                side="buy",
                quantity=buy_quantity,
                price=price,
                amount=amount,
                target_weight=target_weights.get(symbol, 0.0),
                commission=commission,
                slippage=slippage,
                total_cost=commission + slippage,
                net_cash_flow=net_cash_flow,
                reason=target_reasons.get(symbol, ""),
            )
        )

    _drop_empty_positions(quantities)
    return max(0.0, cash)


def _target_quantity(
    symbol: str,
    target_weights: Mapping[str, float],
    portfolio_value: float,
    last_prices: Mapping[str, float],
) -> float:
    price = last_prices.get(symbol)
    if price is None or price <= 0:
        return 0.0
    return portfolio_value * target_weights.get(symbol, 0.0) / price


def _execution_price(mark_price: float, side: str, cost_config: BacktestCostConfig) -> float:
    if side == "buy":
        return mark_price * (1 + cost_config.slippage_rate)
    return mark_price * (1 - cost_config.slippage_rate)


def _commission(amount: float, cost_config: BacktestCostConfig) -> float:
    if amount <= 0:
        return 0.0
    return max(amount * cost_config.commission_rate, cost_config.min_commission)


def _max_affordable_buy_quantity(cash: float, price: float, cost_config: BacktestCostConfig) -> float:
    if cash <= 0 or price <= 0:
        return 0.0

    if cost_config.commission_rate > 0:
        percentage_fee_quantity = cash / (price * (1 + cost_config.commission_rate))
        percentage_fee_amount = percentage_fee_quantity * price
        if percentage_fee_amount * cost_config.commission_rate >= cost_config.min_commission:
            return percentage_fee_quantity

    if cost_config.min_commission > 0:
        return max(0.0, (cash - cost_config.min_commission) / price)
    return cash / price


def _calculate_metrics(
    *,
    initial_cash: float,
    equity_curve: Sequence[DailyEquityPoint],
    trades: Sequence[ExecutedTrade],
) -> BacktestMetrics:
    if not equity_curve:
        return BacktestMetrics(
            cumulative_return=0.0,
            annual_return=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            win_rate=0.0,
            turnover=0.0,
        )

    final_value = equity_curve[-1].value
    cumulative_return = final_value / initial_cash - 1
    periods = len(equity_curve)
    annual_return = _annualized_return(initial_cash, final_value, periods)
    daily_returns = _daily_returns(initial_cash, equity_curve)
    non_zero_returns = [r for r in daily_returns if abs(r) > 1e-12]
    positive_returns = [r for r in non_zero_returns if r > 0]
    average_equity = sum(point.value for point in equity_curve) / len(equity_curve)
    max_drawdown = min(point.drawdown for point in equity_curve)

    return BacktestMetrics(
        cumulative_return=cumulative_return,
        annual_return=annual_return,
        max_drawdown=max_drawdown,
        sharpe_ratio=_annualized_sharpe(daily_returns),
        win_rate=len(positive_returns) / len(non_zero_returns) if non_zero_returns else 0.0,
        turnover=sum(trade.amount for trade in trades) / average_equity if average_equity > 0 else 0.0,
        calmar_ratio=_calmar_ratio(annual_return, max_drawdown),
        sortino_ratio=_sortino_ratio(daily_returns),
        volatility=_annualized_volatility(daily_returns),
        profit_factor=_profit_factor(daily_returns),
    )


def _annualized_return(initial_cash: float, final_value: float, periods: int) -> float:
    if periods <= 0 or initial_cash <= 0:
        return 0.0
    total_return_ratio = final_value / initial_cash
    if total_return_ratio <= 0:
        return -1.0
    return total_return_ratio ** (252 / periods) - 1


def _daily_returns(initial_cash: float, equity_curve: Sequence[DailyEquityPoint]) -> list[float]:
    values = [initial_cash] + [point.value for point in equity_curve]
    return [
        values[index] / values[index - 1] - 1
        for index in range(1, len(values))
        if values[index - 1] > 0
    ]


def _annualized_sharpe(daily_returns: Sequence[float]) -> float:
    if len(daily_returns) < 2:
        return 0.0
    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((daily_return - mean_return) ** 2 for daily_return in daily_returns) / (len(daily_returns) - 1)
    std_return = math.sqrt(variance)
    if std_return <= 0:
        return 0.0
    return mean_return / std_return * math.sqrt(252)


def _calmar_ratio(annual_return: float, max_drawdown: float) -> float:
    if max_drawdown >= 0:
        return 0.0
    return min(annual_return / abs(max_drawdown), 20.0)


def _sortino_ratio(daily_returns: Sequence[float]) -> float:
    if len(daily_returns) < 2:
        return 0.0
    mean_return = sum(daily_returns) / len(daily_returns)
    negative_returns = [r for r in daily_returns if r < 0]
    if not negative_returns:
        return 10.0
    downside_variance = sum(r ** 2 for r in negative_returns) / len(daily_returns)
    downside_std = math.sqrt(downside_variance)
    if downside_std <= 0:
        return 0.0
    return min(mean_return / downside_std * math.sqrt(252), 20.0)


def _annualized_volatility(daily_returns: Sequence[float]) -> float:
    if len(daily_returns) < 2:
        return 0.0
    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    return math.sqrt(variance) * math.sqrt(252)


def _profit_factor(daily_returns: Sequence[float]) -> float:
    gains = sum(r for r in daily_returns if r > 0)
    losses = abs(sum(r for r in daily_returns if r < 0))
    if losses <= 0:
        return 10.0
    return min(gains / losses, 20.0)


def _monthly_returns(
    equity_curve: Sequence[DailyEquityPoint],
    initial_cash: float,
) -> dict[str, float]:
    if not equity_curve:
        return {}
    from collections import defaultdict as _defaultdict
    by_month: dict[str, list[DailyEquityPoint]] = _defaultdict(list)
    for point in equity_curve:
        by_month[point.trade_date[:7]].append(point)
    result: dict[str, float] = {}
    prev_value = initial_cash
    for month_key in sorted(by_month):
        end_value = by_month[month_key][-1].value
        result[month_key] = round(end_value / prev_value - 1, 6) if prev_value > 0 else 0.0
        prev_value = end_value
    return result


def _portfolio_value(cash: float, quantities: Mapping[str, float], last_prices: Mapping[str, float]) -> float:
    return cash + sum(quantity * last_prices.get(symbol, 0.0) for symbol, quantity in quantities.items())


def _strategy_positions(
    quantities: Mapping[str, float],
    last_prices: Mapping[str, float],
    portfolio_value: float,
) -> dict[str, Position]:
    positions: dict[str, Position] = {}
    for snapshot in _position_snapshots(quantities, last_prices, portfolio_value):
        positions[snapshot.symbol] = Position(
            symbol=snapshot.symbol,
            quantity=snapshot.quantity,
            market_value=snapshot.market_value,
            weight=snapshot.weight,
            available_quantity=snapshot.quantity,
        )
    return positions


def _position_snapshots(
    quantities: Mapping[str, float],
    last_prices: Mapping[str, float],
    portfolio_value: float,
) -> tuple[PositionSnapshot, ...]:
    snapshots: list[PositionSnapshot] = []
    for symbol, quantity in sorted(quantities.items()):
        if quantity <= 0:
            continue
        price = last_prices.get(symbol)
        if price is None:
            continue
        market_value = quantity * price
        snapshots.append(
            PositionSnapshot(
                symbol=symbol,
                quantity=quantity,
                price=price,
                market_value=market_value,
                weight=market_value / portfolio_value if portfolio_value > 0 else 0.0,
            )
        )
    return tuple(snapshots)


def _drop_empty_positions(quantities: dict[str, float]) -> None:
    for symbol in list(quantities):
        if quantities[symbol] <= 1e-9:
            del quantities[symbol]


def _to_strategy_bar(row: MarketBarDaily) -> StrategyBar:
    return StrategyBar(
        symbol=row.symbol,
        trade_date=row.trade_date,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        amount=row.amount,
        adjusted_close=row.adjusted_close,
        can_buy=row.can_buy,
        can_sell=row.can_sell,
        is_suspended=row.is_suspended,
        is_limit_up=row.is_limit_up,
        is_limit_down=row.is_limit_down,
    )


def _valuation_price(row: MarketBarDaily) -> float:
    return row.adjusted_close or row.close
