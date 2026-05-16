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


class AgentDefinitionBase(BaseModel):
    name: str
    role: str
    avatar: str = "A"
    description: str = ""
    objective: str = ""
    downstreamHint: str = ""
    autonomy: str = "supervised"
    status: str = "active"
    modelConfig: dict
    systemPrompt: str
    userPromptTemplate: str
    inputSchema: dict
    outputSchema: dict
    normalizedInputSchema: dict
    normalizedOutputSchema: dict
    inputMapping: list[dict]
    outputMapping: list[dict]
    toolPolicy: list[dict]
    constraints: list[dict]
    runtimePolicy: dict


class AgentDefinitionCreate(AgentDefinitionBase):
    pass


class AgentDefinitionUpdate(AgentDefinitionBase):
    pass


class AgentDefinitionOut(AgentDefinitionBase):
    id: str


class WorkflowNodeIn(BaseModel):
    id: str | None = None
    agentDefinitionId: str
    label: str | None = None
    positionX: float
    positionY: float
    configOverride: dict = {}


class WorkflowEdgeIn(BaseModel):
    id: str | None = None
    sourceNodeId: str
    targetNodeId: str
    mapping: list[dict] = []
    condition: dict = {}


class WorkflowBase(BaseModel):
    name: str
    description: str = ""
    version: str = "1.0.0"
    status: str = "draft"
    isDefault: bool = False
    nodes: list[WorkflowNodeIn]
    edges: list[WorkflowEdgeIn]


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(WorkflowBase):
    pass


class WorkflowNodeOut(WorkflowNodeIn):
    id: str


class WorkflowEdgeOut(WorkflowEdgeIn):
    id: str


class WorkflowOut(WorkflowBase):
    id: str
    nodes: list[WorkflowNodeOut]
    edges: list[WorkflowEdgeOut]


class WorkflowRunCreate(BaseModel):
    traceId: str | None = None
    payload: dict


class WorkflowRunOut(BaseModel):
    workflowId: str
    traceId: str
    result: dict


class WorkflowVersionOut(BaseModel):
    id: str
    workflowId: str
    version: str
    status: str
    publishedAt: str
    snapshot: dict


class WorkflowPublishOut(BaseModel):
    workflow: WorkflowOut
    version: WorkflowVersionOut
