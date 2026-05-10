"""Audit domain models — immutable audit logs and idempotency keys."""

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class AuditLog(BaseModel):
    """Immutable audit log — append only, no updates or deletes."""

    __tablename__ = "audit_logs"

    actor: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(32), default="system")  # human / agent / system
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    result: Mapped[str] = mapped_column(String(32), default="success")
    result_tone: Mapped[str] = mapped_column(String(16), default="green")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    curr_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)


class IdempotencyKey(BaseModel):
    """Idempotency key record for duplicate request prevention."""

    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_code: Mapped[int | None] = mapped_column(nullable=True)


class EventOutbox(BaseModel):
    """Event outbox for reliable event publishing."""

    __tablename__ = "event_outbox"

    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    published_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
