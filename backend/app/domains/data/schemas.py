"""Data domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel, ConfigDict, Field


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


class FeatureOut(BaseModel):
    id: str
    name: str
    version: str
    kind: str | None = None
    description: str | None = None
    computationWindow: int | None = None
    validated: bool = False
    permissionScope: str = "research"


class FeatureUsageOut(BaseModel):
    featureId: str
    featureName: str
    featureVersion: str
    strategyVersionId: str
    backtestRunId: str | None = None
    role: str | None = None


class RunLineageOut(BaseModel):
    runId: str
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


class MarketDataCsvImportIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    path: str
    default_symbol: str | None = Field(default=None, alias="defaultSymbol")
    source_name: str = Field(default="csv", alias="sourceName")


class MarketDataAkshareImportIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    symbols: list[str]
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    adjust: str = "qfq"


class MarketDataImportSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str
    total_rows: int = Field(alias="totalRows")
    imported_rows: int = Field(alias="importedRows")
    inserted_rows: int = Field(alias="insertedRows")
    updated_rows: int = Field(alias="updatedRows")
    skipped_rows: int = Field(alias="skippedRows")
    symbols: list[str]
    start_date: str | None = Field(alias="startDate")
    end_date: str | None = Field(alias="endDate")
    errors: list[str]


class MarketBarDailyOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    symbol: str
    trade_date: str = Field(alias="tradeDate")
    prev_close: float | None = Field(alias="prevClose")
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float | None
    adjusted_close: float | None = Field(alias="adjustedClose")
    forward_factor: float | None = Field(alias="forwardFactor")
    limit_up_price: float | None = Field(alias="limitUpPrice")
    limit_down_price: float | None = Field(alias="limitDownPrice")
    is_st: bool = Field(alias="isSt")
    is_limit_up: bool = Field(alias="isLimitUp")
    is_limit_down: bool = Field(alias="isLimitDown")
    is_suspended: bool = Field(alias="isSuspended")
    can_buy: bool = Field(alias="canBuy")
    can_sell: bool = Field(alias="canSell")
