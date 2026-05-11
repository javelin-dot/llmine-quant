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
