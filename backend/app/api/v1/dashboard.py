"""Dashboard API — returns overview data aligned with frontend MockData."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.dashboard import (
    Agent,
    Alert,
    DashboardOverview,
    DashboardStrategy,
    EquityPoint,
    MarketIndex,
    Meta,
    ModalData,
    PortfolioMetrics,
    SystemHealth,
)

router = APIRouter()


# ── Mock data (will be replaced by database queries in later milestones) ──

_META = Meta(product="LLMine Quant", subtitle="AI-Native Trading Engine")

_SYSTEM = SystemHealth(
    healthScore=94,
    healthStatusLabel="HEALTHY",
    healthBarHeights=[8, 14, 10, 18, 12, 16, 10, 14, 12, 10, 8, 14],
    autopilot=True,
    riskGateLabel="风控门 · NORMAL",
)

_MODALS: dict[str, ModalData] = {
    "global": ModalData(
        title="全局概览",
        body="系统运行正常，所有核心模块在线。当前有 7 个策略在运行，3 个待审批订单。",
        primary="确认",
    ),
    "kill": ModalData(
        title="Kill Switch",
        body="确认触发全局熔断？此操作将暂停所有策略的新开仓，仅允许平仓。",
        primary="确认熔断",
    ),
    "create": ModalData(
        title="新建策略",
        body="AI 正在根据您的描述生成策略代码...",
        primary="查看详情",
    ),
    "autopilot": ModalData(
        title="AI Autopilot",
        body="Autopilot 当前处于开启状态。AI Agent 将自动执行模拟盘交易并生成实盘提案。",
        primary="确认",
    ),
    "approve": ModalData(
        title="审批确认",
        body="请确认该订单的所有风控检查已通过。",
        primary="批准",
    ),
    "pause": ModalData(
        title="暂停策略",
        body="确认暂停该策略？当前持仓将保持不变。",
        primary="确认暂停",
    ),
}

_MARKET_INDICES = [
    MarketIndex(name="上证指数", symbol="000001.SH", price=3350.12, change=0.32, volume="4523亿"),
    MarketIndex(name="深证成指", symbol="399001.SZ", price=10872.45, change=0.45, volume="6128亿"),
    MarketIndex(name="创业板指", symbol="399006.SZ", price=2180.89, change=-0.12, volume="2845亿"),
]

_PORTFOLIO_METRICS = PortfolioMetrics(
    totalReturn=0.37,
    annualReturn=0.185,
    maxDrawdown=-0.123,
    sharpeRatio=1.34,
    sortinoRatio=1.89,
    benchmark="000300.SH",
    benchmarkReturn=0.08,
)

_EQUITY_CURVE = [
    EquityPoint(date="2026-01-01", value=1.0, benchmark=1.0),
    EquityPoint(date="2026-01-15", value=1.03, benchmark=1.01),
    EquityPoint(date="2026-02-01", value=1.08, benchmark=1.02),
    EquityPoint(date="2026-02-15", value=1.12, benchmark=1.03),
    EquityPoint(date="2026-03-01", value=1.18, benchmark=1.05),
    EquityPoint(date="2026-03-15", value=1.22, benchmark=1.04),
    EquityPoint(date="2026-04-01", value=1.28, benchmark=1.06),
    EquityPoint(date="2026-04-15", value=1.32, benchmark=1.07),
    EquityPoint(date="2026-05-01", value=1.37, benchmark=1.08),
]

_AGENTS = [
    Agent(avatar="R", name="Research", detail="扫描市场结构", metric="3 tasks", status="active"),
    Agent(avatar="S", name="Strategy", detail="生成策略代码", metric="2 drafts", status="active"),
    Agent(avatar="B", name="Backtest", detail="执行回测验证", metric="5 running", status="active"),
    Agent(avatar="X", name="Explain", detail="归因分析", metric="idle", status="idle"),
    Agent(avatar="P", name="Portfolio", detail="组合优化", metric="1 proposal", status="waiting"),
    Agent(avatar="E", name="Execution", detail="订单执行", metric="3 pending", status="attention"),
    Agent(avatar="K", name="Risk", detail="风控检查", metric="0 breaches", status="active"),
]

_ALERTS = [
    Alert(id="a1", type="approval", title="3 笔实盘订单待审批", time="2 min ago", severity="high"),
    Alert(id="a2", type="risk", title="策略 MA趋势 回撤接近阈值", time="15 min ago", severity="medium", target="risk"),
    Alert(id="a3", type="system", title="数据源 Tushare 延迟升高", time="1h ago", severity="low", target="data"),
]

_STRATEGIES = [
    DashboardStrategy(id="s1", name="MA趋势", type="trend", return_pct=0.185, status="live", sparkline=[1.0, 1.02, 1.05, 1.08, 1.12, 1.15, 1.18], lastSignalTime="09:31"),
    DashboardStrategy(id="s2", name="价值选股", type="value", return_pct=0.221, status="paper", sparkline=[1.0, 1.03, 1.06, 1.09, 1.13, 1.17, 1.20], lastSignalTime="09:30"),
    DashboardStrategy(id="s3", name="行业轮动", type="rotation", return_pct=0.152, status="live", sparkline=[1.0, 1.01, 1.03, 1.02, 1.05, 1.08, 1.10], lastSignalTime="09:28"),
    DashboardStrategy(id="s4", name="XGBoost", type="ml", return_pct=0.284, status="backtest", sparkline=[1.0, 1.04, 1.08, 1.12, 1.16, 1.20, 1.24], lastSignalTime="—"),
    DashboardStrategy(id="s5", name="均值回归", type="mean_reversion", return_pct=0.095, status="draft", sparkline=[1.0, 0.99, 1.01, 1.02, 1.01, 1.03, 1.02], lastSignalTime="—"),
]


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)) -> DashboardOverview:
    """Return the complete dashboard overview aligned with frontend MockData."""
    return DashboardOverview(
        meta=_META,
        system=_SYSTEM,
        modals=_MODALS,
        marketIndices=_MARKET_INDICES,
        portfolioMetrics=_PORTFOLIO_METRICS,
        equityCurve=_EQUITY_CURVE,
        agents=_AGENTS,
        alerts=_ALERTS,
        strategies=_STRATEGIES,
        pendingApprovals=3,
    )


@router.get("/system-health")
async def get_system_health() -> SystemHealth:
    """Return system health status."""
    return _SYSTEM


@router.get("/alerts")
async def get_alerts() -> list[Alert]:
    """Return active alerts."""
    return _ALERTS
