"""Security domain models — vault keys, AI permissions, withdrawal guards."""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class VaultKey(BaseModel):
    """Vault-managed key (API key, wallet key, SSH key, etc.)."""

    __tablename__ = "vault_keys"

    label: Mapped[str] = mapped_column(String(128), nullable=False)
    key_type: Mapped[str] = mapped_column(String(32), nullable=False)  # api / wallet / ssh / webhook / db
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    rotated_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expires_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    days_to_expiry: Mapped[int] = mapped_column(Integer, default=365)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active / rotating / expiring / expired
    scope: Mapped[str | None] = mapped_column(String(256), nullable=True)
    encrypted_value: Mapped[str | None] = mapped_column(Text, nullable=True)


class AIPermission(BaseModel):
    """AI tool permission rule."""

    __tablename__ = "ai_permissions"

    category: Mapped[str] = mapped_column(String(64), nullable=False)
    api_name: Mapped[str] = mapped_column(String(128), nullable=False)
    desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed: Mapped[bool] = mapped_column(default=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class WithdrawalRule(BaseModel):
    """Withdrawal guard rule."""

    __tablename__ = "withdrawal_rules"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="enabled")  # enforced / enabled / disabled


class SecurityEvent(BaseModel):
    """Security audit event."""

    __tablename__ = "security_events"

    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # rotation / block / access / violation / audit
    severity: Mapped[str] = mapped_column(String(16), default="info")  # critical / high / medium / low / info
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="resolved")  # resolved / ongoing / review
