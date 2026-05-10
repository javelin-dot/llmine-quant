"""Risk domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel


class RiskHeader(BaseModel):
    healthScore: int
    healthStatus: str
    healthStatusTone: str
    killSwitchArmed: bool
    lastIncident: str
    autoBlocks24h: int
    pendingApprovals: int
    activeBreaches: int


class RiskKpi(BaseModel):
    label: str
    value: str
    trend: str
    tone: str


class RiskBudgetRow(BaseModel):
    name: str
    used: float
    limit: float
    unit: str
    tone: str
    desc: str


class VaRHistory(BaseModel):
    date: str
    value: float


class VaRDecomposition(BaseModel):
    strategy: str
    contribution: float
    pct: float
    tone: str


class VaRPanel(BaseModel):
    daily: float
    dailyPct: float
    weekly: float
    weeklyPct: float
    confidence: float
    currency: str
    history: list[VaRHistory]
    decomposition: list[VaRDecomposition]


class CircuitBreaker(BaseModel):
    level: str  # L1 / L2 / L3 / L4
    name: str
    status: str  # armed / triggered / cooldown / disabled
    statusTone: str
    trigger: str
    action: str
    triggers24h: int
    lastTrigger: str


class PolicyDecisionOut(BaseModel):
    time: str
    agent: str
    request: str
    decision: str  # allowed / denied / approval_required / modified
    decisionTone: str
    reason: str
    durationMs: int


class RiskBreachOut(BaseModel):
    time: str
    severity: str
    severityTone: str
    title: str
    detail: str
    resolution: str
    status: str
    statusTone: str


class RiskScreen(BaseModel):
    header: RiskHeader
    kpis: list[RiskKpi]
    budgets: list[RiskBudgetRow]
    var: VaRPanel
    circuits: list[CircuitBreaker]
    policyStream: list[PolicyDecisionOut]
    breaches: list[RiskBreachOut]
