"""Agent domain Pydantic schemas."""

from pydantic import BaseModel


class AgentOut(BaseModel):
    id: str
    name: str
    role: str
    status: str
    statusTone: str
    currentTask: str
    metric: str
    heartbeat: str


class AgentTaskOut(BaseModel):
    id: str
    agentId: str
    agentName: str
    taskType: str
    priority: int
    status: str
    statusTone: str
    createdAt: str
    startedAt: str | None
    completedAt: str | None
    result: str | None


class AgentMessageOut(BaseModel):
    id: str
    fromAgent: str
    toAgent: str | None
    msgType: str
    topic: str
    payload: str
    correlationId: str | None
    createdAt: str


class ToolOut(BaseModel):
    id: str
    name: str
    level: str
    levelTone: str
    description: str
    allowedAgents: list[str]
    enabled: bool


class AgentOverview(BaseModel):
    agents: list[AgentOut]
    tasks: list[AgentTaskOut]
    messages: list[AgentMessageOut]
    tools: list[ToolOut]


class AgentTaskCreate(BaseModel):
    """Request body for creating a new agent task."""

    agent_role: str  # e.g. "strategy" / "research" / "backtest" / "risk"
    task_type: str
    payload: dict | None = None
    priority: int = 0
    correlation_id: str | None = None


class AgentMessageCreate(BaseModel):
    """Request body for sending a new inter-agent message."""

    from_agent: str  # agent role or id
    to_agent: str | None = None
    msg_type: str = "event"  # request / response / event / broadcast
    topic: str
    payload: dict
    correlation_id: str | None = None
