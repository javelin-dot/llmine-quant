"""Seed development data into the database."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.core.security import hash_password


async def seed() -> None:
    """Seed the database with development data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await _seed_users(session)
        await session.commit()
        print("Database seeded successfully.")


async def _seed_users(session: AsyncSession) -> None:
    """Seed default users and roles."""
    from app.domains.identity.models import Organization, Role, User, UserRole

    # Organization
    org = Organization(id="org-001", name="LLMine Dev", status="active", plan="enterprise")
    session.add(org)

    # Users
    admin = User(
        id="user-admin",
        email="admin@llmine.local",
        name="系统管理员",
        hashed_password=hash_password("admin123"),
        status="active",
        org_id=org.id,
    )
    researcher = User(
        id="user-researcher",
        email="researcher@llmine.local",
        name="量化研究员",
        hashed_password=hash_password("research123"),
        status="active",
        org_id=org.id,
    )
    trader = User(
        id="user-trader",
        email="trader@llmine.local",
        name="交易员",
        hashed_password=hash_password("trade123"),
        status="active",
        org_id=org.id,
    )
    session.add_all([admin, researcher, trader])

    # Roles
    roles = [
        Role(id="role-admin", name="admin", scope="global"),
        Role(id="role-researcher", name="researcher", scope="global"),
        Role(id="role-trader", name="trader", scope="global"),
        Role(id="role-risk", name="risk_officer", scope="global"),
        Role(id="role-viewer", name="viewer", scope="global"),
    ]
    session.add_all(roles)

    # Assign roles
    assignments = [
        UserRole(user_id=admin.id, role_id="role-admin"),
        UserRole(user_id=researcher.id, role_id="role-researcher"),
        UserRole(user_id=trader.id, role_id="role-trader"),
    ]
    session.add_all(assignments)


if __name__ == "__main__":
    asyncio.run(seed())
