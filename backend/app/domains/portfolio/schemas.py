"""Portfolio domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel, Field


class NAV(BaseModel):
    total: float
    currency: str
    todayPnl: float
    todayPct: float
    mtdPct: float
    ytdPct: float
    cashPct: float
    leverage: float
    netExposure: float
    varDaily: float
    varPct: float


class RiskBudget(BaseModel):
    label: str
    pct: float
    limit: float
    tone: str
    desc: str


class AllocationStrategy(BaseModel):
    name: str
    family: str
    weight: float
    pnl: float
    pnlPct: float
    risk: str
    status: str
    statusTone: str
    contribution: float
    sparkline: list[float]


class Allocation(BaseModel):
    strategies: list[AllocationStrategy]


class Correlation(BaseModel):
    labels: list[str]
    matrix: list[list[float]]


class ConcentrationSector(BaseModel):
    name: str
    weight: float
    change: float


class ConcentrationHolding(BaseModel):
    symbol: str
    name: str
    weight: float
    change: float


class ConcentrationFactor(BaseModel):
    name: str
    exposure: float
    tone: str


class Concentration(BaseModel):
    sectors: list[ConcentrationSector]
    holdings: list[ConcentrationHolding]
    factors: list[ConcentrationFactor]


class RebalanceAction(BaseModel):
    id: str
    type: str
    from_: str = Field(serialization_alias="from")
    to: str
    delta: str
    reason: str
    impact: str
    urgency: str
    urgencyTone: str


class PortfolioScreen(BaseModel):
    nav: NAV
    riskBudget: list[RiskBudget]
    allocation: Allocation
    correlation: Correlation
    concentration: Concentration
    rebalance: list[RebalanceAction]
