"""Database session management."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("db")

_engine_kw: dict = {"echo": settings.database_echo, "future": True}
if settings.database_url.startswith("sqlite"):
    _engine_kw["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(settings.database_url, **_engine_kw)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """Dependency to get a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
