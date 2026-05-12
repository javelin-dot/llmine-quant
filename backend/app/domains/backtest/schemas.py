"""Backtest domain Pydantic schemas aligned with frontend MockData."""

# ruff: noqa: N815

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Kpi(BaseModel):
    label: str
    value: str
    trend: str
    tone: str


class CurvePoint(BaseModel):
    date: str
    value: float


class EquityCurve(BaseModel):
    label: str
    inSample: list[CurvePoint]
    outSample: list[CurvePoint]
    drawdown: list[CurvePoint]


class ConfidenceFeature(BaseModel):
    title: str
    desc: str
    score: str
    tone: str


class ConfidenceTower(BaseModel):
    score: int
    label: str
    features: list[ConfidenceFeature]


class WalkForwardFold(BaseModel):
    period: str
    isReturn: float
    oosReturn: float


class BacktestComparisonRow(BaseModel):
    id: str
    name: str
    family: str
    annualReturn: float
    maxDd: float
    sharpe: float
    oosScore: float
    overfit: str  # low / medium / high
    status: str
    sparkline: list[float]


class StressScenario(BaseModel):
    id: str
    name: str
    severity: str
    loss: str
    maxDd: str
    fuse: str
    fuseTone: str
    suggestion: str
    human: str


class ParameterHeatmap(BaseModel):
    xLabel: str
    yLabel: str
    xTicks: list[str]
    yTicks: list[str]
    cells: list[list[float]]
    bestX: int
    bestY: int


class BacktestScreen(BaseModel):
    kpis: list[Kpi]
    equityCurves: EquityCurve
    confidence: ConfidenceTower
    walkForward: dict[str, list[WalkForwardFold]]
    comparison: list[BacktestComparisonRow]
    scenarios: list[StressScenario]
    parameterHeatmap: ParameterHeatmap


class BacktestCostIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    commission_rate: float = Field(default=0.0003, alias="commissionRate")
    min_commission: float = Field(default=5.0, alias="minCommission")
    stamp_tax_rate: float = Field(default=0.001, alias="stampTaxRate")
    slippage_bps: float = Field(default=1.0, alias="slippageBps")


class BacktestCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    universe: list[str]
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    strategy_name: str = Field(default="dual_ma", alias="strategyName")
    initial_cash: float = Field(default=1_000_000.0, alias="initialCash")
    strategy_params: dict[str, Any] = Field(default_factory=dict, alias="strategyParams")
    cost_config: BacktestCostIn = Field(default_factory=BacktestCostIn, alias="costConfig")


class BacktestMetricOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cumulative_return: float = Field(alias="cumulativeReturn")
    annual_return: float = Field(alias="annualReturn")
    max_drawdown: float = Field(alias="maxDrawdown")
    sharpe_ratio: float = Field(alias="sharpeRatio")
    win_rate: float = Field(alias="winRate")
    turnover: float


class BacktestEquityPointOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_date: str = Field(alias="tradeDate")
    value: float
    drawdown: float | None = None


class BacktestTaskResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(alias="taskId")
    status: str
    run_id: str | None = Field(default=None, alias="runId")
    metrics: BacktestMetricOut | None = None
    equity_curve: list[BacktestEquityPointOut] = Field(default_factory=list, alias="equityCurve")
