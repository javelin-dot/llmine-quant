"""Backtest Service API — backtest tasks, runs, reports, equity curves."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.backtest.schemas import (
    BacktestComparisonRow,
    BacktestScreen,
    ConfidenceFeature,
    ConfidenceTower,
    CurvePoint,
    EquityCurve,
    Kpi,
    ParameterHeatmap,
    StressScenario,
    WalkForwardFold,
)

router = APIRouter()

_KPIS = [
    Kpi(label="累计收益", value="+37.0%", trend="▲", tone="green"),
    Kpi(label="年化收益", value="+18.5%", trend="▲", tone="green"),
    Kpi(label="最大回撤", value="-12.3%", trend="▼", tone="yellow"),
    Kpi(label="夏普比率", value="1.34", trend="▲", tone="green"),
    Kpi(label="胜率", value="58.2%", trend="▲", tone="green"),
    Kpi(label="盈亏比", value="1.82", trend="▲", tone="green"),
]

_EQUITY_CURVE = EquityCurve(
    label="MA趋势策略",
    inSample=[
        CurvePoint(date="2024-01-02", value=1.0),
        CurvePoint(date="2024-02-01", value=1.05),
        CurvePoint(date="2024-03-01", value=1.12),
        CurvePoint(date="2024-04-01", value=1.18),
        CurvePoint(date="2024-05-01", value=1.25),
        CurvePoint(date="2024-06-01", value=1.30),
        CurvePoint(date="2024-07-01", value=1.28),
        CurvePoint(date="2024-08-01", value=1.35),
    ],
    outSample=[
        CurvePoint(date="2024-09-01", value=1.38),
        CurvePoint(date="2024-10-01", value=1.32),
        CurvePoint(date="2024-11-01", value=1.40),
        CurvePoint(date="2024-12-01", value=1.37),
    ],
    drawdown=[
        CurvePoint(date="2024-01-02", value=0.0),
        CurvePoint(date="2024-02-01", value=-0.02),
        CurvePoint(date="2024-03-01", value=-0.01),
        CurvePoint(date="2024-04-01", value=-0.05),
        CurvePoint(date="2024-05-01", value=-0.03),
        CurvePoint(date="2024-06-01", value=-0.08),
        CurvePoint(date="2024-07-01", value=-0.12),
        CurvePoint(date="2024-08-01", value=-0.09),
        CurvePoint(date="2024-09-01", value=-0.06),
        CurvePoint(date="2024-10-01", value=-0.10),
        CurvePoint(date="2024-11-01", value=-0.04),
        CurvePoint(date="2024-12-01", value=-0.07),
    ],
)

_CONFIDENCE = ConfidenceTower(
    score=78,
    label="稳健",
    features=[
        ConfidenceFeature(title="IS/OOS 比率", desc="样本外收益 / 样本内收益", score="0.68", tone="green"),
        ConfidenceFeature(title="参数稳定性", desc="参数扰动后收益变化", score="0.72", tone="green"),
        ConfidenceFeature(title="滑点敏感性", desc="+1‰ 滑点对收益影响", score="-3.2%", tone="yellow"),
        ConfidenceFeature(title="夏普比率衰减", desc="OOS 夏普 / IS 夏普", score="0.65", tone="green"),
        ConfidenceFeature(title="最大回撤一致性", desc="IS 与 OOS 回撤差异", score="+2.1%", tone="yellow"),
    ],
)

_WALK_FORWARD = {
    "folds": [
        WalkForwardFold(period="2023 Q1", isReturn=0.08, oosReturn=0.06),
        WalkForwardFold(period="2023 Q2", isReturn=0.12, oosReturn=0.09),
        WalkForwardFold(period="2023 Q3", isReturn=0.05, oosReturn=0.04),
        WalkForwardFold(period="2023 Q4", isReturn=0.10, oosReturn=0.08),
        WalkForwardFold(period="2024 Q1", isReturn=0.15, oosReturn=0.11),
    ]
}

_COMPARISON = [
    BacktestComparisonRow(id="s1", name="MA趋势", family="trend", annualReturn=0.185, maxDd=-0.123, sharpe=1.34, oosScore=78, overfit="low", status="live", sparkline=[1.0, 1.02, 1.05, 1.08, 1.12, 1.15, 1.18]),
    BacktestComparisonRow(id="s2", name="价值选股", family="value", annualReturn=0.221, maxDd=-0.098, sharpe=1.56, oosScore=85, overfit="low", status="paper", sparkline=[1.0, 1.03, 1.06, 1.09, 1.13, 1.17, 1.20]),
    BacktestComparisonRow(id="s3", name="行业轮动", family="rotation", annualReturn=0.152, maxDd=-0.156, sharpe=1.12, oosScore=72, overfit="medium", status="live", sparkline=[1.0, 1.01, 1.03, 1.02, 1.05, 1.08, 1.10]),
    BacktestComparisonRow(id="s4", name="XGBoost", family="ml", annualReturn=0.284, maxDd=-0.189, sharpe=1.42, oosScore=91, overfit="low", status="backtest", sparkline=[1.0, 1.04, 1.08, 1.12, 1.16, 1.20, 1.24]),
]

_SCENARIOS = [
    StressScenario(id="sc1", name="2015 股灾", severity="high", loss="-18.5%", maxDd="-25.3%", fuse="触发 L2", fuseTone="red", suggestion="降低仓位至 50%，暂停新开仓", human="需人工确认"),
    StressScenario(id="sc2", name="2018 熊市", severity="medium", loss="-12.1%", maxDd="-15.8%", fuse="触发 L1", fuseTone="yellow", suggestion="减仓至 70%，加强监控", human="自动处理"),
    StressScenario(id="sc3", name="2020 疫情", severity="high", loss="-22.3%", maxDd="-28.1%", fuse="触发 L3", fuseTone="red", suggestion="清仓观察", human="需人工确认"),
    StressScenario(id="sc4", name="2024 震荡", severity="low", loss="-5.2%", maxDd="-8.1%", fuse="未触发", fuseTone="green", suggestion="维持当前仓位", human="自动处理"),
]

_HEATMAP = ParameterHeatmap(
    xLabel="MA短周期",
    yLabel="MA长周期",
    xTicks=["3", "5", "10", "15", "20"],
    yTicks=["10", "20", "30", "60", "120"],
    cells=[
        [0.12, 0.15, 0.18, 0.14, 0.10],
        [0.14, 0.19, 0.22, 0.18, 0.13],
        [0.11, 0.16, 0.20, 0.17, 0.12],
        [0.09, 0.13, 0.16, 0.15, 0.11],
        [0.07, 0.10, 0.12, 0.11, 0.08],
    ],
    bestX=2,
    bestY=1,
)


@router.get("/overview", response_model=BacktestScreen)
async def get_backtest_overview(db: AsyncSession = Depends(get_db)) -> BacktestScreen:
    """Return the complete Backtest Lab screen data."""
    return BacktestScreen(
        kpis=_KPIS,
        equityCurves=_EQUITY_CURVE,
        confidence=_CONFIDENCE,
        walkForward=_WALK_FORWARD,
        comparison=_COMPARISON,
        scenarios=_SCENARIOS,
        parameterHeatmap=_HEATMAP,
    )


@router.post("/")
async def create_backtest_task() -> dict[str, str]:
    """Create a backtest task."""
    return {"task_id": "bt-001", "status": "queued"}


@router.get("/{task_id}")
async def get_backtest_task(task_id: str) -> dict[str, str]:
    """Get backtest task status."""
    return {"task_id": task_id, "status": "completed"}
