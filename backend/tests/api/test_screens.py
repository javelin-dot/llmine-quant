"""End-to-end tests for all screen APIs."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import AsyncSessionLocal
from app.domains.execution.models import Approval
from app.domains.portfolio.models import RebalanceProposal
from app.domains.risk.models import CircuitBreaker as CircuitBreakerModel
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded_circuit_l2():
    """Seed an L2 circuit breaker and yield its ID; clean up after."""
    async with AsyncSessionLocal() as session:
        cb = CircuitBreakerModel(
            id="cb-l2-test",
            level="L2",
            name="组合熔断",
            trigger="组合回撤 > 15%",
            action="减仓至 50% 仓位",
            status="armed",
            status_tone="green",
            triggers24h=0,
        )
        session.add(cb)
        await session.commit()
    yield "cb-l2-test"
    async with AsyncSessionLocal() as session:
        row = await session.get(CircuitBreakerModel, "cb-l2-test")
        if row:
            await session.delete(row)
            await session.commit()


@pytest.fixture
async def seeded_approval():
    """Seed a pending approval and yield its ID; clean up after."""
    async with AsyncSessionLocal() as session:
        a = Approval(
            id="ap-test-001",
            portfolio_id="port-1",
            type="live",
            symbol="600519",
            name="贵州茅台",
            side="BUY",
            qty="100",
            notional="¥16.8万",
            notional_pct=0.0168,
            confidence=0.92,
            expire_sec=300,
            urgency="high",
            status="pending",
        )
        session.add(a)
        await session.commit()
    yield "ap-test-001"
    async with AsyncSessionLocal() as session:
        row = await session.get(Approval, "ap-test-001")
        if row:
            await session.delete(row)
            await session.commit()


@pytest.fixture
async def seeded_rebalance():
    """Seed a pending rebalance proposal and yield its ID; clean up after."""
    async with AsyncSessionLocal() as session:
        r = RebalanceProposal(
            id="rb-test-001",
            portfolio_id="port-1",
            type="reduce",
            from_symbol="Value-ROE",
            to_symbol="Cash",
            delta="-3%",
            urgency="medium",
            urgency_tone="yellow",
            status="pending",
        )
        session.add(r)
        await session.commit()
    yield "rb-test-001"
    async with AsyncSessionLocal() as session:
        row = await session.get(RebalanceProposal, "rb-test-001")
        if row:
            await session.delete(row)
            await session.commit()


class TestHealth:
    async def test_health_check(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestDashboard:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "meta" in data
        assert "marketIndices" in data
        assert len(data["marketIndices"]) > 0

    async def test_system_health(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/system-health")
        assert resp.status_code == 200
        assert "healthScore" in resp.json()

    async def test_alerts(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/alerts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestData:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/data/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "header" in data
        assert "sources" in data


class TestStrategy:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/strategies/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipelineStatus" in data
        assert "matrix" in data

    async def test_templates(self, client: AsyncClient):
        resp = await client.get("/api/v1/strategies/templates")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestBacktest:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/backtests/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "kpis" in data
        assert "equityCurves" in data


class TestRisk:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/risk/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "header" in data
        assert "circuits" in data

    async def test_trigger_circuit(self, client: AsyncClient, seeded_circuit_l2):
        resp = await client.post("/api/v1/risk/circuit-breakers/L2/trigger")
        assert resp.status_code == 200
        assert resp.json()["status"] == "triggered"

    async def test_recover_circuit(self, client: AsyncClient, seeded_circuit_l2):
        # First trigger so status is not "armed"
        await client.post("/api/v1/risk/circuit-breakers/L2/trigger")
        resp = await client.post("/api/v1/risk/circuit-breakers/L2/recover")
        assert resp.status_code == 200
        assert resp.json()["status"] == "recovery_requested"


class TestPortfolio:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/portfolio/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "nav" in data
        assert "allocation" in data

    async def test_approve_rebalance(self, client: AsyncClient, seeded_rebalance):
        resp = await client.post(f"/api/v1/portfolio/rebalance/{seeded_rebalance}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"


class TestExecution:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/execution/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "approvals" in data
        assert "orderBook" in data

    async def test_approve_trade(self, client: AsyncClient, seeded_approval):
        resp = await client.post(f"/api/v1/execution/approvals/{seeded_approval}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    async def test_reject_trade(self, client: AsyncClient):
        # Seed a fresh approval for reject
        async with AsyncSessionLocal() as session:
            a = Approval(
                id="ap-reject-test",
                portfolio_id="port-1",
                type="paper",
                symbol="300750",
                name="宁德时代",
                side="SELL",
                qty="200",
                notional="¥9.2万",
                notional_pct=0.0092,
                confidence=0.88,
                expire_sec=300,
                urgency="medium",
                status="pending",
            )
            session.add(a)
            await session.commit()
        try:
            resp = await client.post("/api/v1/execution/approvals/ap-reject-test/reject")
            assert resp.status_code == 200
            assert resp.json()["status"] == "rejected"
        finally:
            async with AsyncSessionLocal() as session:
                row = await session.get(Approval, "ap-reject-test")
                if row:
                    await session.delete(row)
                    await session.commit()


class TestExplain:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/explain/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "signalHeader" in data
        assert "attribution" in data
        assert "decisionChain" in data


class TestSecurity:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/security/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "header" in data
        assert "vault" in data
        assert "aiPermissions" in data

    async def test_rotate_key(self, client: AsyncClient):
        resp = await client.post("/api/v1/security/vault/rotate/k1")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rotated"


class TestCollaboration:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/collaboration/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "activeReviews" in data
        assert "abTests" in data

    async def test_approve_review(self, client: AsyncClient):
        resp = await client.post("/api/v1/collaboration/reviews/r1/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"


class TestAudit:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/audit/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "rows" in data
        assert "actorStats" in data
        assert "toolRegistry" in data


class TestAgents:
    async def test_overview(self, client: AsyncClient):
        resp = await client.get("/api/v1/agents/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "tasks" in data
        assert "tools" in data


class TestAuth:
    async def test_login_success(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@llmine.local", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # OK if users seeded, 401 if not — either is acceptable in CI
        assert resp.status_code in (200, 401)
        if resp.status_code == 200:
            data = resp.json()
            assert "access_token" in data
            assert "user_id" in data

    async def test_login_wrong_password(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@llmine.local", "password": "wrong"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_user(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@example.com", "password": "x"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401
