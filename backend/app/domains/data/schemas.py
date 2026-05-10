"""Data domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel


class DataSourceTier(BaseModel):
    tier: str  # research / paper / live
    label: str
    count: int
    active: int
    avgLatencyMs: int
    license: str
    tone: str
    desc: str


class DataSourceOut(BaseModel):
    id: str
    name: str
    provider: str
    tier: str
    tierTone: str
    type: str
    coverage: str
    latencyMs: int
    latencyP95: int
    missingPct: float
    driftScore: float
    license: str
    status: str
    statusTone: str
    lastUpdate: str


class LatencyTrend(BaseModel):
    times: list[str]
    research: list[float]
    paper: list[float]
    live: list[float]
    slaMs: int


class BiasGate(BaseModel):
    title: str
    desc: str
    status: str  # pass / watch / fail / enforced
    statusTone: str
    lastCheck: str
    note: str


class LineageNodeOut(BaseModel):
    id: str
    label: str
    tier: str
    tone: str
    version: str
    permission: str


class LineageOut(BaseModel):
    nodes: list[LineageNodeOut]
    edges: list[dict[str, str]]


class DataIncidentOut(BaseModel):
    time: str
    source: str
    type: str
    typeTone: str
    severity: str
    severityTone: str
    title: str
    detail: str
    resolution: str
    status: str
    statusTone: str


class DataOverview(BaseModel):
    totalSources: int
    activeSources: int
    erroredSources: int
    avgLatencyMs: int
    p95LatencyMs: int
    missingRate: float
    incidents24h: int
    healthScore: int
    healthStatus: str
    healthStatusTone: str


class DataScreen(BaseModel):
    header: DataOverview
    tiers: list[DataSourceTier]
    kpis: list[dict[str, str]]
    sources: list[DataSourceOut]
    latencyTrend: LatencyTrend
    biasGate: list[BiasGate]
    lineage: LineageOut
    incidents: list[DataIncidentOut]
