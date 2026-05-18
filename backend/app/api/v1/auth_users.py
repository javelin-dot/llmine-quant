"""Admin-only user directory: list, invite (create + role), update profile flags."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import fetch_user_role_names, get_admin_user
from app.core.security import hash_password
from app.db.session import get_db
from app.domains.identity.models import Role, User, UserRole

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(get_admin_user)]


class UserListRow(BaseModel):
    user_id: str
    email: str
    name: str
    status: str
    roles: list[str]


class RoleRow(BaseModel):
    id: str
    name: str
    description: str | None


class InviteUserBody(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=3, max_length=256)
    role_name: str = Field(default="researcher", min_length=2, max_length=64)
    password: str | None = None


class InviteUserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    initial_password: str
    role_name: str


class UpdateUserBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    status: str | None = None


@router.get("/users", response_model=list[UserListRow])
async def list_users(db: DbSession, _admin: AdminUser) -> list[UserListRow]:
    users = (await db.execute(select(User).order_by(User.created_at.asc()))).scalars().all()
    rows: list[UserListRow] = []
    for user in users:
        roles = await fetch_user_role_names(db, user.id)
        rows.append(
            UserListRow(
                user_id=user.id,
                email=user.email,
                name=user.name,
                status=user.status,
                roles=roles,
            )
        )
    return rows


@router.get("/roles", response_model=list[RoleRow])
async def list_roles(db: DbSession, _admin: AdminUser) -> list[RoleRow]:
    rs = (await db.execute(select(Role).order_by(Role.name.asc()))).scalars().all()
    return [RoleRow(id=r.id, name=r.name, description=r.description) for r in rs]


@router.post("/users", response_model=InviteUserResponse, status_code=201)
async def invite_user(db: DbSession, admin: AdminUser, body: InviteUserBody) -> InviteUserResponse:
    """Create a user with a known initial password and one role (invite / onboard)."""
    email_n = body.email.strip().lower()
    existing = (await db.execute(select(User).where(User.email == email_n))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    if body.password is not None and len(body.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")

    role = (await db.execute(select(Role).where(Role.name == body.role_name.strip()))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role_name")

    initial = body.password if body.password else secrets.token_urlsafe(12)
    user = User(
        email=email_n,
        name=body.name.strip(),
        hashed_password=hash_password(initial),
        status="active",
        org_id=admin.org_id,
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()
    await db.refresh(user)

    return InviteUserResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        initial_password=initial,
        role_name=role.name,
    )


@router.patch("/users/{user_id}", response_model=UserListRow)
async def update_user(
    user_id: str,
    db: DbSession,
    admin: AdminUser,
    body: UpdateUserBody,
) -> UserListRow:
    if body.name is None and body.status is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update")

    if body.status is not None and body.status not in ("active", "inactive"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status must be active or inactive")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.status == "inactive" and user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account")

    if body.name is not None:
        user.name = body.name.strip()
    if body.status is not None:
        user.status = body.status

    await db.commit()
    await db.refresh(user)

    roles = await fetch_user_role_names(db, user.id)
    return UserListRow(
        user_id=user.id,
        email=user.email,
        name=user.name,
        status=user.status,
        roles=roles,
    )
