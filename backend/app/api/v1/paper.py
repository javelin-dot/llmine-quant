"""Paper trading API — accounts, orders, fills, NAV, breaches, EOD trigger."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tracing import get_actor_id
from app.db.session import get_db
from app.domains.execution.paper_models import (
    PaperAccount,
    PaperFill,
    PaperNavPoint,
    PaperOrder,
    PaperPosition,
    PaperRiskBreach,
)
from app.domains.execution.paper_schemas import (
    PaperAccountCreateIn,
    PaperAccountOut,
    PaperFillOut,
    PaperNavPointOut,
    PaperOrderOut,
    PaperPositionOut,
    PaperRiskBreachOut,
    RunEodIn,
    RunEodOut,
)
from app.services.paper_trading import PaperTradingEngine

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


# ── accounts ────────────────────────────────────────────────────────────


@router.post("/accounts", response_model=PaperAccountOut)
async def create_paper_account(
    payload: PaperAccountCreateIn,
    db: DbSession,
) -> PaperAccountOut:
    """Create a paper trading account."""
    cost_json = json.dumps(payload.cost_config, ensure_ascii=False) if payload.cost_config else None
    account = PaperAccount(
        name=payload.name,
        owner_id=payload.owner_id or get_actor_id() or "system",
        strategy_id=payload.strategy_id,
        strategy_version_id=payload.strategy_version_id,
        market=payload.market,
        base_currency=payload.base_currency,
        initial_cash=payload.initial_cash,
        cash=payload.initial_cash,
        cost_config_json=cost_json,
        inception_date=payload.inception_date or datetime.now(timezone.utc).date().isoformat(),
        peak_nav=payload.initial_cash,
        status="active",
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return _account_out(account)


@router.get("/accounts", response_model=list[PaperAccountOut])
async def list_paper_accounts(db: DbSession) -> list[PaperAccountOut]:
    rows = (
        await db.execute(
            select(PaperAccount).where(PaperAccount.deleted_at.is_(None))
            .order_by(PaperAccount.created_at.desc())
        )
    ).scalars().all()
    return [_account_out(a) for a in rows]


@router.get("/accounts/{account_id}", response_model=PaperAccountOut)
async def get_paper_account(account_id: str, db: DbSession) -> PaperAccountOut:
    account = await db.get(PaperAccount, account_id)
    if account is None or account.deleted_at is not None:
        raise HTTPException(status_code=404, detail="paper account not found")
    return _account_out(account)


# ── positions / orders / fills / nav / breaches ─────────────────────────


@router.get("/accounts/{account_id}/positions", response_model=list[PaperPositionOut])
async def list_paper_positions(account_id: str, db: DbSession) -> list[PaperPositionOut]:
    await _require_account(db, account_id)
    rows = (
        await db.execute(
            select(PaperPosition).where(
                PaperPosition.account_id == account_id, PaperPosition.quantity > 0
            )
            .order_by(PaperPosition.market_value.desc())
        )
    ).scalars().all()
    return [
        PaperPositionOut(
            symbol=p.symbol,
            quantity=p.quantity,
            avgCost=p.avg_cost,
            lastPrice=p.last_price,
            marketValue=p.market_value,
            weight=p.weight,
        )
        for p in rows
    ]


@router.get("/accounts/{account_id}/orders", response_model=list[PaperOrderOut])
async def list_paper_orders(
    account_id: str,
    db: DbSession,
    limit: int = 100,
) -> list[PaperOrderOut]:
    await _require_account(db, account_id)
    rows = (
        await db.execute(
            select(PaperOrder)
            .where(PaperOrder.account_id == account_id)
            .order_by(PaperOrder.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        PaperOrderOut(
            id=o.id,
            accountId=o.account_id,
            strategyId=o.strategy_id,
            tradeDate=o.trade_date,
            symbol=o.symbol,
            side=o.side,
            targetWeight=o.target_weight,
            targetQuantity=o.target_quantity,
            filledQuantity=o.filled_quantity,
            status=o.status,
            reason=o.reason,
            rejectionReason=o.rejection_reason,
        )
        for o in rows
    ]


@router.get("/accounts/{account_id}/fills", response_model=list[PaperFillOut])
async def list_paper_fills(account_id: str, db: DbSession, limit: int = 200) -> list[PaperFillOut]:
    await _require_account(db, account_id)
    rows = (
        await db.execute(
            select(PaperFill)
            .where(PaperFill.account_id == account_id)
            .order_by(PaperFill.trade_date.desc(), PaperFill.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        PaperFillOut(
            id=f.id,
            orderId=f.order_id,
            tradeDate=f.trade_date,
            symbol=f.symbol,
            side=f.side,
            quantity=f.quantity,
            price=f.price,
            amount=f.amount,
            commission=f.commission,
            stampTax=f.stamp_tax,
            slippage=f.slippage,
            totalCost=f.total_cost,
        )
        for f in rows
    ]


@router.get("/accounts/{account_id}/nav", response_model=list[PaperNavPointOut])
async def list_paper_nav(account_id: str, db: DbSession) -> list[PaperNavPointOut]:
    await _require_account(db, account_id)
    rows = (
        await db.execute(
            select(PaperNavPoint)
            .where(PaperNavPoint.account_id == account_id)
            .order_by(PaperNavPoint.trade_date.asc())
        )
    ).scalars().all()
    return [
        PaperNavPointOut(
            tradeDate=p.trade_date,
            nav=p.nav,
            cash=p.cash,
            marketValue=p.market_value,
            dailyReturn=p.daily_return,
            drawdown=p.drawdown,
        )
        for p in rows
    ]


@router.get("/accounts/{account_id}/breaches", response_model=list[PaperRiskBreachOut])
async def list_paper_breaches(account_id: str, db: DbSession) -> list[PaperRiskBreachOut]:
    await _require_account(db, account_id)
    rows = (
        await db.execute(
            select(PaperRiskBreach)
            .where(PaperRiskBreach.account_id == account_id)
            .order_by(PaperRiskBreach.trade_date.desc(), PaperRiskBreach.created_at.desc())
        )
    ).scalars().all()
    return [
        PaperRiskBreachOut(
            id=b.id,
            tradeDate=b.trade_date,
            rule=b.rule,
            severity=b.severity,
            detail=b.detail,
            status=b.status,
        )
        for b in rows
    ]


# ── EOD trigger (manual run; same path that Celery beat calls) ──────────


@router.post("/accounts/{account_id}/run-eod", response_model=RunEodOut)
async def run_eod_manual(
    account_id: str,
    payload: RunEodIn,
    db: DbSession,
) -> RunEodOut:
    """Run the end-of-day cycle for a paper account for a specific trade_date."""
    await _require_account(db, account_id)
    engine = PaperTradingEngine(db)
    summary = await engine.run_end_of_day(account_id, payload.trade_date)
    return RunEodOut(
        account_id=summary.account_id,
        trade_date=summary.trade_date,
        orders_created=summary.orders_created,
        orders_filled=summary.orders_filled,
        orders_rejected=summary.orders_rejected,
        breaches=summary.breaches,
        nav=summary.nav,
    )


# ── helpers ─────────────────────────────────────────────────────────────


def _account_out(a: PaperAccount) -> PaperAccountOut:
    return PaperAccountOut(
        id=a.id,
        name=a.name,
        ownerId=a.owner_id,
        strategyId=a.strategy_id,
        strategyVersionId=a.strategy_version_id,
        market=a.market,
        baseCurrency=a.base_currency,
        initialCash=a.initial_cash,
        cash=a.cash,
        inceptionDate=a.inception_date,
        lastProcessedDate=a.last_processed_date,
        peakNav=a.peak_nav,
        status=a.status,
    )


async def _require_account(db: AsyncSession, account_id: str) -> PaperAccount:
    account = await db.get(PaperAccount, account_id)
    if account is None or account.deleted_at is not None:
        raise HTTPException(status_code=404, detail="paper account not found")
    return account
