"""Portfolio Service API — NAV, allocation, correlation, concentration, rebalance."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.portfolio.schemas import (
    Allocation,
    AllocationStrategy,
    Concentration,
    ConcentrationFactor,
    ConcentrationHolding,
    ConcentrationSector,
    Correlation,
    NAV,
    PortfolioScreen,
    RebalanceAction,
    RiskBudget,
)

router = APIRouter()

_NAV = NAV(
    total=12460000.0,
    currency="CNY",
    todayPnl=84200.0,
    todayPct=0.68,
    mtdPct=3.12,
    ytdPct=18.7,
    cashPct=18.0,
    leverage=1.18,
    netExposure=0.78,
    varDaily=124600.0,
    varPct=1.0,
)

_RISK_BUDGET = [
    RiskBudget(label="总风险预算使用率", pct=0.65, limit=0.85, tone="green", desc="距 85% 阈值仍有 20pt 缓冲"),
    RiskBudget(label="单策略最大占比", pct=0.30, limit=0.35, tone="yellow", desc="Value-ROE 30%,接近 35% 上限"),
    RiskBudget(label="行业集中度", pct=0.18, limit=0.25, tone="green", desc="消费板块 18%,在安全区间"),
    RiskBudget(label="现金缓冲", pct=0.18, limit=0.10, tone="blue", desc="高于 10% 下限,可承接调仓"),
]

_ALLOCATION = Allocation(
    strategies=[
        AllocationStrategy(name="Value-ROE-v12", family="价值", weight=0.30, pnl=412000.0, pnlPct=0.158, risk="A-", status="live", statusTone="green", contribution=0.42, sparkline=[1.00, 1.02, 1.03, 1.05, 1.08, 1.10, 1.13, 1.15, 1.16]),
        AllocationStrategy(name="Trend-MA-v8", family="趋势", weight=0.18, pnl=186000.0, pnlPct=0.142, risk="B+", status="live", statusTone="green", contribution=0.18, sparkline=[1.00, 1.01, 1.04, 1.03, 1.06, 1.08, 1.11, 1.12, 1.14]),
        AllocationStrategy(name="Sector-Rotation", family="轮动", weight=0.14, pnl=124000.0, pnlPct=0.124, risk="A", status="live", statusTone="green", contribution=0.13, sparkline=[1.00, 1.02, 1.04, 1.05, 1.07, 1.09, 1.10, 1.11, 1.12]),
        AllocationStrategy(name="XGBoost-Alpha", family="ML", weight=0.10, pnl=98400.0, pnlPct=0.218, risk="B", status="live", statusTone="green", contribution=0.11, sparkline=[1.00, 1.03, 1.05, 1.08, 1.12, 1.15, 1.18, 1.20, 1.22]),
        AllocationStrategy(name="PB-LowVol", family="低波动", weight=0.06, pnl=28400.0, pnlPct=0.062, risk="A+", status="live", statusTone="green", contribution=0.04, sparkline=[1.00, 1.01, 1.02, 1.02, 1.03, 1.04, 1.05, 1.05, 1.06]),
        AllocationStrategy(name="NewEnergy-Pair", family="配对", weight=0.04, pnl=-12400.0, pnlPct=-0.034, risk="B-", status="paper", statusTone="yellow", contribution=-0.01, sparkline=[1.00, 1.02, 1.01, 0.99, 0.98, 0.97, 0.97, 0.96, 0.97]),
        AllocationStrategy(name="Earnings-Drift", family="事件", weight=0.00, pnl=0.0, pnlPct=0.0, risk="A", status="backtest", statusTone="blue", contribution=0.0, sparkline=[1.00, 1.01, 1.03, 1.04, 1.06, 1.08, 1.09, 1.10, 1.11]),
        AllocationStrategy(name="现金缓冲", family="现金", weight=0.18, pnl=1840.0, pnlPct=0.0001, risk="A+", status="live", statusTone="blue", contribution=0.01, sparkline=[1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    ],
)

_CORRELATION = Correlation(
    labels=["Value", "Trend", "Rotation", "XGB", "LowVol", "Pair", "Earn", "Cash"],
    matrix=[
        [1.00, 0.32, 0.45, 0.28, 0.24, 0.12, 0.38, 0.05],
        [0.32, 1.00, 0.58, 0.42, 0.18, 0.22, 0.46, 0.04],
        [0.45, 0.58, 1.00, 0.36, 0.21, 0.18, 0.52, 0.06],
        [0.28, 0.42, 0.36, 1.00, 0.16, 0.14, 0.34, 0.03],
        [0.24, 0.18, 0.21, 0.16, 1.00, 0.08, 0.18, 0.02],
        [0.12, 0.22, 0.18, 0.14, 0.08, 1.00, 0.16, 0.02],
        [0.38, 0.46, 0.52, 0.34, 0.18, 0.16, 1.00, 0.05],
        [0.05, 0.04, 0.06, 0.03, 0.02, 0.02, 0.05, 1.00],
    ],
)

_CONCENTRATION = Concentration(
    sectors=[
        ConcentrationSector(name="消费", weight=0.18, change=0.012),
        ConcentrationSector(name="科技", weight=0.16, change=0.024),
        ConcentrationSector(name="金融", weight=0.14, change=-0.008),
        ConcentrationSector(name="新能源", weight=0.12, change=-0.018),
        ConcentrationSector(name="医药", weight=0.10, change=0.006),
        ConcentrationSector(name="工业", weight=0.08, change=0.002),
        ConcentrationSector(name="材料", weight=0.04, change=-0.004),
    ],
    holdings=[
        ConcentrationHolding(symbol="600519", name="贵州茅台", weight=0.082, change=0.018),
        ConcentrationHolding(symbol="300750", name="宁德时代", weight=0.064, change=-0.024),
        ConcentrationHolding(symbol="600036", name="招商银行", weight=0.058, change=0.006),
        ConcentrationHolding(symbol="000333", name="美的集团", weight=0.052, change=0.014),
        ConcentrationHolding(symbol="002594", name="比亚迪", weight=0.048, change=-0.012),
        ConcentrationHolding(symbol="600276", name="恒瑞医药", weight=0.042, change=0.008),
        ConcentrationHolding(symbol="600900", name="长江电力", weight=0.038, change=0.002),
        ConcentrationHolding(symbol="000858", name="五粮液", weight=0.036, change=0.022),
    ],
    factors=[
        ConcentrationFactor(name="Value 价值", exposure=0.42, tone="green"),
        ConcentrationFactor(name="Quality 质量", exposure=0.38, tone="green"),
        ConcentrationFactor(name="Momentum 动量", exposure=0.24, tone="blue"),
        ConcentrationFactor(name="Size 规模", exposure=-0.18, tone="yellow"),
        ConcentrationFactor(name="Low Vol 低波", exposure=0.16, tone="blue"),
        ConcentrationFactor(name="Yield 红利", exposure=0.12, tone="blue"),
    ],
)

_REBALANCE = [
    RebalanceAction(
        id="r1", type="reduce", from_="Value-ROE-v12", to="现金缓冲", delta="-3%",
        reason="单策略占比 30% 接近上限,建议降至 27% 以保留新机会缓冲",
        impact="DD 预算 +1.2pt · Sharpe -0.04",
        urgency="medium", urgencyTone="yellow",
    ),
    RebalanceAction(
        id="r2", type="add", from_="现金缓冲", to="XGBoost-Alpha", delta="+2%",
        reason="XGBoost OOS 稳定度 86%,且与现有策略相关性 <0.3",
        impact="组合预期收益 +0.4% · 相关性 +0.02",
        urgency="low", urgencyTone="green",
    ),
    RebalanceAction(
        id="r3", type="rotate", from_="NewEnergy-Pair", to="Earnings-Drift", delta="4%",
        reason="新能源配对策略近期回撤扩大,事件驱动策略回测稳定",
        impact="回撤敞口 -0.8% · Beta -0.06",
        urgency="high", urgencyTone="red",
    ),
    RebalanceAction(
        id="r4", type="hedge", from_="消费板块", to="股指期货空头", delta="5%敞口",
        reason="消费集中度 18% 接近预警,北向资金 5 日净流出 -32 亿",
        impact="Beta 暴露 -0.12 · 对冲成本 0.3%",
        urgency="medium", urgencyTone="yellow",
    ),
]


@router.get("/overview", response_model=PortfolioScreen)
async def get_portfolio_overview(db: AsyncSession = Depends(get_db)) -> PortfolioScreen:
    """Return the complete Portfolio Cockpit screen data."""
    return PortfolioScreen(
        nav=_NAV,
        riskBudget=_RISK_BUDGET,
        allocation=_ALLOCATION,
        correlation=_CORRELATION,
        concentration=_CONCENTRATION,
        rebalance=_REBALANCE,
    )


@router.post("/rebalance/{proposal_id}/approve")
async def approve_rebalance(proposal_id: str) -> dict[str, str]:
    """Approve a rebalance proposal."""
    return {"proposal_id": proposal_id, "status": "approved"}
