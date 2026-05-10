"""Execution domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel


class ExecutionSummary(BaseModel):
    pending: int
    urgent: int
    blocked: int
    approved24h: int
    avgLatencySec: float
    successRate: float


class ApprovalOut(BaseModel):
    id: str
    type: str
    typeTone: str
    symbol: str
    name: str
    side: str
    qty: str
    notional: str
    notionalPct: float
    limitPrice: str
    stopLoss: str
    confidence: float
    riskGrade: str
    reason: str
    impact: str
    expireSec: int
    urgency: str
    urgencyTone: str
    strategy: str


class PreTradeCheckOut(BaseModel):
    name: str
    current: float
    limit: float
    status: str
    statusTone: str
    note: str


class OrderBookRow(BaseModel):
    time: str
    symbol: str
    side: str
    qty: str
    limit: str
    filled: str
    status: str
    statusTone: str
    slippageBps: float
    pnl: float | None


class SlippageBucket(BaseModel):
    range: str
    count: int


class SlippageMetric(BaseModel):
    avgBps: float
    p50Bps: float
    p95Bps: float
    buckets: list[SlippageBucket]


class FillRateMetric(BaseModel):
    total: int
    filled: int
    partial: int
    rejected: int
    canceled: int


class RejectReason(BaseModel):
    reason: str
    count: int
    tone: str


class ExecutionMetrics(BaseModel):
    slippage: SlippageMetric
    fillRate: FillRateMetric
    rejectReasons: list[RejectReason]


class AgentTraceOut(BaseModel):
    time: str
    agent: str
    action: str
    detail: str
    tone: str
    icon: str


class ExecutionScreen(BaseModel):
    summary: ExecutionSummary
    approvals: list[ApprovalOut]
    preTradeChecks: list[PreTradeCheckOut]
    orderBook: list[OrderBookRow]
    metrics: ExecutionMetrics
    agentTrace: list[AgentTraceOut]
