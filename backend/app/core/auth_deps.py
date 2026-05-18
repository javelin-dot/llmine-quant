"""Auth dependencies — reusable FastAPI Depends for JWT-based authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.domains.identity.models import Role, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Require a valid JWT; raise 401 if missing or invalid."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = decode_access_token(token)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = (await db.execute(select(User).where(User.id == claims["sub"]))).scalar_one_or_none()
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Return current user if authenticated, None otherwise (for public endpoints)."""
    if not token:
        return None
    claims = decode_access_token(token)
    if not claims:
        return None
    return (await db.execute(select(User).where(User.id == claims["sub"]))).scalar_one_or_none()


async def fetch_user_role_names(db: AsyncSession, user_id: str) -> list[str]:
    """Role `name` values assigned to ``user_id`` (e.g. admin, researcher)."""
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            UserRole.deleted_at.is_(None),
            Role.deleted_at.is_(None),
        )
        .order_by(Role.name.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def user_has_admin_role(db: AsyncSession, user_id: str) -> bool:
    """True if ``user_id`` has the global ``admin`` role."""
    stmt = (
        select(UserRole.id)
        .select_from(UserRole)
        .join(Role, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            Role.name == "admin",
            UserRole.deleted_at.is_(None),
            Role.deleted_at.is_(None),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def get_admin_user(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """Require bearer token plus global ``admin`` role assignment."""
    if not await user_has_admin_role(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return current_user
