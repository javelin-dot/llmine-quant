"""Risk Service API — risk overview, budgets, VaR, circuit breakers, breaches."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.risk.schemas import (
    CircuitBreaker,
    PolicyDecisionOut,
    RiskBreachOut,
    RiskBudgetRow,
    RiskHeader,
    RiskKpi,
    RiskScreen,
    VaRDecomposition,
    VaRHistory,
    VaRPanel,
)

router = APIRouter()

_HEADER = RiskHeader(
    healthScore=92,
    healthStatus="HEALTHY",
    healthStatusTone="green",
    killSwitchArmed=True,
    lastIncident="2h ago",
    autoBlocks24h=3,
    pendingApprovals=2,
    activeBreaches=1,
)

_KPIS = [
    RiskKpi(label="日VaR", value="¥128.5K", trend="▼", tone="green"),
    RiskKpi(label="周VaR", value="¥342.1K", trend="▼", tone="green"),
    RiskKpi(label="最大回撤", value="-12.3%", trend="▼", tone="yellow"),
    RiskKpi(label="组合Beta", value="0.85", trend="▲", tone="yellow"),
    RiskKpi(label="杠杆", value="1.12x", trend="→", tone="green"),
]

_BUDGETS = [
    RiskBudgetRow(name="单日亏损限额", used=0.032, limit=0.050, unit="绝对", tone="green", desc="当日已实现+浮亏"),
    RiskBudgetRow(name="最大回撤限额", used=0.123, limit=0.200, unit="绝对", tone="yellow", desc="峰值到谷值回撤"),
    RiskBudgetRow(name="单票集中上限", used=0.085, limit=0.100, unit="权重", tone="green", desc="个股权重"),
    RiskBudgetRow(name="行业集中上限", used=0.220, limit=0.300, unit="权重", tone="green", desc="单一行业权重"),
    RiskBudgetRow(name="净敞口限额", used=0.650, limit=0.800, unit="比例", tone="green", desc="净多头/空头比例"),
]

_VAR = VaRPanel(
    daily=128500.0,
    dailyPct=1.28,
    weekly=342100.0,
    weeklyPct=3.42,
    confidence=0.95,
    currency="CNY",
    history=[
        VaRHistory(date="2026-05-01", value=115000.0),
        VaRHistory(date="2026-05-02", value=118000.0),
        VaRHistory(date="2026-05-03", value=112000.0),
        VaRHistory(date="2026-05-04", value=125000.0),
        VaRHistory(date="2026-05-05", value=130000.0),
        VaRHistory(date="2026-05-06", value=128000.0),
        VaRHistory(date="2026-05-07", value=122000.0),
        VaRHistory(date="2026-05-08", value=128500.0),
    ],
    decomposition=[
        VaRDecomposition(strategy="MA趋势", contribution=45200.0, pct=35.2, tone="yellow"),
        VaRDecomposition(strategy="价值选股", contribution=32100.0, pct=25.0, tone="green"),
        VaRDecomposition(strategy="行业轮动", contribution=51300.0, pct=39.8, tone="yellow"),
    ],
)

_CIRCUITS = [
    CircuitBreaker(
        level="L1", name="可恢复熔断", status="armed", statusTone="green",
        trigger="行情延迟 > 5min / 策略心跳异常", action="暂停新开仓，允许平仓",
        triggers24h=0, lastTrigger="—",
    ),
    CircuitBreaker(
        level="L2", name="组合熔断", status="armed", statusTone="green",
        trigger="组合回撤 > 15%", action="减仓至 50% 仓位",
        triggers24h=0, lastTrigger="—",
    ),
    CircuitBreaker(
        level="L3", name="不可恢复熔断", status="armed", statusTone="green",
        trigger="资金异常 / 重复下单 / 风控服务宕机", action="全部暂停，冻结账户",
        triggers24h=0, lastTrigger="—",
    ),
    CircuitBreaker(
        level="L4", name="全市场熔断", status="armed", statusTone="green",
        trigger="大盘单日跌幅 > 7%", action="清仓或暂停",
        triggers24h=0, lastTrigger="—",
    ),
]

_POLICY_STREAM = [
    PolicyDecisionOut(
        time="09:31:15", agent="Risk", request="MA趋势 买入 贵州茅台 100股",
        decision="approval_required", decisionTone="yellow",
        reason="名义金额超过单票限额 80%", durationMs=45,
    ),
    PolicyDecisionOut(
        time="09:30:42", agent="Risk", request="价值选股 卖出 宁德时代 200股",
        decision="allowed", decisionTone="green",
        reason="通过所有风控检查", durationMs=12,
    ),
    PolicyDecisionOut(
        time="09:28:10", agent="Risk", request="行业轮动 买入 比亚迪 150股",
        decision="modified", decisionTone="blue",
        reason="数量调整为 120 股以符合集中度限制", durationMs=28,
    ),
]

_BREACHES = [
    RiskBreachOut(
        time="09:15", severity="medium", severityTone="yellow",
        title="MA趋势策略回撤接近阈值",
        detail="当前回撤 12.3%，接近 L2 熔断阈值 15%",
        resolution="监控中，若继续扩大将自动触发减仓",
        status="ongoing", statusTone="yellow",
    ),
]


@router.get("/overview", response_model=RiskScreen)
async def get_risk_overview(db: AsyncSession = Depends(get_db)) -> RiskScreen:
    """Return the complete Risk Control screen data."""
    return RiskScreen(
        header=_HEADER,
        kpis=_KPIS,
        budgets=_BUDGETS,
        var=_VAR,
        circuits=_CIRCUITS,
        policyStream=_POLICY_STREAM,
        breaches=_BREACHES,
    )


@router.post("/circuit-breakers/{level}/trigger")
async def trigger_circuit(level: str) -> dict[str, str]:
    """Manually trigger a circuit breaker."""
    return {"level": level, "status": "triggered"}


@router.post("/circuit-breakers/{level}/recover")
async def recover_circuit(level: str) -> dict[str, str]:
    """Request circuit breaker recovery."""
    return {"level": level, "status": "recovery_requested"}
