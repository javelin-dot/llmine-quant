"""Celery tasks driving the paper-trading EOD batch."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.domains.execution.paper_models import PaperAccount
from app.services.paper_trading import PaperTradingEngine
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.paper_trading.run_eod_for_all_accounts")
def run_eod_for_all_accounts(trade_date: str | None = None) -> list[dict[str, object]]:
    """Iterate every active PaperAccount and run the EOD cycle.

    ``trade_date`` defaults to today (YYYY-MM-DD). Beat schedule does not
    pass a date so the natural call is "today's close".
    """
    target_date = trade_date or datetime.now().date().isoformat()
    return asyncio.run(_run_eod_for_all(target_date))


@celery_app.task(name="app.tasks.paper_trading.run_eod_for_account")
def run_eod_for_account(account_id: str, trade_date: str) -> dict[str, object]:
    """Run the EOD cycle for a single account — handy for backfills."""
    return asyncio.run(_run_eod_for_account(account_id, trade_date))


# ── coroutines ─────────────────────────────────────────────────────────


async def _run_eod_for_all(trade_date: str) -> list[dict[str, object]]:
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(PaperAccount.id).where(
                    PaperAccount.status == "active",
                    PaperAccount.deleted_at.is_(None),
                )
            )
        ).scalars().all()

    out: list[dict[str, object]] = []
    for account_id in rows:
        try:
            out.append(await _run_eod_for_account(account_id, trade_date))
        except Exception as exc:  # noqa: BLE001
            logger.exception("paper EOD failed for %s", account_id)
            out.append({"accountId": account_id, "error": str(exc)})
    return out


async def _run_eod_for_account(account_id: str, trade_date: str) -> dict[str, object]:
    async with AsyncSessionLocal() as session:
        engine = PaperTradingEngine(session)
        summary = await engine.run_end_of_day(account_id, trade_date)
        return {
            "accountId": summary.account_id,
            "tradeDate": summary.trade_date,
            "ordersCreated": summary.orders_created,
            "ordersFilled": summary.orders_filled,
            "ordersRejected": summary.orders_rejected,
            "breaches": summary.breaches,
            "nav": summary.nav,
        }
