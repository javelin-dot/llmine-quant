"""Strategy Service API — strategies, versions, tasks, pipeline."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tracing import get_actor_id, get_trace_id
from app.db.base_class import now_utc
from app.db.session import AsyncSessionLocal, get_db
from app.domains.agents.models import AgentMessage
from app.domains.strategy.models import (
    PipelineEvent,
    Strategy,
    StrategyTask,
    StrategyTemplate as StrategyTemplateModel,
    StrategyVersion,
)
from app.domains.strategy.schemas import (
    FeedEvent,
    PipelineEventOut,
    PipelineLane,
    PipelineStatus,
    PipelineTicket,
    StrategyCreate,
    StrategyDetail,
    StrategyListItem,
    StrategyListResponse,
    StrategyMatrixRow,
    StrategyScreen,
    StrategyTaskCreate,
    StrategyTaskOut,
    StrategyTemplate,
    StrategyTransition,
    StrategyUpdate,
    StrategyVersionOut,
)
from app.services.audit_service import AuditService
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
        riskProfile=task.risk_profile,
        status=task.status,
        statusTone=tones.get(task.status, "gray"),
        progress=progress,
        stage=stage,
        strategyId=task.strategy_id,
        agentTaskId=task.agent_task_id,
        result=task.result,
        error=task.error,
        createdAt=task.created_at.isoformat() if task.created_at else "",
        updatedAt=task.updated_at.isoformat() if task.updated_at else "",
    )


def _list_item(s: Strategy) -> StrategyListItem:
    return StrategyListItem(
        id=s.id,
        name=s.name,
        family=s.family,
        type=s.type,
        status=s.status,
        riskProfile=s.risk_profile,
        market=s.market,
        sharpe=s.sharpe,
        maxDd=s.max_dd,
        annualReturn=s.annual_return,
        oosScore=s.oos_score,
        updatedAt=s.updated_at.isoformat() if s.updated_at else "",
    )


def _version_out(v: StrategyVersion) -> StrategyVersionOut:
    return StrategyVersionOut(
        id=v.id,
        version=v.version,
        status=v.status,
        codeText=v.code_text,
        paramsSchema=v.params_schema,
        riskRules=v.risk_rules,
        createdAt=v.created_at.isoformat() if v.created_at else "",
    )


def _event_out(e: PipelineEvent) -> PipelineEventOut:
    return PipelineEventOut(
        id=e.id,
        strategyId=e.strategy_id,
        stage=e.stage,
        event=e.event,
        progress=e.progress,
        detail=e.detail,
        createdAt=e.created_at.isoformat() if e.created_at else "",
    )


async def _run_pipeline_bg(task_id: str) -> None:
    """Background runner with its own session."""
    async with AsyncSessionLocal() as db:
        service = StrategyGenerationService(db)
        await service.run_pipeline(task_id)


async def _resolve_live_strategy(
    db: AsyncSession, strategy_or_task_id: str
) -> tuple[Strategy, str] | None:
    """Return (Strategy, canonical_strategy_id) or None.

    Supports lookup by real strategy id, or by ``StrategyTask.id`` when the client
    mistakenly uses the generation task UUID (same shape as strategy ids).
    """
    strategy = await db.get(Strategy, strategy_or_task_id)
    if strategy is not None:
        if strategy.deleted_at is not None:
            return None
        return (strategy, strategy.id)
    task = await db.get(StrategyTask, strategy_or_task_id)
    if task is not None and task.strategy_id:
        strategy = await db.get(Strategy, task.strategy_id)
        if strategy is not None and strategy.deleted_at is None:
            return (strategy, strategy.id)

    version = await db.get(StrategyVersion, strategy_or_task_id)
    if version is not None:
        strategy = await db.get(Strategy, version.strategy_id)
        if strategy is not None and strategy.deleted_at is None:
            return (strategy, strategy.id)

    return None


# ── routes ────────────────────────────────────────────────────────────

@router.get("/overview", response_model=StrategyScreen)
async def get_strategy_overview(db: AsyncSession = Depends(get_db)) -> StrategyScreen:
    """Return the complete Strategy Factory screen data (DB-driven)."""
    # Pipeline status counts (exclude soft-deleted rows)
    counts: dict[str, int] = {s: 0 for s in ["research", "backtest", "paper", "live", "paused"]}
    rows = await db.execute(
        select(Strategy.status, func.count(Strategy.id))
        .where(Strategy.deleted_at.is_(None))
        .group_by(Strategy.status)
    )
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

    # Matrix — last 20 strategies (exclude soft-deleted)
    strat_rows = await db.execute(
        select(Strategy)
        .where(Strategy.deleted_at.is_(None))
        .order_by(Strategy.updated_at.desc())
        .limit(20)
    )
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
        task_row = await db.execute(
            select(StrategyTask)
            .where(StrategyTask.strategy_id == task_id)
            .order_by(StrategyTask.created_at.desc())
            .limit(1)
        )
        task = task_row.scalar_one_or_none()
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


@router.get("", response_model=StrategyListResponse)
@router.get("/", response_model=StrategyListResponse)
async def list_strategies(
    status: str | None = Query(default=None, description="Filter by status"),
    family: str | None = Query(default=None, description="Filter by strategy family"),
    market: str | None = Query(default=None, description="Filter by market"),
    q: str | None = Query(default=None, description="Free-text search on name/description"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> StrategyListResponse:
    """List strategies with optional filters and pagination."""
    base = select(Strategy).where(Strategy.deleted_at.is_(None))
    if status:
        base = base.where(Strategy.status == status)
    if family:
        base = base.where(Strategy.family == family)
    if market:
        base = base.where(Strategy.market == market)
    if q:
        like = f"%{q}%"
        base = base.where(or_(Strategy.name.ilike(like), Strategy.description.ilike(like)))

    total_row = await db.execute(
        select(func.count())
        .select_from(base.subquery())
    )
    total = int(total_row.scalar() or 0)

    rows = await db.execute(
        base.order_by(Strategy.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_list_item(s) for s in rows.scalars().all()]
    return StrategyListResponse(total=total, items=items)


@router.post("/{strategy_id}/transition")
async def transition_strategy(
    strategy_id: str,
    payload: StrategyTransition,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Transition a strategy to a new pipeline stage."""
    strategy = await db.get(Strategy, strategy_id)
    if strategy is None or strategy.deleted_at is not None:
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
    return [_event_out(e) for e in rows.scalars().all()]


