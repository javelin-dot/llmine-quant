"""Agent domain models — agent registry, tasks, messages, tool registry."""

from sqlalchemy import Boolean, Float, Integer, String, Text
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


class AgentDefinition(BaseModel):
    """Reusable, fully configurable agent definition."""

    __tablename__ = "agent_definitions"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    avatar: Mapped[str] = mapped_column(String(16), default="A")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    downstream_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    autonomy: Mapped[str] = mapped_column(String(32), default="supervised")
    status: Mapped[str] = mapped_column(String(16), default="active")
    model_config_json: Mapped[str] = mapped_column(Text, default="{}")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    user_prompt_template: Mapped[str] = mapped_column(Text, default="")
    input_schema_json: Mapped[str] = mapped_column(Text, default="{}")
    output_schema_json: Mapped[str] = mapped_column(Text, default="{}")
    normalized_input_schema_json: Mapped[str] = mapped_column(Text, default="{}")
    normalized_output_schema_json: Mapped[str] = mapped_column(Text, default="{}")
    input_mapping_json: Mapped[str] = mapped_column(Text, default="[]")
    output_mapping_json: Mapped[str] = mapped_column(Text, default="[]")
    tool_policy_json: Mapped[str] = mapped_column(Text, default="[]")
    constraints_json: Mapped[str] = mapped_column(Text, default="[]")
    runtime_policy_json: Mapped[str] = mapped_column(Text, default="{}")


class WorkflowDefinition(BaseModel):
    """Saved workflow that composes multiple agent definitions."""

    __tablename__ = "workflow_definitions"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    published_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class WorkflowVersion(BaseModel):
    """Immutable published snapshot of a workflow graph and its agent definitions."""

    __tablename__ = "workflow_versions"

    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="published")
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)


class WorkflowNode(BaseModel):
    """Agent instance placed on a workflow canvas."""

    __tablename__ = "workflow_nodes"

    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_definition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)
    config_override_json: Mapped[str] = mapped_column(Text, default="{}")


class WorkflowEdge(BaseModel):
    """Directed connection between two workflow nodes."""

    __tablename__ = "workflow_edges"

    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mapping_json: Mapped[str] = mapped_column(Text, default="[]")
    condition_json: Mapped[str] = mapped_column(Text, default="{}")
