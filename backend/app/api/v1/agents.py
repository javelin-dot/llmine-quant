"""Agent Orchestrator API — agent registry, tasks, messages, tool registry."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.agents.schemas import (
    AgentMessageOut,
    AgentOut,
    AgentOverview,
    AgentTaskOut,
    ToolOut,
)

router = APIRouter()

_AGENTS = [
    AgentOut(id="a1", name="Research", role="research", status="active", statusTone="green", currentTask="扫描市场结构", metric="3 tasks", heartbeat="2s ago"),
    AgentOut(id="a2", name="Strategy", role="strategy", status="active", statusTone="green", currentTask="生成策略代码", metric="2 drafts", heartbeat="5s ago"),
    AgentOut(id="a3", name="Backtest", role="backtest", status="active", statusTone="green", currentTask="执行回测验证", metric="5 running", heartbeat="3s ago"),
    AgentOut(id="a4", name="Explain", role="explain", status="idle", statusTone="gray", currentTask="等待信号", metric="idle", heartbeat="1m ago"),
    AgentOut(id="a5", name="Portfolio", role="portfolio", status="waiting", statusTone="blue", currentTask="组合优化", metric="1 proposal", heartbeat="10s ago"),
    AgentOut(id="a6", name="Execution", role="execution", status="attention", statusTone="yellow", currentTask="订单执行", metric="3 pending", heartbeat="4s ago"),
    AgentOut(id="a7", name="Risk", role="risk", status="active", statusTone="green", currentTask="风控检查", metric="0 breaches", heartbeat="1s ago"),
    AgentOut(id="a8", name="Data", role="data", status="active", statusTone="green", currentTask="数据同步", metric="12 sources", heartbeat="6s ago"),
]

_TASKS = [
    AgentTaskOut(id="t1", agentId="a1", agentName="Research", taskType="market_scan", priority=1, status="running", statusTone="green", createdAt="09:00", startedAt="09:00", completedAt=None, result=None),
    AgentTaskOut(id="t2", agentId="a2", agentName="Strategy", taskType="code_gen", priority=2, status="running", statusTone="green", createdAt="09:05", startedAt="09:05", completedAt=None, result=None),
    AgentTaskOut(id="t3", agentId="a3", agentName="Backtest", taskType="backtest_run", priority=1, status="pending", statusTone="yellow", createdAt="09:10", startedAt=None, completedAt=None, result=None),
    AgentTaskOut(id="t4", agentId="a6", agentName="Execution", taskType="order_submit", priority=3, status="failed", statusTone="red", createdAt="09:25", startedAt="09:25", completedAt="09:26", result="价格超出涨跌幅限制"),
]

_MESSAGES = [
    AgentMessageOut(id="m1", fromAgent="Research", toAgent="Strategy", msgType="event", topic="market_signal", payload='{"sector": "新能源", "momentum": 0.85}', correlationId="corr-001", createdAt="09:20"),
    AgentMessageOut(id="m2", fromAgent="Strategy", toAgent="Backtest", msgType="request", topic="run_backtest", payload='{"strategy_id": "s1", "version": "v1.3"}', correlationId="corr-002", createdAt="09:25"),
    AgentMessageOut(id="m3", fromAgent="Backtest", toAgent="Strategy", msgType="response", topic="backtest_result", payload='{"sharpe": 1.34, "max_dd": -0.123}', correlationId="corr-002", createdAt="09:30"),
    AgentMessageOut(id="m4", fromAgent="Risk", toAgent="Execution", msgType="broadcast", topic="risk_alert", payload='{"level": "L1", "message": "回撤接近阈值"}', correlationId=None, createdAt="09:15"),
]

_TOOLS = [
    ToolOut(id="tool1", name="place_order", level="高风险", levelTone="red", description="执行买卖订单", allowedAgents=["Execution", "Portfolio"], enabled=True),
    ToolOut(id="tool2", name="cancel_order", level="中风险", levelTone="yellow", description="撤销未成交订单", allowedAgents=["Execution", "Risk"], enabled=True),
    ToolOut(id="tool3", name="query_position", level="低风险", levelTone="green", description="查询持仓信息", allowedAgents=["Portfolio", "Risk", "Execution"], enabled=True),
    ToolOut(id="tool4", name="run_backtest", level="低风险", levelTone="green", description="运行策略回测", allowedAgents=["Backtest", "Strategy"], enabled=True),
    ToolOut(id="tool5", name="adjust_risk_budget", level="高风险", levelTone="red", description="调整风险预算", allowedAgents=["Risk"], enabled=True),
]


@router.get("/overview", response_model=AgentOverview)
async def get_agent_overview(db: AsyncSession = Depends(get_db)) -> AgentOverview:
    """Return the complete Agent Orchestrator overview."""
    return AgentOverview(
        agents=_AGENTS,
        tasks=_TASKS,
        messages=_MESSAGES,
        tools=_TOOLS,
    )


@router.post("/tasks")
async def create_agent_task(agent_id: str, task_type: str, payload: str) -> dict[str, str]:
    """Create a new agent task."""
    return {"task_id": "task-new", "agent_id": agent_id, "status": "queued"}


@router.post("/messages")
async def send_agent_message(from_agent: str, to_agent: str | None, topic: str, payload: str) -> dict[str, str]:
    """Send an inter-agent message."""
    return {"message_id": "msg-new", "from": from_agent, "to": to_agent, "status": "sent"}
