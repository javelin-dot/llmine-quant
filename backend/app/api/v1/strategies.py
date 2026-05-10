"""Strategy Service API — strategies, versions, tasks, pipeline."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.strategy.schemas import (
    FeedEvent,
    PipelineLane,
    PipelineStatus,
    PipelineTicket,
    StrategyCreate,
    StrategyMatrixRow,
    StrategyScreen,
    StrategyTaskCreate,
    StrategyTemplate,
)

router = APIRouter()

_PIPELINE_STATUS = [
    PipelineStatus(stage="research", count=3, tone="blue"),
    PipelineStatus(stage="backtest", count=5, tone="green"),
    PipelineStatus(stage="paper", count=2, tone="yellow"),
    PipelineStatus(stage="live", count=4, tone="red"),
    PipelineStatus(stage="paused", count=1, tone="purple"),
]

_TEMPLATES = [
    StrategyTemplate(id="t1", name="双均线趋势", risk="balanced", market="A", family="trend", desc="MA5/MA20 交叉策略，适用震荡上行的市场"),
    StrategyTemplate(id="t2", name="价值选股", risk="conservative", market="A", family="value", desc="ROE > 15% 且 PE < 30，月度调仓"),
    StrategyTemplate(id="t3", name="行业轮动", risk="aggressive", market="A", family="rotation", desc="动量排名行业，周度调仓"),
    StrategyTemplate(id="t4", name="XGBoost 多因子", risk="balanced", market="A", family="ml", desc="机器学习分类，预测 5 日收益率方向"),
]

_FEED = [
    FeedEvent(time="09:31", agent="Strategy", event="生成策略 双均线趋势_v2", tone="green"),
    FeedEvent(time="09:28", agent="Backtest", event="MA趋势 回测完成，Sharpe 1.34", tone="blue"),
    FeedEvent(time="09:25", agent="Risk", event="通过风控检查，无违规", tone="green"),
    FeedEvent(time="09:20", agent="Research", event="发现新能源板块动量信号", tone="yellow"),
]

_MATRIX = [
    StrategyMatrixRow(id="s1", name="MA趋势", family="trend", annualReturn=0.185, maxDd=-0.123, sharpe=1.34, status="live", oosScore=78, sparkline=[1.0, 1.02, 1.05, 1.08, 1.12, 1.15, 1.18], lastUpdate="2 min ago"),
    StrategyMatrixRow(id="s2", name="价值选股", family="value", annualReturn=0.221, maxDd=-0.098, sharpe=1.56, status="paper", oosScore=85, sparkline=[1.0, 1.03, 1.06, 1.09, 1.13, 1.17, 1.20], lastUpdate="5 min ago"),
    StrategyMatrixRow(id="s3", name="行业轮动", family="rotation", annualReturn=0.152, maxDd=-0.156, sharpe=1.12, status="live", oosScore=72, sparkline=[1.0, 1.01, 1.03, 1.02, 1.05, 1.08, 1.10], lastUpdate="10 min ago"),
    StrategyMatrixRow(id="s4", name="XGBoost", family="ml", annualReturn=0.284, maxDd=-0.189, sharpe=1.42, status="backtest", oosScore=91, sparkline=[1.0, 1.04, 1.08, 1.12, 1.16, 1.20, 1.24], lastUpdate="15 min ago"),
    StrategyMatrixRow(id="s5", name="均值回归", family="mean_reversion", annualReturn=0.095, maxDd=-0.067, sharpe=0.98, status="draft", oosScore=0, sparkline=[1.0, 0.99, 1.01, 1.02, 1.01, 1.03, 1.02], lastUpdate="—"),
]

_PIPELINE_BOARD = [
    PipelineLane(
        lane="研究中",
        tone="blue",
        tickets=[
            PipelineTicket(id="t1", title="新能源动量策略", desc="基于 AKShare 板块数据", progress=30, metrics=[{"label": "因子数", "value": "12"}, {"label": "样本期", "value": "3年"}], tag="research"),
        ],
    ),
    PipelineLane(
        lane="回测中",
        tone="green",
        tickets=[
            PipelineTicket(id="t2", title="价值选股_v2", desc="加入 PB 因子过滤", progress=70, metrics=[{"label": "IS收益", "value": "22.1%"}, {"label": "OOS", "value": "85"}], tag="backtest"),
            PipelineTicket(id="t3", title="XGBoost调参", desc="网格搜索最优参数", progress=50, metrics=[{"label": "参数组合", "value": "128"}, {"label": "已运行", "value": "64"}], tag="backtest"),
        ],
    ),
    PipelineLane(
        lane="模拟盘",
        tone="yellow",
        tickets=[
            PipelineTicket(id="t4", title="MA趋势_v3", desc="加入止损逻辑", progress=90, metrics=[{"label": "模拟收益", "value": "+8.5%"}, {"label": "最大回撤", "value": "-5.2%"}], tag="paper"),
        ],
    ),
    PipelineLane(
        lane="实盘",
        tone="red",
        tickets=[
            PipelineTicket(id="t5", title="MA趋势", desc="双均线策略实盘运行", progress=100, metrics=[{"label": "实盘收益", "value": "+18.5%"}, {"label": "夏普", "value": "1.34"}], tag="live"),
            PipelineTicket(id="t6", title="行业轮动", desc="行业动量轮动策略", progress=100, metrics=[{"label": "实盘收益", "value": "+15.2%"}, {"label": "夏普", "value": "1.12"}], tag="live"),
        ],
    ),
]


@router.get("/overview", response_model=StrategyScreen)
async def get_strategy_overview(db: AsyncSession = Depends(get_db)) -> StrategyScreen:
    """Return the complete Strategy Factory screen data."""
    return StrategyScreen(
        pipelineStatus=_PIPELINE_STATUS,
        templates=_TEMPLATES,
        nlPrompt="",
        feed=_FEED,
        matrix=_MATRIX,
        pipelineBoard=_PIPELINE_BOARD,
    )


@router.get("/templates", response_model=list[StrategyTemplate])
async def get_templates() -> list[StrategyTemplate]:
    """Return strategy templates."""
    return _TEMPLATES


@router.post("/tasks")
async def create_strategy_task(payload: StrategyTaskCreate) -> dict[str, str]:
    """Create a natural language strategy generation task."""
    return {"task_id": "task-001", "status": "queued"}


@router.post("/")
async def create_strategy(payload: StrategyCreate) -> dict[str, str]:
    """Create a strategy draft."""
    return {"strategy_id": "s-new", "status": "draft"}
