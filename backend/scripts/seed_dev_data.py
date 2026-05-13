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
        await _seed_circuit_breakers(session)
        await _seed_risk_budgets(session)
        await session.commit()
        print("Database seeded successfully.")


async def _seed_users(session: AsyncSession) -> None:
    """Seed default users and roles."""
    from app.domains.identity.models import Organization, Role, User, UserRole

    org = Organization(id="org-001", name="LLMine Dev", status="active", plan="enterprise")
    session.add(org)

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

    roles = [
        Role(id="role-admin", name="admin", scope="global"),
        Role(id="role-researcher", name="researcher", scope="global"),
        Role(id="role-trader", name="trader", scope="global"),
        Role(id="role-risk", name="risk_officer", scope="global"),
        Role(id="role-viewer", name="viewer", scope="global"),
    ]
    session.add_all(roles)

    assignments = [
        UserRole(user_id=admin.id, role_id="role-admin"),
        UserRole(user_id=researcher.id, role_id="role-researcher"),
        UserRole(user_id=trader.id, role_id="role-trader"),
    ]
    session.add_all(assignments)


async def _seed_circuit_breakers(session: AsyncSession) -> None:
    """Seed default circuit breaker configuration."""
    from app.domains.risk.models import CircuitBreaker

    circuits = [
        CircuitBreaker(
            id="cb-l1",
            level="L1",
            name="可恢复熔断",
            trigger="行情延迟 > 5min / 策略心跳异常",
            action="暂停新开仓，允许平仓",
            status="armed",
            status_tone="green",
            triggers24h=0,
        ),
        CircuitBreaker(
            id="cb-l2",
            level="L2",
            name="组合熔断",
            trigger="组合回撤 > 15%",
            action="减仓至 50% 仓位",
            status="armed",
            status_tone="green",
            triggers24h=0,
        ),
        CircuitBreaker(
            id="cb-l3",
            level="L3",
            name="不可恢复熔断",
            trigger="资金异常 / 重复下单 / 风控服务宕机",
            action="全部暂停，冻结账户",
            status="armed",
            status_tone="green",
            triggers24h=0,
        ),
        CircuitBreaker(
            id="cb-l4",
            level="L4",
            name="全市场熔断",
            trigger="大盘单日跌幅 > 7%",
            action="清仓或暂停",
            status="armed",
            status_tone="green",
            triggers24h=0,
        ),
    ]
    session.add_all(circuits)


async def _seed_risk_budgets(session: AsyncSession) -> None:
    """Seed default risk budget rows."""
    from app.domains.risk.models import RiskBudget

    budgets = [
        RiskBudget(
            id="rb-daily-loss",
            portfolio_id="port-default",
            metric="单日亏损限额",
            limit_value=0.050,
            used_value=0.032,
            unit="绝对",
            tone="green",
            description="当日已实现+浮亏",
        ),
        RiskBudget(
            id="rb-max-dd",
            portfolio_id="port-default",
            metric="最大回撤限额",
            limit_value=0.200,
            used_value=0.123,
            unit="绝对",
            tone="yellow",
            description="峰值到谷值回撤",
        ),
        RiskBudget(
            id="rb-single-stock",
            portfolio_id="port-default",
            metric="单票集中上限",
            limit_value=0.100,
            used_value=0.085,
            unit="权重",
            tone="green",
            description="个股权重",
        ),
        RiskBudget(
            id="rb-sector",
            portfolio_id="port-default",
            metric="行业集中上限",
            limit_value=0.300,
            used_value=0.220,
            unit="权重",
            tone="green",
            description="单一行业权重",
        ),
        RiskBudget(
            id="rb-net-exposure",
            portfolio_id="port-default",
            metric="净敞口限额",
            limit_value=0.800,
            used_value=0.650,
            unit="比例",
            tone="green",
            description="净多头/空头比例",
        ),
    ]
    session.add_all(budgets)


if __name__ == "__main__":
    asyncio.run(seed())
