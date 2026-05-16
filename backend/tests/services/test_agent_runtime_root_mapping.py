import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.agents.models import AgentDefinition, WorkflowDefinition, WorkflowNode
from app.services.agents.runtime import build_langgraph_workflow


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def test_root_node_wraps_initial_payload_for_configured_input_mapping(session):
    session.add(
        AgentDefinition(
            id="ad-root",
            name="Root",
            role="root",
            avatar="R",
            model_config_json='{"provider":"mock","model":"mock"}',
            input_mapping_json='[{"from":"payload","to":"payload"}]',
            output_mapping_json='[{"from":"result","to":"payload"}]',
            normalized_input_schema_json='{"type":"object","properties":{"traceId":{"type":"string"},"payload":{"type":"object"}},"required":["traceId","payload"]}',
            normalized_output_schema_json='{"type":"object","properties":{"traceId":{"type":"string"},"status":{"type":"string"},"payload":{"type":"object"}},"required":["traceId","status","payload"]}',
        )
    )
    session.add(WorkflowDefinition(id="wf-root", name="wf-root"))
    session.add(WorkflowNode(id="n1", workflow_id="wf-root", agent_definition_id="ad-root"))
    await session.commit()

    graph = await build_langgraph_workflow(session, "wf-root")
    result = await graph.ainvoke(
        {
            "traceId": "trace-root",
            "payload": {"symbol": "600519.SH"},
            "current": {"symbol": "600519.SH"},
            "nodeResults": {},
            "history": [],
        }
    )

    assert result["current"]["status"] == "ok"
    assert result["history"][0]["agent"] == "root"
