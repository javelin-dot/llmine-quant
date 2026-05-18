"""Portfolio Service API — NAV, allocation, correlation, concentration, rebalance."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.portfolio.models import NAVSnapshot, RebalanceProposal
from app.domains.portfolio.schemas import (
    NAV,
    Allocation,
    Concentration,
    Correlation,
    PortfolioScreen,
    RebalanceAction,
    RiskBudget,
)
from app.services.audit_service import AuditService

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]

_URGENCY_TONE = {"high": "red", "medium": "yellow", "low": "green"}

# ── Static overlays (risk budget slice, allocations) — wired from portfolio analytics later ──

_RISK_BUDGET: list[RiskBudget] = []

_ALLOCATION = Allocation(strategies=[])

_CORRELATION = Correlation(labels=[], matrix=[])

_CONCENTRATION = Concentration(sectors=[], holdings=[], factors=[])


async def _get_nav(db: AsyncSession) -> NAV:
    snap = (
        await db.execute(
            select(NAVSnapshot).order_by(NAVSnapshot.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if snap is None:
        return NAV(
            total=0.0, currency="CNY", todayPnl=0.0, todayPct=0.0,
            mtdPct=0.0, ytdPct=0.0, cashPct=0.0, leverage=1.0,
            netExposure=0.0, varDaily=0.0, varPct=0.0,
        )
    pct = round(snap.pnl / max(snap.nav - snap.pnl, 1) * 100, 2) if snap.nav else 0.0
    return NAV(
        total=snap.nav,
        currency="CNY",
        todayPnl=snap.pnl,
        todayPct=pct,
        mtdPct=0.0,
        ytdPct=0.0,
        cashPct=0.0,
        leverage=snap.leverage,
        netExposure=0.0,
        varDaily=0.0,
        varPct=0.0,
    )


async def _get_rebalance(db: AsyncSession) -> list[RebalanceAction]:
    rows = (
        await db.execute(
            select(RebalanceProposal)
            .where(RebalanceProposal.status == "pending")
            .order_by(RebalanceProposal.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    return [
        RebalanceAction(
            id=r.id,
            type=r.type,
            from_=r.from_symbol or "—",
            to=r.to_symbol or "—",
            delta=r.delta or "—",
            reason=r.reason or "",
            impact=r.impact or "",
            urgency=r.urgency,
            urgencyTone=_URGENCY_TONE.get(r.urgency, "yellow"),
        )
        for r in rows
    ]


@router.get("/overview", response_model=PortfolioScreen)
async def get_portfolio_overview(db: DbSession) -> PortfolioScreen:
    """Return the Portfolio Cockpit screen — NAV and rebalance from DB."""
    nav = await _get_nav(db)
    rebalance = await _get_rebalance(db)
    return PortfolioScreen(
        nav=nav,
        riskBudget=_RISK_BUDGET,
        allocation=_ALLOCATION,
        correlation=_CORRELATION,
        concentration=_CONCENTRATION,
        rebalance=rebalance,
    )


@router.get("/rebalance", response_model=list[RebalanceAction])
async def list_rebalance_proposals(db: DbSession) -> list[RebalanceAction]:
    """List pending rebalance proposals."""
    return await _get_rebalance(db)


@router.post("/rebalance/{proposal_id}/approve")
async def approve_rebalance(proposal_id: str, db: DbSession) -> dict[str, str]:
    """Approve a rebalance proposal and write audit log."""
    row = (
        await db.execute(select(RebalanceProposal).where(RebalanceProposal.id == proposal_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="rebalance proposal not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail=f"proposal is already {row.status}")

    row.status = "approved"
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        action="approve_rebalance",
        resource_type="rebalance_proposal",
        resource_id=proposal_id,
        actor_type="human",
        result="approved",
        result_tone="green",
        detail=f"{row.type}: {row.from_symbol} → {row.to_symbol} {row.delta}",
    )
    return {"proposal_id": proposal_id, "status": "approved"}
