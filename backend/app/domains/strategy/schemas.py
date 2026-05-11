"""Strategy domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel, Field


class PipelineStatus(BaseModel):
    stage: str
    count: int
    tone: str  # blue / green / yellow / purple / red


class StrategyTemplate(BaseModel):
    id: str
    name: str
    risk: str  # conservative / balanced / aggressive
    market: str
    family: str
    desc: str


class FeedEvent(BaseModel):
    time: str
    agent: str
    event: str
    tone: str


class StrategyMatrixRow(BaseModel):
    id: str
    name: str
    family: str
    annualReturn: float
    maxDd: float
    sharpe: float
    status: str  # live / paper / backtest / draft
    oosScore: float
    sparkline: list[float]
    lastUpdate: str


class PipelineTicket(BaseModel):
    id: str
    title: str
    desc: str
    progress: int
    metrics: list[dict[str, str]]
    tag: str
    tagClass: str | None = None


class PipelineLane(BaseModel):
    lane: str
    tone: str
    tickets: list[PipelineTicket]


class StrategyScreen(BaseModel):
    pipelineStatus: list[PipelineStatus]
    templates: list[StrategyTemplate]
    nlPrompt: str
    feed: list[FeedEvent]
    matrix: list[StrategyMatrixRow]
    pipelineBoard: list[PipelineLane]


class StrategyCreate(BaseModel):
    name: str
    family: str = "trend"
    type: str = "rule"
    description: str | None = None
    risk_profile: str = "balanced"
    market: str = "A"
    universe: str | None = None
    frequency: str = "1d"


class StrategyTaskCreate(BaseModel):
    prompt: str
    market: str = "A"
    risk_profile: str = Field(default="balanced", alias="riskProfile")

    model_config = {"populate_by_name": True}


class StrategyTaskOut(BaseModel):
    """Generation task as exposed by the API."""

    id: str
    prompt: str
    market: str
    risk_profile: str = Field(alias="riskProfile")
    status: str
    statusTone: str
    progress: int = 0
    stage: str | None = None
    strategy_id: str | None = Field(default=None, alias="strategyId")
    agent_task_id: str | None = Field(default=None, alias="agentTaskId")
    result: str | None = None
    error: str | None = None
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class PipelineEventOut(BaseModel):
    """Single pipeline event for a strategy task."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    stage: str
    event: str
    progress: int
    detail: str | None = None
    created_at: str = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class StrategyTransition(BaseModel):
    """Request body for transitioning a strategy between pipeline stages."""

    target: str  # research / backtest / paper / live / archived
    note: str | None = None


class StrategyVersionOut(BaseModel):
    """A persisted strategy version (immutable code snapshot)."""

    id: str
    version: str
    status: str
    code_text: str | None = Field(default=None, alias="codeText")
    params_schema: str | None = Field(default=None, alias="paramsSchema")
    risk_rules: str | None = Field(default=None, alias="riskRules")
    created_at: str = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class StrategyDetail(BaseModel):
    """Full strategy detail — basic info + metrics + versions + recent events."""

    id: str
    name: str
    family: str
    type: str
    status: str
    description: str | None = None
    risk_profile: str = Field(alias="riskProfile")
    market: str
    universe: str | None = None
    frequency: str
    owner_id: str | None = Field(default=None, alias="ownerId")
    sharpe: float | None = None
    max_dd: float | None = Field(default=None, alias="maxDd")
    annual_return: float | None = Field(default=None, alias="annualReturn")
    oos_score: float | None = Field(default=None, alias="oosScore")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    versions: list[StrategyVersionOut] = []
    recent_events: list[PipelineEventOut] = Field(default_factory=list, alias="recentEvents")

    model_config = {"populate_by_name": True}


class StrategyUpdate(BaseModel):
    """Partial update payload for a strategy."""

    name: str | None = None
    family: str | None = None
    description: str | None = None
    risk_profile: str | None = Field(default=None, alias="riskProfile")
    market: str | None = None
    universe: str | None = None
    frequency: str | None = None
    status: str | None = None

    model_config = {"populate_by_name": True}


class StrategyListItem(BaseModel):
    """Compact row for listing strategies."""

    id: str
    name: str
    family: str
    type: str
    status: str
    risk_profile: str = Field(alias="riskProfile")
    market: str
    sharpe: float | None = None
    max_dd: float | None = Field(default=None, alias="maxDd")
    annual_return: float | None = Field(default=None, alias="annualReturn")
    oos_score: float | None = Field(default=None, alias="oosScore")
    updated_at: str = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class StrategyListResponse(BaseModel):
    """Paginated strategy listing."""

    total: int
    items: list[StrategyListItem]
