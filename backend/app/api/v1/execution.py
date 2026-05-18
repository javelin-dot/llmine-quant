"""Execution Service API — approvals, order book, pre-trade checks, execution metrics."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager as ws_manager
from app.db.session import get_db
from app.domains.execution.models import AgentTrace, Approval, Order
from app.domains.execution.schemas import (
    AgentTraceOut,
    ApprovalOut,
    ExecutionMetrics,
    ExecutionScreen,
    ExecutionSummary,
    FillRateMetric,
    OrderBookRow,
    PreTradeCheckOut,
    SlippageMetric,
)
from app.services.audit_service import AuditService

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]

_TYPE_TONE = {
    "live": "red", "paper": "green", "reduce": "yellow", "add": "blue",
    "rotate": "purple", "hedge": "purple", "pause": "gray",
}
_URGENCY_TONE = {"high": "red", "medium": "yellow", "low": "green"}
_STATUS_TONE = {
    "filled": "green", "partial": "yellow", "working": "blue",
    "rejected": "red", "canceled": "gray",
}

# ── Derived execution analytics (fills, rejects) populated when trade history aggregates exist ──

_PRE_TRADE_CHECKS: list[PreTradeCheckOut] = []

_METRICS = ExecutionMetrics(
    slippage=SlippageMetric(
        avgBps=0.0,
        p50Bps=0.0,
        p95Bps=0.0,
        buckets=[],
    ),
    fillRate=FillRateMetric(total=0, filled=0, partial=0, rejected=0, canceled=0),
    rejectReasons=[],
)


def _fmt_time(dt) -> str:
    if dt is None:
        return "—"
    s = dt.isoformat()
    return s[11:19] if len(s) > 11 else s


def _approval_to_out(a: Approval) -> ApprovalOut:
    return ApprovalOut(
        id=a.id,
        type=a.type,
        typeTone=_TYPE_TONE.get(a.type, "blue"),
        symbol=a.symbol,
        name=a.name,
        side=a.side,
        qty=a.qty,
        notional=a.notional,
        notionalPct=a.notional_pct,
        limitPrice=a.limit_price or "—",
        stopLoss=a.stop_loss or "—",
        confidence=a.confidence,
        riskGrade=a.risk_grade or "—",
        reason=a.reason or "",
        impact=a.impact or "",
        expireSec=a.expire_sec,
        urgency=a.urgency,
        urgencyTone=_URGENCY_TONE.get(a.urgency, "yellow"),
        strategy=a.strategy_id or "—",
    )


async def _get_approvals(db: AsyncSession, status: str = "pending") -> list[ApprovalOut]:
    rows = (
        await db.execute(
            select(Approval)
            .where(Approval.status == status)
            .order_by(Approval.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [_approval_to_out(a) for a in rows]


async def _get_order_book(db: AsyncSession) -> list[OrderBookRow]:
    rows = (
        await db.execute(
            select(Order).order_by(Order.created_at.desc()).limit(20)
        )
    ).scalars().all()
    return [
        OrderBookRow(
            time=_fmt_time(r.created_at),
            symbol=r.symbol,
            side=r.side,
            qty=r.qty,
            limit=r.limit_price,
            filled=r.filled_qty,
            status=r.status,
            statusTone=_STATUS_TONE.get(r.status, "blue"),
            slippageBps=r.slippage_bps,
            pnl=r.pnl,
        )
        for r in rows
    ]


async def _get_agent_traces(db: AsyncSession) -> list[AgentTraceOut]:
    rows = (
        await db.execute(
            select(AgentTrace).order_by(AgentTrace.created_at.desc()).limit(20)
        )
    ).scalars().all()
    return [
        AgentTraceOut(
            time=_fmt_time(r.created_at),
            agent=r.agent,
            action=r.action,
            detail=r.detail or "",
            tone=r.tone,
            icon=r.icon or "info",
        )
        for r in rows
    ]


async def _get_summary(db: AsyncSession) -> ExecutionSummary:
    pending = (
        await db.execute(select(func.count(Approval.id)).where(Approval.status == "pending"))
    ).scalar() or 0
    urgent = (
        await db.execute(
            select(func.count(Approval.id))
            .where(Approval.status == "pending", Approval.urgency == "high")
        )
    ).scalar() or 0
    blocked = (
        await db.execute(
            select(func.count(Approval.id)).where(Approval.status == "expired")
        )
    ).scalar() or 0
    approved24h = (
        await db.execute(
            select(func.count(Approval.id)).where(Approval.status == "approved")
        )
    ).scalar() or 0
    return ExecutionSummary(
        pending=int(pending),
        urgent=int(urgent),
        blocked=int(blocked),
        approved24h=int(approved24h),
        avgLatencySec=0.0,
        successRate=0.0,
    )


@router.get("/overview", response_model=ExecutionScreen)
async def get_execution_overview(db: DbSession) -> ExecutionScreen:
    """Return the Execution Center screen — approvals and orders from DB."""
    approvals = await _get_approvals(db)
    order_book = await _get_order_book(db)
    agent_traces = await _get_agent_traces(db)
    summary = await _get_summary(db)
    return ExecutionScreen(
        summary=summary,
        approvals=approvals,
        preTradeChecks=_PRE_TRADE_CHECKS,
        orderBook=order_book,
        metrics=_METRICS,
        agentTrace=agent_traces,
    )


@router.get("/approvals", response_model=list[ApprovalOut])
async def list_approvals(
    db: DbSession,
    status: str = Query(default="pending"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ApprovalOut]:
    """List trade approval requests filtered by status."""
    rows = (
        await db.execute(
            select(Approval)
            .where(Approval.status == status)
            .order_by(Approval.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [_approval_to_out(a) for a in rows]


@router.post("/approvals/{approval_id}/approve")
async def approve_trade(approval_id: str, db: DbSession) -> dict[str, str]:
    """Approve a pending trade and write audit log."""
    row = (await db.execute(select(Approval).where(Approval.id == approval_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="approval not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail=f"approval is already {row.status}")

    row.status = "approved"
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        action="approve_trade",
        resource_type="approval",
        resource_id=approval_id,
        actor_type="human",
        result="approved",
        result_tone="green",
        detail=f"{row.side} {row.qty} {row.symbol} @ {row.limit_price}",
    )
    await ws_manager.broadcast(
        {"type": "approval_update", "approval_id": approval_id, "status": "approved",
         "symbol": row.symbol, "side": row.side, "qty": row.qty},
        topic="execution-events",
    )
    return {"approval_id": approval_id, "status": "approved"}


@router.post("/approvals/{approval_id}/reject")
async def reject_trade(approval_id: str, db: DbSession) -> dict[str, str]:
    """Reject a pending trade and write audit log."""
    row = (await db.execute(select(Approval).where(Approval.id == approval_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="approval not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail=f"approval is already {row.status}")

    row.status = "rejected"
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        action="reject_trade",
        resource_type="approval",
        resource_id=approval_id,
        actor_type="human",
        result="rejected",
        result_tone="red",
        detail=f"{row.side} {row.qty} {row.symbol} @ {row.limit_price}",
    )
    await ws_manager.broadcast(
        {"type": "approval_update", "approval_id": approval_id, "status": "rejected",
         "symbol": row.symbol, "side": row.side},
        topic="execution-events",
    )
    return {"approval_id": approval_id, "status": "rejected"}
