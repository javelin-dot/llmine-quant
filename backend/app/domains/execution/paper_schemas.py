"""Pydantic schemas for paper-trading API."""

# ruff: noqa: N815

from pydantic import BaseModel, ConfigDict, Field


class PaperAccountCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    owner_id: str | None = Field(default=None, alias="ownerId")
    strategy_id: str | None = Field(default=None, alias="strategyId")
    strategy_version_id: str | None = Field(default=None, alias="strategyVersionId")
    market: str = "A"
    base_currency: str = Field(default="CNY", alias="baseCurrency")
    initial_cash: float = Field(default=1_000_000.0, alias="initialCash")
    inception_date: str | None = Field(default=None, alias="inceptionDate")
    cost_config: dict[str, float] | None = Field(default=None, alias="costConfig")


class PaperAccountOut(BaseModel):
    id: str
    name: str
    ownerId: str
    strategyId: str | None
    strategyVersionId: str | None
    market: str
    baseCurrency: str
    initialCash: float
    cash: float
    inceptionDate: str | None
    lastProcessedDate: str | None
    peakNav: float | None
    status: str


class PaperAccountBindStrategyIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_id: str = Field(alias="strategyId")
    strategy_version_id: str = Field(alias="strategyVersionId")


class PaperPositionOut(BaseModel):
    symbol: str
    quantity: float
    availableQuantity: float
    todayBuyQuantity: float
    avgCost: float
    lastPrice: float | None
    marketValue: float
    weight: float


class PaperOrderOut(BaseModel):
    id: str
    accountId: str
    strategyId: str | None
    tradeDate: str
    symbol: str
    side: str
    targetWeight: float
    targetQuantity: float
    filledQuantity: float
    status: str
    reason: str | None
    rejectionReason: str | None


class ManualPaperOrderIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    side: str
    quantity: float
    trade_date: str | None = Field(default=None, alias="tradeDate")
    reason: str | None = None
    execution_mode: str = Field(default="immediate", alias="executionMode")


class ReplacePaperOrderIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    quantity: float


class MatchPaperOrdersIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_date: str | None = Field(default=None, alias="tradeDate")


class PaperTargetPositionOut(BaseModel):
    symbol: str
    targetWeight: float
    currentWeight: float
    driftWeight: float
    targetQuantity: float
    currentQuantity: float
    recommendedAction: str
    reason: str | None


class PaperEvaluationSnapshotOut(BaseModel):
    tradeDate: str | None
    sessionStatus: str
    strategyBound: bool
    targetGross: float
    currentGross: float
    driftGross: float
    targets: list[PaperTargetPositionOut]


class PaperFillOut(BaseModel):
    id: str
    orderId: str
    tradeDate: str
    symbol: str
    side: str
    quantity: float
    price: float
    amount: float
    commission: float
    stampTax: float
    slippage: float
    totalCost: float


class PaperNavPointOut(BaseModel):
    tradeDate: str
    nav: float
    cash: float
    marketValue: float
    dailyReturn: float | None
    drawdown: float | None


class PaperRiskBreachOut(BaseModel):
    id: str
    tradeDate: str
    rule: str
    severity: str
    detail: str | None
    status: str


class RunEodIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_date: str = Field(alias="tradeDate")


class RunEodOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(alias="accountId")
    trade_date: str = Field(alias="tradeDate")
    orders_created: int = Field(alias="ordersCreated")
    orders_filled: int = Field(alias="ordersFilled")
    orders_rejected: int = Field(alias="ordersRejected")
    breaches: int
    nav: float | None
