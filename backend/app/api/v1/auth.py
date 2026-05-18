"""Auth API — login, register, token refresh, logout."""

import hashlib
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import fetch_user_role_names, get_current_user, user_has_admin_role
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.db.base_class import now_utc
from app.db.session import get_db
from app.domains.identity.models import Session, User

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    name: str
    email: str


class RefreshRequest(BaseModel):
    access_token: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/login", response_model=TokenResponse)
async def login(
    db: DbSession,
    form: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    """Authenticate with email + password, return JWT access token."""
    user = (
        await db.execute(select(User).where(User.email == form.username))
    ).scalar_one_or_none()

    if user is None or not user.hashed_password or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")

    expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        data={"sub": user.id, "email": user.email, "name": user.name},
        expires_delta=expires,
    )

    # Record session
    session = Session(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=str((now_utc() + expires).isoformat()),
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(session)
    await db.commit()

    return TokenResponse(
        access_token=token,
        expires_in=int(expires.total_seconds()),
        user_id=user.id,
        name=user.name,
        email=user.email,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    """Create a new account and return a JWT access token."""
    existing = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        name=payload.name.strip(),
        hashed_password=hash_password(payload.password),
        status="active",
    )
    db.add(user)
    await db.flush()  # populate user.id

    expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        data={"sub": user.id, "email": user.email, "name": user.name},
        expires_delta=expires,
    )
    session = Session(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=str((now_utc() + expires).isoformat()),
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(session)
    await db.commit()

    return TokenResponse(
        access_token=token,
        expires_in=int(expires.total_seconds()),
        user_id=user.id,
        name=user.name,
        email=user.email,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    db: DbSession,
) -> TokenResponse:
    """Issue a new access token given a still-valid existing token."""
    claims = decode_access_token(payload.access_token)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = (await db.execute(select(User).where(User.id == claims["sub"]))).scalar_one_or_none()
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    expires = timedelta(minutes=settings.access_token_expire_minutes)
    new_token = create_access_token(
        data={"sub": user.id, "email": user.email, "name": user.name},
        expires_delta=expires,
    )
    session = Session(
        user_id=user.id,
        token_hash=_hash_token(new_token),
        expires_at=str((now_utc() + expires).isoformat()),
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(session)
    await db.commit()

    return TokenResponse(
        access_token=new_token,
        expires_in=int(expires.total_seconds()),
        user_id=user.id,
        name=user.name,
        email=user.email,
    )


@router.post("/logout")
async def logout(payload: RefreshRequest, db: DbSession) -> dict[str, str]:
    """Revoke the given token by deleting its session record."""
    token_hash = _hash_token(payload.access_token)
    session = (
        await db.execute(select(Session).where(Session.token_hash == token_hash))
    ).scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.commit()
    return {"status": "logged_out"}


@router.get("/me")
async def get_me(db: DbSession, current_user: User = Depends(get_current_user)) -> dict:
    """Return current user info from Bearer token (Authorization header)."""
    roles = await fetch_user_role_names(db, current_user.id)
    is_admin = await user_has_admin_role(db, current_user.id)
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "status": current_user.status,
        "roles": roles,
        "is_admin": is_admin,
    }
