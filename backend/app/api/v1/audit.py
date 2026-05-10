"""Audit Service API — immutable audit logs, actor stats, tool registry, HITL rules."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.audit.schemas import (
    ActorStat,
    AuditKpi,
    AuditRow,
    AuditScreen,
    HitlRule,
    ToolRegistryItem,
)

router = APIRouter()

_KPIS = [
    AuditKpi(label="今日事件", value="1,245", trend="▲", tone="blue"),
    AuditKpi(label="Agent 操作", value="892", trend="▲", tone="green"),
    AuditKpi(label="人工审批", value="47", trend="▼", tone="yellow"),
    AuditKpi(label="异常事件", value="3", trend="→", tone="red"),
    AuditKpi(label="哈希链完整", value="100%", trend="→", tone="green"),
]

_ROWS = [
    AuditRow(
        time="09:31:15", actor="MA趋势 Agent", actorType="agent", action="生成买入信号",
        resource="600519", result="成功", resultTone="green", confidence=0.92,
        detail="买入贵州茅台 100股，置信度 92%", traceId="trace-20260510-093115",
    ),
    AuditRow(
        time="09:31:12", actor="Risk Agent", actorType="agent", action="预交易检查",
        resource="600519", result="通过", resultTone="green", confidence=1.0,
        detail="通过集中度、VaR、涨跌停检查", traceId="trace-20260510-093115",
    ),
    AuditRow(
        time="09:30:45", actor="Execution Agent", actorType="agent", action="执行订单",
        resource="300750", result="部分成交", resultTone="yellow", confidence=0.85,
        detail="卖出宁德时代 150/200股，滑点 4.5bps", traceId="trace-20260510-093045",
    ),
    AuditRow(
        time="09:25:33", actor="Risk Agent", actorType="agent", action="拦截订单",
        resource="000858", result="拒绝", resultTone="red", confidence=1.0,
        detail="价格超出涨跌幅限制，订单被拒绝", traceId="trace-20260510-092533",
    ),
    AuditRow(
        time="09:20:10", actor="投资总监", actorType="human", action="审批通过",
        resource="MA趋势", result="批准", resultTone="green", confidence=1.0,
        detail="批准 MA趋势策略 v1.3 上线", traceId="trace-20260510-092010",
    ),
]

_ACTOR_STATS = [
    ActorStat(actor="Strategy Agent", count=342, tone="blue"),
    ActorStat(actor="Risk Agent", count=278, tone="green"),
    ActorStat(actor="Execution Agent", count=156, tone="yellow"),
    ActorStat(actor="Portfolio Agent", count=89, tone="purple"),
    ActorStat(actor="Human Reviewer", count=47, tone="red"),
]

_TOOL_REGISTRY = [
    ToolRegistryItem(
        name="place_order", level="高风险", levelTone="red",
        desc="执行买卖订单", agents=["Execution", "Portfolio"],
    ),
    ToolRegistryItem(
        name="cancel_order", level="中风险", levelTone="yellow",
        desc="撤销未成交订单", agents=["Execution", "Risk"],
    ),
    ToolRegistryItem(
        name="query_position", level="低风险", levelTone="green",
        desc="查询持仓信息", agents=["Portfolio", "Risk", "Execution"],
    ),
    ToolRegistryItem(
        name="run_backtest", level="低风险", levelTone="green",
        desc="运行策略回测", agents=["Backtest", "Strategy"],
    ),
    ToolRegistryItem(
        name="adjust_risk_budget", level="高风险", levelTone="red",
        desc="调整风险预算", agents=["Risk"],
    ),
]

_HITL_RULES = [
    HitlRule(rule="实盘订单审批", desc="所有实盘账户订单需人工审批", status="approval", statusTone="red"),
    HitlRule(rule="策略上线审批", desc="策略从模拟盘切换到实盘需审批", status="approval", statusTone="red"),
    HitlRule(rule="大额交易提醒", desc="单笔交易超过 50 万需提醒", status="review", statusTone="yellow"),
    HitlRule(rule="数据异常处理", desc="数据漂移超过阈值自动暂停策略", status="auto", statusTone="green"),
    HitlRule(rule="熔断恢复", desc="L2 及以上熔断恢复需人工确认", status="approval", statusTone="red"),
]


@router.get("/overview", response_model=AuditScreen)
async def get_audit_overview(db: AsyncSession = Depends(get_db)) -> AuditScreen:
    """Return the complete Audit & Compliance screen data."""
    return AuditScreen(
        kpis=_KPIS,
        rows=_ROWS,
        actorStats=_ACTOR_STATS,
        toolRegistry=_TOOL_REGISTRY,
        hitlRules=_HITL_RULES,
    )
