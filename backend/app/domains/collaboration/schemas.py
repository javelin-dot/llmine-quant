"""Collaboration domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel, Field


class Kpi(BaseModel):
    label: str
    value: str
    trend: str
    tone: str


class Reviewer(BaseModel):
    role: str
    decision: str
    tone: str


class ActiveReview(BaseModel):
    id: str
    strategy: str
    fromVer: str
    toVer: str
    status: str
    statusTone: str
    reviewers: list[Reviewer]
    createdAt: str
    priority: str
    priorityTone: str


class DiffRow(BaseModel):
    field: str
    from_: str = Field(serialization_alias="from")
    to: str
    impact: str


class DiffPanel(BaseModel):
    header: str
    rows: list[DiffRow]


class ReviewThreadItem(BaseModel):
    role: str
    text: str
    tag: str
    tagClass: str | None


class ABTestOut(BaseModel):
    id: str
    name: str
    control: str
    variant: str
    status: str
    statusTone: str
    duration: str
    samples: int
    improvement: float
    sparkline: list[float]


class ApprovalFlowStage(BaseModel):
    stage: str
    tone: str
    required: bool
    completed: bool
    assignee: str
    note: str


class FooterCard(BaseModel):
    title: str
    desc: str
    tag: str
    tagClass: str | None


class CollaborationScreen(BaseModel):
    kpis: list[Kpi]
    activeReviews: list[ActiveReview]
    diff: DiffPanel
    reviewThread: list[ReviewThreadItem]
    abTests: list[ABTestOut]
    approvalFlow: list[ApprovalFlowStage]
    footerCards: list[FooterCard]
