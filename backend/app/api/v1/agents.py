"""Agent Orchestrator API — agent registry, tasks, messages, tool registry."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.agents.models import AgentMessage, AgentRegistry, AgentTask, ToolRegistry
from app.domains.agents.schemas import (
    AgentMessageCreate,
    AgentMessageOut,
    AgentOut,
    AgentOverview,
    AgentTaskCreate,
    AgentTaskOut,
    ToolOut,
)
from app.services.agent_orchestrator import AgentOrchestrator

router = APIRouter()


def _agent_out(agent: AgentRegistry) -> AgentOut:
    return AgentOut(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        status=agent.status,
        statusTone="green" if agent.status == "active" else "gray" if agent.status == "idle" else "yellow",
        currentTask=agent.current_task or "—",
        metric=agent.metric or "—",
        heartbeat=agent.heartbeat_at or "—",
    )


def _task_out(task: AgentTask, agent_name: str = "") -> AgentTaskOut:
    tones = {
        "pending": "yellow",
        "running": "blue",
        "succeeded": "green",
        "failed": "red",
    }
    return AgentTaskOut(
        id=task.id,
        agentId=task.agent_id,
        agentName=agent_name,
        taskType=task.task_type,
        priority=task.priority,
        status=task.status,
        statusTone=tones.get(task.status, "gray"),
        createdAt=task.created_at.isoformat() if task.created_at else "",
        startedAt=task.started_at,
        completedAt=task.completed_at,
        result=task.result_json,
    )


def _message_out(msg: AgentMessage) -> AgentMessageOut:
    return AgentMessageOut(
        id=msg.id,
        fromAgent=msg.from_agent,
        toAgent=msg.to_agent,
        msgType=msg.msg_type,
        topic=msg.topic,
        payload=msg.payload_json,
        correlationId=msg.correlation_id,
        createdAt=msg.created_at.isoformat() if msg.created_at else "",
    )


def _tool_out(tool: ToolRegistry) -> ToolOut:
    try:
        allowed = json.loads(tool.allowed_agents) if tool.allowed_agents else []
    except Exception:
        allowed = []
    level_map = {"low": ("低风险", "green"), "medium": ("中风险", "yellow"), "high": ("高风险", "red")}
    label, tone = level_map.get(tool.level, ("未知", "gray"))
    return ToolOut(
        id=tool.id,
        name=tool.name,
        level=label,
        levelTone=tone,
        description=tool.description or "",
        allowedAgents=allowed,
        enabled=tool.enabled,
    )


@router.get("/overview", response_model=AgentOverview)
async def get_agent_overview(db: AsyncSession = Depends(get_db)) -> AgentOverview:
    """Return the complete Agent Orchestrator overview (DB-driven)."""
    agents_result = await db.execute(select(AgentRegistry).order_by(AgentRegistry.name))
    agents = [_agent_out(a) for a in agents_result.scalars().all()]

    tasks_result = await db.execute(
        select(AgentTask).order_by(desc(AgentTask.created_at)).limit(20)
    )
    tasks = [_task_out(t) for t in tasks_result.scalars().all()]

    messages_result = await db.execute(
        select(AgentMessage).order_by(desc(AgentMessage.created_at)).limit(20)
    )
    messages = [_message_out(m) for m in messages_result.scalars().all()]

    tools_result = await db.execute(select(ToolRegistry).order_by(ToolRegistry.name))
    tools = [_tool_out(t) for t in tools_result.scalars().all()]

    return AgentOverview(agents=agents, tasks=tasks, messages=messages, tools=tools)


@router.post("/tasks", response_model=AgentTaskOut)
async def create_agent_task(
    payload: AgentTaskCreate,
    db: AsyncSession = Depends(get_db),
) -> AgentTaskOut:
    """Create a new agent task and dispatch it."""
    orchestrator = AgentOrchestrator(db)
    task = await orchestrator.dispatch(
        agent_role=payload.agent_role,
        task_type=payload.task_type,
        payload=payload.payload or {},
        priority=payload.priority,
        correlation_id=payload.correlation_id,
    )
    return _task_out(task)


@router.get("/tasks/{task_id}", response_model=AgentTaskOut)
async def get_agent_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> AgentTaskOut:
    """Get a single agent task."""
    task = await db.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_out(task)


@router.post("/messages", response_model=AgentMessageOut)
async def send_agent_message(
    payload: AgentMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> AgentMessageOut:
    """Send an inter-agent message."""
    orchestrator = AgentOrchestrator(db)
    msg = await orchestrator.send_message(
        from_agent=payload.from_agent,
        to_agent=payload.to_agent,
        topic=payload.topic,
        payload=payload.payload,
        correlation_id=payload.correlation_id,
        msg_type=payload.msg_type,
    )
    return _message_out(msg)


@router.get("/messages", response_model=list[AgentMessageOut])
async def get_agent_messages(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> list[AgentMessageOut]:
    """List recent inter-agent messages."""
    rows = await db.execute(
        select(AgentMessage).order_by(desc(AgentMessage.created_at)).limit(limit)
    )
    return [_message_out(m) for m in rows.scalars().all()]
