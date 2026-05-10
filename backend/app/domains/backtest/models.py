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
    """Performance metrics for a backtest run."""

    __tablename__ = "backtest_metrics"

    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
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
