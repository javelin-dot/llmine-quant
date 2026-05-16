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
    strategy_id: str | None = Field(default=None, alias="strategyId")
    initial_cash: float = Field(default=1_000_000.0, alias="initialCash")
    strategy_params: dict[str, Any] = Field(default_factory=dict, alias="strategyParams")
    cost_config: BacktestCostIn = Field(default_factory=BacktestCostIn, alias="costConfig")
    in_sample_end_date: str | None = Field(
        default=None,
        alias="inSampleEndDate",
        description="Inclusive split point — dates after this are OOS. "
        "Must be within [startDate, endDate).",
    )


class UniverseSuggestIn(BaseModel):
    """Three-step universe builder criteria (三步选股法).

    Step 1 — 流动性筛选 (Liquidity): index pool + data depth + average turnover.
    Step 2 — 波动率筛选 (Volatility): annualized vol band (drop dead stocks and
              hyper-volatile noise).
    Step 3 — 动量筛选 (Momentum): trailing return over a lookback window.
    """

    model_config = ConfigDict(populate_by_name=True)

    strategy_family: str = Field(default="trend", alias="strategyFamily")
    max_symbols: int = Field(default=20, ge=1, le=200, alias="maxSymbols")
    diversify: bool = True

    # Step 1 — liquidity
    index_pool: str = Field(default="both", alias="indexPool")
    # one of: 'csi300' | 'csi500' | 'csi1000' | 'both' | 'all'
    # - csi300 / csi500 / csi1000:  index constituents (with weights)
    # - both:                       CSI 300 + CSI 500 union
    # - all:                        every A-share stock (~5k symbols, no weights)
    boards: list[str] = Field(default_factory=list, alias="boards")
    # Exchange-board filter (subset, empty = unrestricted). Values:
    #   'main'    — 沪深主板 (600/601/603/605/000/001/002)
    #   'star'    — 科创板 (688/689)
    #   'chinext' — 创业板 (300/301)
    #   'bse'     — 北交所 (43/83/87/92/8)
    sectors: list[str] = Field(default_factory=list, alias="sectors")
    # Industry sector names (申万行业, empty = unrestricted), e.g. ['半导体', '医药生物']
    min_bars: int = Field(default=60, ge=1, alias="minBars")
    min_avg_turnover_cny: float = Field(default=1e8, ge=0, alias="minAvgTurnoverCny")
    # average daily turnover in CNY (default 1亿元 ≈ 100M CNY)

    # Step 2 — volatility band (annualized)
    min_volatility: float = Field(default=0.10, ge=0, le=5, alias="minVolatility")
    max_volatility: float = Field(default=0.80, ge=0, le=5, alias="maxVolatility")

    # Step 3 — momentum
    momentum_window_days: int = Field(default=60, ge=5, le=500, alias="momentumWindowDays")
    min_momentum: float = Field(default=-0.20, ge=-1.0, le=5.0, alias="minMomentum")
    max_momentum: float = Field(default=2.0, ge=-1.0, le=10.0, alias="maxMomentum")


class UniverseCandidate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    name: str | None = None
    bars: int
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    coverage_days: int = Field(alias="coverageDays")
    selected: bool
    reason: str | None = None  # AI-generated selection / exclusion reason
    avg_turnover: float | None = Field(default=None, alias="avgTurnover")
    volatility: float | None = None
    momentum: float | None = None
    drop_reason: str | None = Field(default=None, alias="dropReason")


class UniverseSuggestOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    symbols: list[str]
    candidates: list[UniverseCandidate]
    diversity_score: float = Field(alias="diversityScore")
    coverage_days: int = Field(alias="coverageDays")
    recommendation: str
    ai_rationale: str | None = Field(default=None, alias="aiRationale")
    ai_model: str | None = Field(default=None, alias="aiModel")
    # Honest pool-size accounting — `candidates` is truncated for UI rendering.
    total_pool: int = Field(default=0, alias="totalPool")
    total_eligible: int = Field(default=0, alias="totalEligible")
    total_rejected: int = Field(default=0, alias="totalRejected")


class BacktestMetricOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cumulative_return: float = Field(alias="cumulativeReturn")
    annual_return: float = Field(alias="annualReturn")
    max_drawdown: float = Field(alias="maxDrawdown")
    sharpe_ratio: float = Field(alias="sharpeRatio")
    win_rate: float = Field(alias="winRate")
    turnover: float
    calmar_ratio: float = Field(default=0.0, alias="calmarRatio")
    sortino_ratio: float = Field(default=0.0, alias="sortinoRatio")
    volatility: float = Field(default=0.0)
    profit_factor: float = Field(default=0.0, alias="profitFactor")


class BacktestEquityPointOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_date: str = Field(alias="tradeDate")
    value: float
    drawdown: float | None = None
    phase: str = "is"  # is / oos


class WalkForwardFoldOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fold_index: int = Field(alias="foldIndex")
    train_start: str = Field(alias="trainStart")
    train_end: str = Field(alias="trainEnd")
    test_start: str = Field(alias="testStart")
    test_end: str = Field(alias="testEnd")
    train_return: float = Field(alias="trainReturn")
    test_return: float = Field(alias="testReturn")
    train_sharpe: float = Field(alias="trainSharpe")
    test_sharpe: float = Field(alias="testSharpe")
    train_max_dd: float = Field(alias="trainMaxDd")
    test_max_dd: float = Field(alias="testMaxDd")


