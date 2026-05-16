"""API tests for workflow publishing and immutable version snapshots."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.domains.agents.models import AgentDefinition, WorkflowDefinition, WorkflowEdge, WorkflowNode
from app.main import app


@pytest.fixture
async def client_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        async def override_get_db():
            yield session
        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, session
        app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_workflow(session) -> None:
    normalized_in = '{"type":"object","properties":{"traceId":{"type":"string"},"payload":{"type":"object"}},"required":["traceId","payload"]}'
    normalized_out = '{"type":"object","properties":{"traceId":{"type":"string"},"status":{"type":"string"},"payload":{"type":"object"}},"required":["traceId","status","payload"]}'
    for role in ("research", "risk"):
        session.add(
            AgentDefinition(
                id=f"ad-{role}",
                name=role.title(),
                role=role,
                normalized_input_schema_json=normalized_in,
                normalized_output_schema_json=normalized_out,
            )
        )
    session.add(WorkflowDefinition(id="wf-1", name="Workflow", version="1.0.0"))
    session.add_all(
        [
            WorkflowNode(id="n1", workflow_id="wf-1", agent_definition_id="ad-research"),
            WorkflowNode(id="n2", workflow_id="wf-1", agent_definition_id="ad-risk"),
            WorkflowEdge(
                id="e1",
                workflow_id="wf-1",
                source_node_id="n1",
                target_node_id="n2",
                mapping_json='[{"from":"payload","to":"payload"}]',
            ),
        ]
    )
    await session.commit()


async def test_publish_creates_immutable_version_snapshot(client_session):
    client, session = client_session
    await _seed_workflow(session)

    first = await client.post("/api/v1/agents/workflows/wf-1/publish")
    assert first.status_code == 200
    body = first.json()
    assert body["workflow"]["status"] == "published"
    assert body["version"]["version"] == "1.0.0"
    assert body["version"]["snapshot"]["workflow"]["nodes"][0]["id"] == "n1"

    update = body["workflow"]
    update["nodes"][0]["label"] = "changed"
    updated = await client.put("/api/v1/agents/workflows/wf-1", json={k: v for k, v in update.items() if k != "id"})
    assert updated.json()["status"] == "draft"

    versions = await client.get("/api/v1/agents/workflows/wf-1/versions")
    assert versions.json()[0]["snapshot"]["workflow"]["nodes"][0]["label"] is None

    second = await client.post("/api/v1/agents/workflows/wf-1/publish")
    assert second.json()["version"]["version"] == "1.0.1"


async def test_publish_rejects_invalid_contract(client_session):
    client, session = client_session
    await _seed_workflow(session)
    edge = await session.get(WorkflowEdge, "e1")
    edge.mapping_json = "[]"
    await session.commit()

    resp = await client.post("/api/v1/agents/workflows/wf-1/publish")
    assert resp.status_code == 422
    assert "下游必填字段 payload 未映射" in str(resp.json())
