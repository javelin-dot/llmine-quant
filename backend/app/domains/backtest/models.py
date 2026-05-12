"""Backtest domain models — tasks, runs, metrics, reports."""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class BacktestTask(BaseModel):
    """Backtest task configuration."""

    __tablename__ = "backtest_tasks"

    strategy_version_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    config: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)  # queued / running / completed / failed / canceled
    priority: Mapped[int] = mapped_column(Integer, default=3)


class BacktestRun(BaseModel):
    """Single backtest run (one parameter set)."""

    __tablename__ = "backtest_runs"

    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    params: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    started_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ended_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    report_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)


class BacktestMetric(BaseModel):
    """Performance metrics for a backtest run.

    ``segment`` distinguishes the time range a row covers:
        - ``all``: full backtest period (always written)
        - ``is`` : in-sample portion when an IS/OOS split is configured
        - ``oos``: out-of-sample portion when an IS/OOS split is configured
    """

    __tablename__ = "backtest_metrics"

    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    segment: Mapped[str] = mapped_column(String(16), default="all", index=True)
    cumulative_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    sortino_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_loss_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    oos_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overfit_level: Mapped[str | None] = mapped_column(String(16), nullable=True)  # low / medium / high


class EquityPoint(BaseModel):
    """Equity curve data point."""

    __tablename__ = "equity_points"

    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trade_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    benchmark: Mapped[float | None] = mapped_column(Float, nullable=True)
    drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    phase: Mapped[str] = mapped_column(String(16), default="is")  # is / oos


class SensitivityRun(BaseModel):
    """Single parameter / slippage perturbation outcome.

    Each row represents one re-run of the backtest with a perturbed setting
    relative to the baseline run. ``kind`` distinguishes ``param`` (strategy
    parameter sweep) from ``slippage`` (transaction cost sweep). The result of
    the baseline itself is stored once with ``is_baseline=True``.
    """

    __tablename__ = "sensitivity_runs"

    parent_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # param / slippage
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    variant_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_baseline: Mapped[bool] = mapped_column(default=False)
    cumulative_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)


class WalkForwardFold(BaseModel):
    """Single fold of a walk-forward analysis tied to a parent BacktestRun.

    For rule-based strategies we treat folds as post-hoc OOS slices of the same
    full-range backtest: each fold records the metrics for its train and test
    windows. When parameter tuning is added later, ``train_params_json`` will
    hold the per-fold chosen parameters.
    """

    __tablename__ = "walk_forward_folds"

    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    fold_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    train_start: Mapped[str] = mapped_column(String(32), nullable=False)
    train_end: Mapped[str] = mapped_column(String(32), nullable=False)
    test_start: Mapped[str] = mapped_column(String(32), nullable=False)
    test_end: Mapped[str] = mapped_column(String(32), nullable=False)
    train_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    test_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    train_sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    test_sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    train_max_dd: Mapped[float | None] = mapped_column(Float, nullable=True)
    test_max_dd: Mapped[float | None] = mapped_column(Float, nullable=True)
    train_params_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class BacktestTrade(BaseModel):
    """Persisted simulated trade with the rule explanation that drove it."""

    __tablename__ = "backtest_trades"

    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    trade_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # buy / sell
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    target_weight: Mapped[float] = mapped_column(Float, default=0.0)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    stamp_tax: Mapped[float] = mapped_column(Float, default=0.0)
    slippage: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    net_cash_flow: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class StressResult(BaseModel):
    """Stress test scenario result."""

    __tablename__ = "stress_results"

    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scenario: Mapped[str] = mapped_column(String(64), nullable=False)
    loss: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_drawdown: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fuse: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fuse_tone: Mapped[str] = mapped_column(String(16), default="green")
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    human: Mapped[str | None] = mapped_column(Text, nullable=True)
