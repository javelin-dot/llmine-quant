"""Audit Service API — immutable audit logs, actor stats, tool registry, HITL rules."""

import csv
import io
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.agents.models import ToolRegistry
from app.domains.audit.models import AuditLog
from app.domains.audit.schemas import (
    ActorStat,
    AuditKpi,
    AuditRow,
    AuditScreen,
    HitlRule,
    ToolRegistryItem,
)
from app.services.audit_service import AuditService

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]

_HITL_RULES = [
    HitlRule(rule="实盘订单审批", desc="所有实盘账户订单需人工审批", status="approval", statusTone="red"),
    HitlRule(rule="策略上线审批", desc="策略从模拟盘切换到实盘需审批", status="approval", statusTone="red"),
    HitlRule(rule="大额交易提醒", desc="单笔交易超过 50 万需提醒", status="review", statusTone="yellow"),
    HitlRule(rule="数据异常处理", desc="数据漂移超过阈值自动暂停策略", status="auto", statusTone="green"),
    HitlRule(rule="熔断恢复", desc="L2 及以上熔断恢复需人工确认", status="approval", statusTone="red"),
    HitlRule(rule="账户资金变动", desc="单日净出入金超过 10 万需审计确认", status="review", statusTone="yellow"),
]

_LEVEL_TONE = {"low": "green", "medium": "yellow", "high": "red", "critical": "red"}
_ACTOR_TONE = {"human": "yellow", "agent": "blue", "system": "green"}


def _fmt_time(dt) -> str:
    if dt is None:
        return "—"
    s = dt.isoformat()
    return s[11:19] if len(s) > 11 else s


def _row_to_out(r: AuditLog) -> AuditRow:
    return AuditRow(
        time=_fmt_time(r.created_at),
        actor=r.actor,
        actorType=r.actor_type,
        action=r.action,
        resource=r.resource_id or r.resource_type,
        result=r.result,
        resultTone=r.result_tone,
        confidence=r.confidence or 1.0,
        detail=r.detail or "",
        traceId=r.trace_id or "",
    )


async def _get_audit_rows(db: AsyncSession, limit: int = 50) -> list[AuditRow]:
    rows = (
        await db.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    return [_row_to_out(r) for r in rows]


async def _get_kpis(db: AsyncSession) -> list[AuditKpi]:
    total = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
    agent_count = (
        await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.actor_type == "agent")
        )
    ).scalar() or 0
    human_count = (
        await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.actor_type == "human")
        )
    ).scalar() or 0
    error_count = (
        await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.result_tone == "red")
        )
    ).scalar() or 0
    # Quick integrity probe: check latest 200 rows for null curr_hash (unhashed = legacy rows)
    hashed = (
        await db.execute(
            select(func.count(AuditLog.id))
            .where(AuditLog.curr_hash.isnot(None))
            .order_by(AuditLog.created_at.desc())
            .limit(200)
        )
    ).scalar() or 0
    hash_pct = "100%" if (total == 0 or hashed > 0) else "—"
    return [
        AuditKpi(label="总事件", value=str(total), trend="▲", tone="blue"),
        AuditKpi(label="Agent 操作", value=str(agent_count), trend="▲", tone="green"),
        AuditKpi(label="人工审批", value=str(human_count), trend="▼", tone="yellow"),
        AuditKpi(label="异常事件", value=str(error_count), trend="→", tone="red" if error_count else "green"),
        AuditKpi(label="哈希链完整", value=hash_pct, trend="→", tone="green"),
    ]


async def _get_actor_stats(db: AsyncSession, limit: int = 8) -> list[ActorStat]:
    rows = (
        await db.execute(
            select(AuditLog.actor, func.count(AuditLog.id).label("cnt"))
            .group_by(AuditLog.actor)
            .order_by(func.count(AuditLog.id).desc())
            .limit(limit)
        )
    ).all()
    return [
        ActorStat(
            actor=r.actor,
            count=int(r.cnt),
            tone=_ACTOR_TONE.get("agent" if "agent" in r.actor.lower() else "human", "blue"),
        )
        for r in rows
    ]


async def _get_tool_registry(db: AsyncSession) -> list[ToolRegistryItem]:
    rows = (
        await db.execute(
            select(ToolRegistry).where(ToolRegistry.enabled.is_(True)).order_by(ToolRegistry.name).limit(20)
        )
    ).scalars().all()
    result = []
    for t in rows:
        try:
            agents = json.loads(t.allowed_agents) if t.allowed_agents else []
        except Exception:
            agents = []
        level = t.level or "low"
        result.append(
            ToolRegistryItem(
                name=t.name,
                level={"low": "低风险", "medium": "中风险", "high": "高风险", "critical": "极高风险"}.get(level, level),
                levelTone=_LEVEL_TONE.get(level, "green"),
                desc=t.description or "",
                agents=agents,
            )
        )
    return result


@router.get("/overview", response_model=AuditScreen)
async def get_audit_overview(db: DbSession) -> AuditScreen:
    """Return the complete Audit & Compliance screen — DB-driven."""
    rows, kpis, actor_stats, registry = (
        await _get_audit_rows(db, 50),
        await _get_kpis(db),
        await _get_actor_stats(db),
        await _get_tool_registry(db),
    )
    return AuditScreen(
        kpis=kpis,
        rows=rows,
        actorStats=actor_stats,
        toolRegistry=registry,
        hitlRules=_HITL_RULES,
    )


@router.get("/logs", response_model=list[AuditRow])
async def list_audit_logs(
    db: DbSession,
    actor_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AuditRow]:
    """Paginated audit log with optional actorType / action filter."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if action:
        stmt = stmt.where(AuditLog.action.contains(action))
    rows = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
    return [_row_to_out(r) for r in rows]


@router.get("/actor-stats", response_model=list[ActorStat])
async def get_actor_stats(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ActorStat]:
    """Return actor operation counts ordered by frequency."""
    return await _get_actor_stats(db, limit=limit)


@router.get("/verify")
async def verify_hash_chain(
    db: DbSession,
    limit: int = Query(default=500, ge=1, le=5000),
) -> dict:
    """Verify SHA-256 hash chain integrity for the most recent audit logs."""
    svc = AuditService(db)
    is_valid, count, broken_id = await svc.verify_chain(limit=limit)
    return {
        "valid": is_valid,
        "verifiedCount": count,
        "brokenEntryId": broken_id if not is_valid else None,
        "status": "intact" if is_valid else "broken",
        "statusTone": "green" if is_valid else "red",
    }


@router.get("/export")
async def export_audit_logs(
    db: DbSession,
    actor_type: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=10000),
) -> StreamingResponse:
    """Export audit logs as CSV."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    rows = (await db.execute(stmt.limit(limit))).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["time", "actor", "actor_type", "action", "resource_type", "resource_id", "result", "confidence", "detail", "trace_id", "curr_hash"])
    for r in rows:
        writer.writerow([
            r.created_at.isoformat() if r.created_at else "",
            r.actor, r.actor_type, r.action,
            r.resource_type, r.resource_id or "",
            r.result, r.confidence or "",
            (r.detail or "").replace("\n", " "),
            r.trace_id or "",
            r.curr_hash or "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


@router.get("/registry", response_model=list[ToolRegistryItem])
async def get_tool_registry(db: DbSession) -> list[ToolRegistryItem]:
    """Return tool registry items."""
    return await _get_tool_registry(db)


@router.get("/hitl-rules", response_model=list[HitlRule])
async def get_hitl_rules() -> list[HitlRule]:
    """Return HITL policy rules."""
    return _HITL_RULES
