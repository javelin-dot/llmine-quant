"""Portfolio Service API — NAV, allocation, correlation, concentration, rebalance."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.portfolio.models import NAVSnapshot, RebalanceProposal
from app.domains.portfolio.schemas import (
    Allocation,
    AllocationStrategy,
    Concentration,
    ConcentrationFactor,
    ConcentrationHolding,
    ConcentrationSector,
    Correlation,
    NAV,
    PortfolioScreen,
    RebalanceAction,
    RiskBudget,
)
from app.services.audit_service import AuditService

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]

_URGENCY_TONE = {"high": "red", "medium": "yellow", "low": "green"}

# ── Static data (strategy allocation, correlation, concentration) ─────────────
# These require strategy performance data that will be populated from backtest/
# paper trading in a later sprint. Kept as representative constants.

_RISK_BUDGET = [
    RiskBudget(label="总风险预算使用率", pct=0.65, limit=0.85, tone="green", desc="距 85% 阈值仍有 20pt 缓冲"),
    RiskBudget(label="单策略最大占比", pct=0.30, limit=0.35, tone="yellow", desc="Value-ROE 30%,接近 35% 上限"),
    RiskBudget(label="行业集中度", pct=0.18, limit=0.25, tone="green", desc="消费板块 18%,在安全区间"),
    RiskBudget(label="现金缓冲", pct=0.18, limit=0.10, tone="blue", desc="高于 10% 下限,可承接调仓"),
]

_ALLOCATION = Allocation(
    strategies=[
        AllocationStrategy(name="Value-ROE-v12", family="价值", weight=0.30, pnl=412000.0, pnlPct=0.158, risk="A-", status="live", statusTone="green", contribution=0.42, sparkline=[1.00, 1.02, 1.03, 1.05, 1.08, 1.10, 1.13, 1.15, 1.16]),
        AllocationStrategy(name="Trend-MA-v8", family="趋势", weight=0.18, pnl=186000.0, pnlPct=0.142, risk="B+", status="live", statusTone="green", contribution=0.18, sparkline=[1.00, 1.01, 1.04, 1.03, 1.06, 1.08, 1.11, 1.12, 1.14]),
        AllocationStrategy(name="XGBoost-Alpha", family="ML", weight=0.10, pnl=98400.0, pnlPct=0.218, risk="B", status="live", statusTone="green", contribution=0.11, sparkline=[1.00, 1.03, 1.05, 1.08, 1.12, 1.15, 1.18, 1.20, 1.22]),
        AllocationStrategy(name="NewEnergy-Pair", family="配对", weight=0.04, pnl=-12400.0, pnlPct=-0.034, risk="B-", status="paper", statusTone="yellow", contribution=-0.01, sparkline=[1.00, 1.02, 1.01, 0.99, 0.98, 0.97, 0.97, 0.96, 0.97]),
        AllocationStrategy(name="现金缓冲", family="现金", weight=0.18, pnl=1840.0, pnlPct=0.0001, risk="A+", status="live", statusTone="blue", contribution=0.01, sparkline=[1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    ],
)

_CORRELATION = Correlation(
    labels=["Value", "Trend", "XGB", "Pair", "Cash"],
    matrix=[
        [1.00, 0.32, 0.28, 0.12, 0.05],
        [0.32, 1.00, 0.42, 0.22, 0.04],
        [0.28, 0.42, 1.00, 0.14, 0.03],
        [0.12, 0.22, 0.14, 1.00, 0.02],
        [0.05, 0.04, 0.03, 0.02, 1.00],
    ],
)

_CONCENTRATION = Concentration(
    sectors=[
        ConcentrationSector(name="消费", weight=0.18, change=0.012),
        ConcentrationSector(name="科技", weight=0.16, change=0.024),
        ConcentrationSector(name="金融", weight=0.14, change=-0.008),
        ConcentrationSector(name="新能源", weight=0.12, change=-0.018),
        ConcentrationSector(name="医药", weight=0.10, change=0.006),
    ],
    holdings=[
        ConcentrationHolding(symbol="600519", name="贵州茅台", weight=0.082, change=0.018),
        ConcentrationHolding(symbol="300750", name="宁德时代", weight=0.064, change=-0.024),
        ConcentrationHolding(symbol="600036", name="招商银行", weight=0.058, change=0.006),
        ConcentrationHolding(symbol="000333", name="美的集团", weight=0.052, change=0.014),
        ConcentrationHolding(symbol="002594", name="比亚迪", weight=0.048, change=-0.012),
    ],
    factors=[
        ConcentrationFactor(name="Value 价值", exposure=0.42, tone="green"),
        ConcentrationFactor(name="Quality 质量", exposure=0.38, tone="green"),
        ConcentrationFactor(name="Momentum 动量", exposure=0.24, tone="blue"),
        ConcentrationFactor(name="Size 规模", exposure=-0.18, tone="yellow"),
    ],
)


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
