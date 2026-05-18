"""Explain Service API — persisted signal attribution & approval."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.explain.schemas import ExplainApproveIn, ExplainApproveOut, ExplainScreen
from app.services.explain_persistence import approve_explain_trace, get_explain_screen

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/overview", response_model=ExplainScreen)
async def get_explain_overview(db: DbSession) -> ExplainScreen:
    """Return Explain screen assembled from relational tables."""
    return await get_explain_screen(db, trace_id=None)


@router.post("/signal/approve", response_model=ExplainApproveOut)
async def approve_explain_signal(body: ExplainApproveIn, db: DbSession) -> ExplainApproveOut:
    """Persist approval on the Explain signal associated with ``traceId``."""
    return await approve_explain_trace(db, body.traceId)
