"""End-to-end tests for all screen APIs."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


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

    async def test_trigger_circuit(self, client: AsyncClient):
        resp = await client.post("/api/v1/risk/circuit-breakers/L2/trigger")
        assert resp.status_code == 200
        assert resp.json()["status"] == "triggered"

    async def test_recover_circuit(self, client: AsyncClient):
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

    async def test_approve_rebalance(self, client: AsyncClient):
        resp = await client.post("/api/v1/portfolio/rebalance/rb1/approve")
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

    async def test_approve_trade(self, client: AsyncClient):
        resp = await client.post("/api/v1/execution/approvals/ap1/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    async def test_reject_trade(self, client: AsyncClient):
        resp = await client.post("/api/v1/execution/approvals/ap1/reject")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"


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
