"""Strategy domain models — strategies, versions, tasks, pipeline events, templates."""

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class Strategy(BaseModel):
    """Strategy master record."""

    __tablename__ = "strategies"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # rule / ml / portfolio
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)  # draft / backtesting / paper / live / paused / archived
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_profile: Mapped[str] = mapped_column(String(32), default="balanced")  # conservative / balanced / aggressive
    market: Mapped[str] = mapped_column(String(32), default="A")  # A / US / HK / crypto
    universe: Mapped[str | None] = mapped_column(String(512), nullable=True)
    frequency: Mapped[str] = mapped_column(String(16), default="1d")
    sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_dd: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    oos_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class StrategyVersion(BaseModel):
    """Immutable strategy version."""

    __tablename__ = "strategy_versions"

    strategy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    code_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    code_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    params_schema: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    risk_rules: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(String(32), default="draft")


class StrategyTask(BaseModel):
    """Natural language strategy generation task."""

    __tablename__ = "strategy_tasks"

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    market: Mapped[str] = mapped_column(String(32), default="A")
    risk_profile: Mapped[str] = mapped_column(String(32), default="balanced")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)  # queued / running / waiting_human / blocked / succeeded / failed / canceled
    agent_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    strategy_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    backtest_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    backtest_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class PipelineEvent(BaseModel):
    """Strategy pipeline state change event."""

    __tablename__ = "strategy_pipeline_events"

    strategy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # research / backtest / paper / live / archived
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    progress: Mapped[int] = mapped_column(default=0)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class StrategyTemplate(BaseModel):
    """Pre-built strategy template."""

    __tablename__ = "strategy_templates"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="balanced")
    market: Mapped[str] = mapped_column(String(32), default="A")
    family: Mapped[str] = mapped_column(String(64), nullable=False)
    template_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
