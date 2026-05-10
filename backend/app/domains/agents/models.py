"""Agent domain models — agent registry, tasks, messages, tool registry."""

from sqlalchemy import Float, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class AgentRegistry(BaseModel):
    """Registered AI agent."""

    __tablename__ = "agent_registry"

    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # research / strategy / backtest / risk / execution / portfolio / explain / data
    status: Mapped[str] = mapped_column(String(16), default="idle")  # active / idle / error / paused
    current_task: Mapped[str | None] = mapped_column(String(256), nullable=True)
    metric: Mapped[str | None] = mapped_column(String(64), nullable=True)
    heartbeat_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentTask(BaseModel):
    """Agent task queue item."""

    __tablename__ = "agent_tasks"

    agent_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending / running / completed / failed
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AgentMessage(BaseModel):
    """Inter-agent message."""

    __tablename__ = "agent_messages"

    from_agent: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    to_agent: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    msg_type: Mapped[str] = mapped_column(String(32), nullable=False)  # request / response / event / broadcast
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class ToolRegistry(BaseModel):
    """Agent tool registry entry."""

    __tablename__ = "tool_registry"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    level: Mapped[str] = mapped_column(String(16), default="low")  # low / medium / high
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_agents: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of agent roles
    schema_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
