"""Strategy Service API — strategies, versions, tasks, pipeline."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_db
from app.domains.agents.models import AgentMessage
from app.domains.strategy.models import (
    PipelineEvent,
    Strategy,
    StrategyTask,
    StrategyTemplate as StrategyTemplateModel,
)
from app.domains.strategy.schemas import (
    FeedEvent,
    PipelineEventOut,
    PipelineLane,
    PipelineStatus,
    PipelineTicket,
    StrategyCreate,
    StrategyMatrixRow,
    StrategyScreen,
    StrategyTaskCreate,
    StrategyTaskOut,
    StrategyTemplate,
    StrategyTransition,
)
from app.services.strategy_generation import StrategyGenerationService

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────

def _task_out(task: StrategyTask) -> StrategyTaskOut:
    tones = {
        "queued": "yellow",
        "running": "blue",
        "succeeded": "green",
        "failed": "red",
        "canceled": "gray",
    }
    progress = {"queued": 0, "running": 50, "succeeded": 100, "failed": 100, "canceled": 0}.get(
        task.status, 0
    )
    stage = {"queued": "queued", "running": "running", "succeeded": "done", "failed": "failed", "canceled": "canceled"}.get(
        task.status
    )
    return StrategyTaskOut(
        id=task.id,
        prompt=task.prompt,
        market=task.market,
        risk_profile=task.risk_profile,
        status=task.status,
        statusTone=tones.get(task.status, "gray"),
        progress=progress,
        stage=stage,
        strategy_id=task.strategy_id,
        agent_task_id=task.agent_task_id,
        result=task.result,
        error=task.error,
        created_at=task.created_at.isoformat() if task.created_at else "",
        updated_at=task.updated_at.isoformat() if task.updated_at else "",
    )


async def _run_pipeline_bg(task_id: str) -> None:
    """Background runner with its own session."""
    async with AsyncSessionLocal() as db:
        service = StrategyGenerationService(db)
        await service.run_pipeline(task_id)


# ── routes ────────────────────────────────────────────────────────────

@router.get("/overview", response_model=StrategyScreen)
async def get_strategy_overview(db: AsyncSession = Depends(get_db)) -> StrategyScreen:
    """Return the complete Strategy Factory screen data (DB-driven)."""
    # Pipeline status counts
    counts: dict[str, int] = {s: 0 for s in ["research", "backtest", "paper", "live", "paused"]}
    rows = await db.execute(select(Strategy.status, func.count(Strategy.id)).group_by(Strategy.status))
    for status, cnt in rows.all():
        if status in counts:
            counts[status] = cnt
    pipeline_status = [
        PipelineStatus(stage="research", count=counts["research"], tone="blue"),
        PipelineStatus(stage="backtest", count=counts["backtest"], tone="green"),
        PipelineStatus(stage="paper", count=counts["paper"], tone="yellow"),
        PipelineStatus(stage="live", count=counts["live"], tone="red"),
        PipelineStatus(stage="paused", count=counts["paused"], tone="purple"),
    ]

    # Templates
    tmpl_rows = await db.execute(
        select(StrategyTemplateModel).order_by(StrategyTemplateModel.created_at.desc()).limit(10)
    )
    templates = [
        StrategyTemplate(
            id=t.id,
            name=t.name,
            risk=t.risk_level,
            market=t.market,
            family=t.family,
            desc=t.description or "",
        )
        for t in tmpl_rows.scalars().all()
    ]

    # Feed — last 20 agent messages
    feed_rows = await db.execute(
        select(AgentMessage).order_by(desc(AgentMessage.created_at)).limit(20)
    )
    feed: list[FeedEvent] = []
    for m in feed_rows.scalars().all():
        try:
            payload = json.loads(m.payload_json) if m.payload_json else {}
        except Exception:
            payload = {}
        evt = payload.get("event", m.topic)
        tone = "green" if any(k in evt for k in ("pass", "succeeded", "published")) else "blue"
        feed.append(
            FeedEvent(
                time=m.created_at.isoformat()[-8:] if m.created_at else "",
                agent=m.from_agent,
                event=evt,
                tone=tone,
            )
        )

    # Matrix — last 20 strategies
    strat_rows = await db.execute(select(Strategy).order_by(Strategy.updated_at.desc()).limit(20))
    strategies = strat_rows.scalars().all()
    matrix = [
        StrategyMatrixRow(
            id=s.id,
            name=s.name,
            family=s.family,
            annualReturn=s.annual_return or 0.0,
            maxDd=s.max_dd or 0.0,
            sharpe=s.sharpe or 0.0,
            status=s.status,
            oosScore=s.oos_score or 0,
            sparkline=[1.0 + (i * 0.02) for i in range(7)],
            lastUpdate=s.updated_at.isoformat() if s.updated_at else "—",
        )
        for s in strategies
    ]

    # Pipeline board — strategies grouped by status
    lanes: dict[str, PipelineLane] = {
        "draft": PipelineLane(lane="草稿", tone="gray", tickets=[]),
        "research": PipelineLane(lane="研究中", tone="blue", tickets=[]),
        "backtest": PipelineLane(lane="回测中", tone="green", tickets=[]),
        "paper": PipelineLane(lane="模拟盘", tone="yellow", tickets=[]),
        "live": PipelineLane(lane="实盘", tone="red", tickets=[]),
        "paused": PipelineLane(lane="暂停", tone="purple", tickets=[]),
    }
    for s in strategies:
        if s.status in lanes:
            lanes[s.status].tickets.append(
                PipelineTicket(
                    id=s.id,
                    title=s.name,
                    desc=s.description or "",
                    progress=0,
                    metrics=[{"label": "夏普", "value": str(s.sharpe or "—")}],
                    tag=s.status,
                )
            )
    pipeline_board = [lanes[k] for k in lanes if lanes[k].tickets]

    return StrategyScreen(
        pipelineStatus=pipeline_status,
        templates=templates,
        nlPrompt="",
        feed=feed,
        matrix=matrix,
        pipelineBoard=pipeline_board,
    )


@router.get("/templates", response_model=list[StrategyTemplate])
async def get_templates(db: AsyncSession = Depends(get_db)) -> list[StrategyTemplate]:
    """Return strategy templates."""
    rows = await db.execute(
        select(StrategyTemplateModel).order_by(StrategyTemplateModel.created_at.desc()).limit(20)
    )
    return [
        StrategyTemplate(
            id=t.id,
            name=t.name,
            risk=t.risk_level,
            market=t.market,
            family=t.family,
            desc=t.description or "",
        )
        for t in rows.scalars().all()
    ]


@router.post("/tasks", response_model=StrategyTaskOut)
async def create_strategy_task(
    payload: StrategyTaskCreate,
    db: AsyncSession = Depends(get_db),
) -> StrategyTaskOut:
    """Create a generation task and kick off the pipeline in background."""
    service = StrategyGenerationService(db)
    task = await service.create_task(
        prompt=payload.prompt,
        market=payload.market,
        risk_profile=payload.risk_profile,
    )
    asyncio.create_task(_run_pipeline_bg(task.id))
    return _task_out(task)


@router.get("/tasks/{task_id}", response_model=StrategyTaskOut)
async def get_strategy_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> StrategyTaskOut:
    """Query task status and progress."""
    task = await db.get(StrategyTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_out(task)


@router.get("/feed", response_model=list[FeedEvent])
async def get_strategy_feed(db: AsyncSession = Depends(get_db)) -> list[FeedEvent]:
    """Return recent agent activity feed."""
    rows = await db.execute(
        select(AgentMessage).order_by(desc(AgentMessage.created_at)).limit(20)
    )
    feed: list[FeedEvent] = []
    for m in rows.scalars().all():
        try:
            payload = json.loads(m.payload_json) if m.payload_json else {}
        except Exception:
            payload = {}
        evt = payload.get("event", m.topic)
        tone = "green" if any(k in evt for k in ("pass", "succeeded", "published")) else "blue"
        feed.append(
            FeedEvent(
                time=m.created_at.isoformat()[-8:] if m.created_at else "",
                agent=m.from_agent,
                event=evt,
                tone=tone,
            )
        )
    return feed


@router.post("/{strategy_id}/transition")
async def transition_strategy(
    strategy_id: str,
    payload: StrategyTransition,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Transition a strategy to a new pipeline stage."""
    strategy = await db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    old_status = strategy.status
    strategy.status = payload.target
    await db.commit()
    await db.refresh(strategy)

    event = PipelineEvent(
        strategy_id=strategy_id,
        stage=payload.target,
        event=f"transition.{old_status}_to_{payload.target}",
        progress=0,
        detail=payload.note or "",
    )
    db.add(event)
    await db.commit()
    return {"strategy_id": strategy_id, "status": strategy.status}


@router.get("/{strategy_id}/events", response_model=list[PipelineEventOut])
async def get_strategy_events(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[PipelineEventOut]:
    """Return pipeline events for a strategy."""
    rows = await db.execute(
        select(PipelineEvent)
        .where(PipelineEvent.strategy_id == strategy_id)
        .order_by(PipelineEvent.created_at.asc())
    )
    return [
        PipelineEventOut(
            id=e.id,
            strategy_id=e.strategy_id,
            stage=e.stage,
            event=e.event,
            progress=e.progress,
            detail=e.detail,
            created_at=e.created_at.isoformat() if e.created_at else "",
        )
        for e in rows.scalars().all()
    ]


@router.post("/", response_model=dict[str, str])
async def create_strategy(
    payload: StrategyCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Create a strategy draft."""
    strategy = Strategy(
        name=payload.name,
        family=payload.family,
        type=payload.type,
        description=payload.description,
        risk_profile=payload.risk_profile,
        market=payload.market,
        universe=payload.universe,
        frequency=payload.frequency,
        status="draft",
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    return {"strategy_id": strategy.id, "status": strategy.status}
