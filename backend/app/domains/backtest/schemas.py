"""Backtest domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel


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
