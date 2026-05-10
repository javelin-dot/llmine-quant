"""Execution Service API — approvals, order book, pre-trade checks, execution metrics."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.execution.schemas import (
    AgentTraceOut,
    ApprovalOut,
    ExecutionMetrics,
    ExecutionScreen,
    ExecutionSummary,
    FillRateMetric,
    OrderBookRow,
    PreTradeCheckOut,
    RejectReason,
    SlippageBucket,
    SlippageMetric,
)

router = APIRouter()

_SUMMARY = ExecutionSummary(
    pending=7,
    urgent=3,
    blocked=1,
    approved24h=12,
    avgLatencySec=2.4,
    successRate=0.96,
)

_APPROVALS = [
    ApprovalOut(
        id="ap1", type="live", typeTone="red", symbol="600519", name="贵州茅台",
        side="BUY", qty="100", notional="¥16.8万", notionalPct=0.0168,
        limitPrice="1680.00", stopLoss="1580.00", confidence=0.92, riskGrade="A",
        reason="MA趋势策略发出买入信号，突破20日均线",
        impact="组合权重将从 7.2% 升至 8.5%，仍在风险预算内",
        expireSec=180, urgency="high", urgencyTone="red", strategy="MA趋势",
    ),
    ApprovalOut(
        id="ap2", type="reduce", typeTone="yellow", symbol="300750", name="宁德时代",
        side="SELL", qty="200", notional="¥9.2万", notionalPct=0.0092,
        limitPrice="460.00", stopLoss="—", confidence=0.88, riskGrade="B",
        reason="行业轮动策略建议减仓，新能源板块动量减弱",
        impact="降低组合波动 0.3%，释放现金",
        expireSec=300, urgency="medium", urgencyTone="yellow", strategy="行业轮动",
    ),
    ApprovalOut(
        id="ap3", type="paper", typeTone="green", symbol="002594", name="比亚迪",
        side="BUY", qty="150", notional="¥5.1万", notionalPct=0.0051,
        limitPrice="340.00", stopLoss="310.00", confidence=0.85, riskGrade="B",
        reason="价值选股策略模拟盘测试，PE处于历史低位",
        impact="模拟盘权重 +0.5%，不影响实盘",
        expireSec=600, urgency="low", urgencyTone="green", strategy="价值选股",
    ),
]

_PRE_TRADE_CHECKS = [
    PreTradeCheckOut(name="单票集中上限", current=0.085, limit=0.100, status="pass", statusTone="green", note="个股权重 8.5%，低于 10% 上限"),
    PreTradeCheckOut(name="行业集中上限", current=0.220, limit=0.300, status="pass", statusTone="green", note="新能源行业 22%，低于 30% 上限"),
    PreTradeCheckOut(name="单日亏损限额", current=0.032, limit=0.050, status="pass", statusTone="green", note="当日已实现+浮亏 3.2%，低于 5% 限额"),
    PreTradeCheckOut(name="净敞口限额", current=0.650, limit=0.800, status="pass", statusTone="green", note="净多头 65%，低于 80% 上限"),
    PreTradeCheckOut(name="VaR 限额", current=1.28, limit=2.00, status="pass", statusTone="green", note="日 VaR 1.28%，低于 2% 限额"),
]

_ORDER_BOOK = [
    OrderBookRow(
        time="09:31:15", symbol="600519", side="BUY", qty="100", limit="1680.00",
        filled="100", status="filled", statusTone="green", slippageBps=2.1, pnl=None,
    ),
    OrderBookRow(
        time="09:30:42", symbol="300750", side="SELL", qty="200", limit="462.00",
        filled="150", status="partial", statusTone="yellow", slippageBps=4.5, pnl=1250.0,
    ),
    OrderBookRow(
        time="09:28:10", symbol="002594", side="BUY", qty="150", limit="338.50",
        filled="0", status="working", statusTone="blue", slippageBps=0.0, pnl=None,
    ),
    OrderBookRow(
        time="09:25:33", symbol="000858", side="BUY", qty="300", limit="145.00",
        filled="0", status="rejected", statusTone="red", slippageBps=0.0, pnl=None,
    ),
]

_METRICS = ExecutionMetrics(
    slippage=SlippageMetric(
        avgBps=3.2,
        p50Bps=2.8,
        p95Bps=12.5,
        buckets=[
            SlippageBucket(range="0-2", count=45),
            SlippageBucket(range="2-5", count=32),
            SlippageBucket(range="5-10", count=15),
            SlippageBucket(range="10-20", count=6),
            SlippageBucket(range=">20", count=2),
        ],
    ),
    fillRate=FillRateMetric(total=100, filled=82, partial=12, rejected=4, canceled=2),
    rejectReasons=[
        RejectReason(reason="价格超出涨跌停限制", count=2, tone="red"),
        RejectReason(reason="账户资金不足", count=1, tone="yellow"),
        RejectReason(reason="风控拦截", count=1, tone="purple"),
    ],
)

_AGENT_TRACE = [
    AgentTraceOut(time="09:31:20", agent="Execution", action="订单成交", detail="贵州茅台 100股 @ 1680.20，滑点 2.1bps", tone="green", icon="check"),
    AgentTraceOut(time="09:30:45", agent="Execution", action="部分成交", detail="宁德时代 150/200股 @ 462.30，剩余 50股", tone="yellow", icon="clock"),
    AgentTraceOut(time="09:28:15", agent="Risk", action="预交易检查通过", detail="比亚迪买入通过所有风控检查", tone="green", icon="shield"),
    AgentTraceOut(time="09:25:35", agent="Risk", action="订单拒绝", detail="五粮液买入被风控拦截：价格超出涨跌幅限制", tone="red", icon="x"),
    AgentTraceOut(time="09:20:10", agent="Portfolio", action="再平衡建议", detail="建议减仓宁德时代 2%，增配贵州茅台 1.5%", tone="blue", icon="refresh"),
]


@router.get("/overview", response_model=ExecutionScreen)
async def get_execution_overview(db: AsyncSession = Depends(get_db)) -> ExecutionScreen:
    """Return the complete Execution Center screen data."""
    return ExecutionScreen(
        summary=_SUMMARY,
        approvals=_APPROVALS,
        preTradeChecks=_PRE_TRADE_CHECKS,
        orderBook=_ORDER_BOOK,
        metrics=_METRICS,
        agentTrace=_AGENT_TRACE,
    )


@router.post("/approvals/{approval_id}/approve")
async def approve_trade(approval_id: str) -> dict[str, str]:
    """Approve a pending trade."""
    return {"approval_id": approval_id, "status": "approved"}


@router.post("/approvals/{approval_id}/reject")
async def reject_trade(approval_id: str) -> dict[str, str]:
    """Reject a pending trade."""
    return {"approval_id": approval_id, "status": "rejected"}