class BacktestTaskListItem(BaseModel):
    """One row in the recent-backtests list (lightweight, no equity curve)."""

    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(alias="taskId")
    run_id: str | None = Field(default=None, alias="runId")
    status: str
    strategy_version_id: str | None = Field(default=None, alias="strategyVersionId")
    strategy_name: str | None = Field(default=None, alias="strategyName")
    start_date: str | None = Field(default=None, alias="startDate")
    end_date: str | None = Field(default=None, alias="endDate")
    in_sample_end_date: str | None = Field(default=None, alias="inSampleEndDate")
    universe: list[str] = Field(default_factory=list)
    cumulative_return: float | None = Field(default=None, alias="cumulativeReturn")
    sharpe_ratio: float | None = Field(default=None, alias="sharpeRatio")
    max_drawdown: float | None = Field(default=None, alias="maxDrawdown")
    overfit_level: str | None = Field(default=None, alias="overfitLevel")
    created_at: str = Field(alias="createdAt")


class BacktestTradeOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_date: str = Field(alias="tradeDate")
    symbol: str
    side: str
    quantity: float
    price: float
    amount: float
    target_weight: float = Field(alias="targetWeight")
    total_cost: float = Field(alias="totalCost")
    net_cash_flow: float = Field(alias="netCashFlow")
    reason: str | None = None


class BacktestReportOut(BaseModel):
    """Unified report aggregating every Phase 3 artefact for a backtest task."""

    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(alias="taskId")
    run_id: str | None = Field(default=None, alias="runId")
    summary: "BacktestTaskResultOut"
    walk_forward_folds: list["WalkForwardFoldOut"] = Field(default_factory=list, alias="walkForwardFolds")
    sensitivity_runs: list["SensitivityRunOut"] = Field(default_factory=list, alias="sensitivityRuns")
    overfit: "OverfitAssessmentOut | None" = None
    trades: list[BacktestTradeOut] = Field(default_factory=list)
    feature_usage: list[dict[str, str | None]] = Field(default_factory=list, alias="featureUsage")
    lineage_node_count: int = Field(default=0, alias="lineageNodeCount")
    lineage_edge_count: int = Field(default=0, alias="lineageEdgeCount")
    lab_checklist: list["BacktestLabCheckOut"] = Field(default_factory=list, alias="labChecklist")
    promotion_gate: "BacktestPromotionGateOut | None" = Field(default=None, alias="promotionGate")


class BacktestLabCheckOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    label: str
    status: str  # pass / warn / fail
    detail: str


class BacktestPromotionGateOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    decision: str  # pass / review / block
    label: str
    readiness_score: int = Field(alias="readinessScore")
    reasons: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list, alias="nextActions")


class OverfitComponentOut(BaseModel):
    name: str
    score: float
    detail: str


class OverfitAssessmentOut(BaseModel):
    score: int
    level: str  # low / medium / high
    components: list[OverfitComponentOut]


class SensitivityRunOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    kind: str
    label: str
    is_baseline: bool = Field(alias="isBaseline")
    cumulative_return: float = Field(alias="cumulativeReturn")
    annual_return: float = Field(alias="annualReturn")
    max_drawdown: float = Field(alias="maxDrawdown")
    sharpe_ratio: float = Field(alias="sharpeRatio")
    win_rate: float = Field(alias="winRate")
    turnover: float


class SensitivityCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    universe: list[str]
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    strategy_name: str = Field(default="dual_ma", alias="strategyName")
    strategy_id: str | None = Field(default=None, alias="strategyId")
    initial_cash: float = Field(default=1_000_000.0, alias="initialCash")
    strategy_params: dict[str, Any] = Field(default_factory=dict, alias="strategyParams")
    cost_config: BacktestCostIn = Field(default_factory=BacktestCostIn, alias="costConfig")
    in_sample_end_date: str | None = Field(default=None, alias="inSampleEndDate")


class SensitivityResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(alias="taskId")
    run_id: str = Field(alias="runId")
    runs: list[SensitivityRunOut]


class WalkForwardCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    universe: list[str]
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    strategy_name: str = Field(default="dual_ma", alias="strategyName")
    strategy_id: str | None = Field(default=None, alias="strategyId")
    initial_cash: float = Field(default=1_000_000.0, alias="initialCash")
    strategy_params: dict[str, Any] = Field(default_factory=dict, alias="strategyParams")
    cost_config: BacktestCostIn = Field(default_factory=BacktestCostIn, alias="costConfig")
    in_sample_end_date: str | None = Field(default=None, alias="inSampleEndDate")
    folds: int = Field(default=4, ge=2, le=20)
    train_ratio: float = Field(default=0.7, ge=0.1, lt=1.0, alias="trainRatio")


class WalkForwardResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(alias="taskId")
    run_id: str = Field(alias="runId")
    folds: list[WalkForwardFoldOut]
    aggregate: "BacktestMetricOut"


class BacktestTaskResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(alias="taskId")
    status: str
    run_id: str | None = Field(default=None, alias="runId")
    metrics: BacktestMetricOut | None = None
    in_sample_metrics: BacktestMetricOut | None = Field(default=None, alias="inSampleMetrics")
    out_sample_metrics: BacktestMetricOut | None = Field(default=None, alias="outSampleMetrics")
    in_sample_end_date: str | None = Field(default=None, alias="inSampleEndDate")
    equity_curve: list[BacktestEquityPointOut] = Field(default_factory=list, alias="equityCurve")
    monthly_returns: dict[str, float] = Field(default_factory=dict, alias="monthlyReturns")
