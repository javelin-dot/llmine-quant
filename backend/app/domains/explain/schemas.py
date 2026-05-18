"""Explain domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel


class SignalHeader(BaseModel):
    strategy: str
    action: str
    target: str
    size: str
    confidence: float
    riskGrade: str
    traceId: str
    timestamp: str
    status: str
    statusTone: str


class AttributionItemOut(BaseModel):
    name: str
    value: float
    desc: str


class AttributionOut(BaseModel):
    base: float
    items: list[AttributionItemOut]
    final: float
    decision: str
    decisionTone: str


class RadarAxis(BaseModel):
    name: str
    score: float
    desc: str


class ConfidenceRadar(BaseModel):
    axes: list[RadarAxis]
    avg: float


class DecisionChainStep(BaseModel):
    step: int
    title: str
    desc: str
    detail: str
    tag: str
    tone: str


class LineageStep(BaseModel):
    step: str
    version: str
    hash: str
    permission: str
    permissionTone: str
    detail: str


class BiasGateOut(BaseModel):
    check: str
    status: str
    desc: str


class SimilarCaseOut(BaseModel):
    id: str
    date: str
    action: str
    ret: float
    days: int
    success: bool
    note: str


class SimilarHistory(BaseModel):
    summary: str
    winRate: float
    avgReturn: float
    cases: list[SimilarCaseOut]


class ExplainScreen(BaseModel):
    signalHeader: SignalHeader
    attribution: AttributionOut
    confidenceRadar: ConfidenceRadar
    decisionChain: list[DecisionChainStep]
    lineage: list[LineageStep]
    biasGate: list[BiasGateOut]
    similarHistory: SimilarHistory


class ExplainApproveIn(BaseModel):
    traceId: str


class ExplainApproveOut(BaseModel):
    traceId: str
    status: str  # approved | ignored if already approved
