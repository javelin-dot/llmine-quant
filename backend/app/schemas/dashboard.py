"""Dashboard schemas aligned with frontend MockData."""

from pydantic import BaseModel, Field


# ── Market Bar ──
class MarketIndex(BaseModel):
    name: str
    symbol: str
    price: float
    change: float
    volume: str


# ── Portfolio Chart ──
class PortfolioMetrics(BaseModel):
    totalReturn: float
    annualReturn: float
    maxDrawdown: float
    sharpeRatio: float
    sortinoRatio: float
    benchmark: str
    benchmarkReturn: float


class EquityPoint(BaseModel):
    date: str
    value: float
    benchmark: float


# ── Agent Matrix ──
class Agent(BaseModel):
    avatar: str
    name: str
    detail: str
    metric: str
    status: str  # active | waiting | attention | idle


# ── Alert Queue ──
class Alert(BaseModel):
    id: str
    type: str  # approval | risk | system
    title: str
    time: str
    severity: str  # high | medium | low
    target: str | None = None


# ── Strategy Grid ──
class DashboardStrategy(BaseModel):
    id: str
    name: str
    type: str
    return_pct: float = Field(serialization_alias="return")
    status: str  # live | paper | backtest | draft
    sparkline: list[float]
    lastSignalTime: str


# ── System ──
class SystemHealth(BaseModel):
    healthScore: int
    healthStatusLabel: str
    healthBarHeights: list[int]
    autopilot: bool
    riskGateLabel: str


class Meta(BaseModel):
    product: str
    subtitle: str


class ModalData(BaseModel):
    title: str
    body: str
    primary: str


# ── Dashboard Overview Response ──
class DashboardOverview(BaseModel):
    meta: Meta
    system: SystemHealth
    modals: dict[str, ModalData]
    marketIndices: list[MarketIndex]
    portfolioMetrics: PortfolioMetrics
    equityCurve: list[EquityPoint]
    agents: list[Agent]
    alerts: list[Alert]
    strategies: list[DashboardStrategy]
    pendingApprovals: int
