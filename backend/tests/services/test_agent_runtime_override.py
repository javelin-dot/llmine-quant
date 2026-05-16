import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.agents.models import AgentDefinition, WorkflowDefinition, WorkflowNode
from app.services.agents.runtime import build_langgraph_workflow

@pytest.fixture
async def session():
    engine=create_async_engine('sqlite+aiosqlite:///:memory:', future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker=async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with maker() as s:
        yield s
    await engine.dispose()

async def test_node_override_changes_runtime_contract(session):
    session.add(AgentDefinition(
        id='ad', name='A', role='a', avatar='A', model_config_json='{"provider":"mock","model":"mock"}',
        system_prompt='system', user_prompt_template='{{normalized_input}}',
        output_schema_json='{"type":"object","properties":{"result":{"type":"object"},"status":{"type":"string"}},"required":["result","status"]}',
        normalized_output_schema_json='{"type":"object","properties":{"traceId":{"type":"string"},"status":{"type":"string"},"payload":{"type":"object"}},"required":["traceId","status","payload"]}',
        output_mapping_json='[{"from":"result","to":"payload"}]',
    ))
    session.add(WorkflowDefinition(id='wf', name='wf'))
    session.add(WorkflowNode(id='n', workflow_id='wf', agent_definition_id='ad', config_override_json='{"userPromptTemplate":"override {{normalized_input}}"}'))
    await session.commit()
    graph=await build_langgraph_workflow(session,'wf')
    result=await graph.ainvoke({'traceId':'t','payload':{},'current':{},'nodeResults':{},'history':[]})
    assert result['current']['payload']['agent']=='a'
