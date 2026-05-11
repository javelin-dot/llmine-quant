"""Audit log service — append-only audit trail wrapper.

Centralises construction of `AuditLog` rows so callers don't need to wire up
trace_id / actor / timestamps themselves.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tracing import get_actor_id, get_trace_id
from app.db.base_class import now_utc
from app.domains.audit.models import AuditLog


class AuditService:
    """Append-only audit log wrapper."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor: str | None = None,
        actor_type: str = "system",
        result: str = "success",
        result_tone: str = "green",
        confidence: float | None = None,
        detail: str | None = None,
    ) -> AuditLog:
        """Append a single audit entry. Returns the persisted row."""
        entry = AuditLog(
            actor=actor or get_actor_id() or "system",
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            result_tone=result_tone,
            confidence=confidence,
            detail=detail,
            trace_id=get_trace_id(),
            updated_at=now_utc(),
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry
