"""Identity domain models — users, organizations, roles."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class Organization(BaseModel):
    """Organization / tenant."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    plan: Mapped[str] = mapped_column(String(32), default="free")


class User(BaseModel):
    """System user."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    org_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)


class Role(BaseModel):
    """RBAC role."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="global")
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)


class UserRole(BaseModel):
    """User-role assignment."""

    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class Session(BaseModel):
    """User login session."""

    __tablename__ = "sessions"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    expires_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