@router.get("/{strategy_id}", response_model=StrategyDetail)
async def get_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
) -> StrategyDetail:
    """Return strategy detail with versions and recent pipeline events."""
    resolved = await _resolve_live_strategy(db, strategy_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strategy, resolved_id = resolved

    version_rows = await db.execute(
        select(StrategyVersion)
        .where(StrategyVersion.strategy_id == resolved_id)
        .order_by(StrategyVersion.created_at.desc())
    )
    versions = [_version_out(v) for v in version_rows.scalars().all()]

    event_rows = await db.execute(
        select(PipelineEvent)
        .where(PipelineEvent.strategy_id == resolved_id)
        .order_by(PipelineEvent.created_at.desc())
        .limit(20)
    )
    events = [_event_out(e) for e in event_rows.scalars().all()]

    return StrategyDetail(
        id=strategy.id,
        name=strategy.name,
        family=strategy.family,
        type=strategy.type,
        status=strategy.status,
        description=strategy.description,
        riskProfile=strategy.risk_profile,
        market=strategy.market,
        universe=strategy.universe,
        frequency=strategy.frequency,
        ownerId=strategy.owner_id,
        sharpe=strategy.sharpe,
        maxDd=strategy.max_dd,
        annualReturn=strategy.annual_return,
        oosScore=strategy.oos_score,
        createdAt=strategy.created_at.isoformat() if strategy.created_at else "",
        updatedAt=strategy.updated_at.isoformat() if strategy.updated_at else "",
        versions=versions,
        recentEvents=events,
    )


@router.put("/{strategy_id}", response_model=StrategyDetail)
@router.patch("/{strategy_id}", response_model=StrategyDetail)
async def update_strategy(
    strategy_id: str,
    payload: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
) -> StrategyDetail:
    """Partial update — only provided fields are modified."""
    strategy = await db.get(Strategy, strategy_id)
    if strategy is None or strategy.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    data = payload.model_dump(exclude_unset=True, by_alias=False)
    old_status = strategy.status
    for field, value in data.items():
        setattr(strategy, field, value)
    strategy.updated_at = now_utc()
    strategy.updated_by = get_actor_id() or strategy.updated_by
    await db.commit()
    await db.refresh(strategy)

    # If status changed, log a pipeline event for traceability.
    if "status" in data and data["status"] != old_status:
        db.add(
            PipelineEvent(
                strategy_id=strategy_id,
                stage=str(data["status"]),
                event=f"transition.{old_status}_to_{data['status']}",
                progress=0,
                detail="manual update",
                trace_id=get_trace_id(),
            )
        )
        await db.commit()

    await AuditService(db).log(
        action="strategy.updated",
        resource_type="strategy",
        resource_id=strategy_id,
        detail=json.dumps(data, ensure_ascii=False)[:512],
    )

    return await get_strategy(strategy_id, db)


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Soft-delete a strategy (sets `deleted_at`)."""
    strategy = await db.get(Strategy, strategy_id)
    if strategy is None or strategy.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strategy.deleted_at = now_utc()
    strategy.updated_at = now_utc()
    strategy.updated_by = get_actor_id() or strategy.updated_by
    await db.commit()

    await AuditService(db).log(
        action="strategy.deleted",
        resource_type="strategy",
        resource_id=strategy_id,
        result_tone="yellow",
        detail=f"name={strategy.name}",
    )

    return {"strategy_id": strategy_id, "deleted": "true"}


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
        owner_id=get_actor_id() or "system",
        trace_id=get_trace_id(),
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    return {"strategy_id": strategy.id, "status": strategy.status}
