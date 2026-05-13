"""Audit log service — append-only audit trail with SHA-256 hash chain.

Each entry links to the previous via prev_hash/curr_hash, forming an
immutable tamper-evident chain. The chain can be verified with
AuditService.verify_chain().
"""

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tracing import get_actor_id, get_trace_id
from app.db.base_class import now_utc
from app.domains.audit.models import AuditLog


def _compute_hash(entry: AuditLog, prev_hash: str) -> str:
    raw = "|".join([
        entry.actor or "",
        entry.actor_type or "",
        entry.action or "",
        entry.resource_type or "",
        entry.resource_id or "",
        entry.result or "",
        entry.created_at.isoformat() if entry.created_at else "",
        prev_hash,
    ])
    return hashlib.sha256(raw.encode()).hexdigest()


class AuditService:
    """Append-only audit log wrapper with SHA-256 hash chain."""

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
        """Append a single audit entry with hash chaining. Returns the persisted row."""
        # Get prev_hash from most recent log
        latest = (
            await self.session.execute(
                select(AuditLog).order_by(AuditLog.created_at.desc()).limit(1)
            )
        ).scalars().first()
        prev_hash = latest.curr_hash or "" if latest else ""

        ts = now_utc()
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
            prev_hash=prev_hash,
            updated_at=ts,
            created_at=ts,
        )
        # Compute curr_hash before persisting
        entry.curr_hash = _compute_hash(entry, prev_hash)
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def verify_chain(self, limit: int = 500) -> tuple[bool, int, str]:
        """Verify the hash chain for the most recent `limit` entries.

        Returns (is_valid, verified_count, first_broken_id_or_empty).
        """
        rows = (
            await self.session.execute(
                select(AuditLog).order_by(AuditLog.created_at.asc()).limit(limit)
            )
        ).scalars().all()

        if not rows:
            return True, 0, ""

        prev_hash = rows[0].prev_hash or ""
        for row in rows:
            if row.curr_hash is None:
                # Legacy row without hash — skip
                prev_hash = row.curr_hash or ""
                continue
            expected = _compute_hash(row, prev_hash)
            if expected != row.curr_hash:
                return False, rows.index(row), row.id
            prev_hash = row.curr_hash

        return True, len(rows), ""
