import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.agents.models import AgentDefinition, WorkflowDefinition, WorkflowEdge, WorkflowNode
from app.services.agents.runtime import build_langgraph_workflow


@pytest.fixture
async def session():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def test_langgraph_workflow_executes_configured_agents(session):
    for role in ['research', 'risk']:
        session.add(AgentDefinition(
            id=f'ad-{role}', name=role.title(), role=role, avatar='A',
            model_config_json='{"provider":"mock","model":"mock"}',
            system_prompt=f'You are {role}', user_prompt_template='{{normalized_input}}',
        ))
    session.add(WorkflowDefinition(id='wf-1', name='wf', is_default=True))
    session.add_all([
        WorkflowNode(id='n1', workflow_id='wf-1', agent_definition_id='ad-research', position_x=0, position_y=0),
        WorkflowNode(id='n2', workflow_id='wf-1', agent_definition_id='ad-risk', position_x=100, position_y=0),
        WorkflowEdge(id='e1', workflow_id='wf-1', source_node_id='n1', target_node_id='n2'),
    ])
    await session.commit()

    graph = await build_langgraph_workflow(session, 'wf-1')
    result = await graph.ainvoke({'traceId': 'trace-1', 'payload': {'foo': 'bar'}, 'current': {'foo': 'bar'}, 'nodeResults': {}, 'history': []})

    assert result['current']['payload']['agent'] == 'risk'
    assert [h['agent'] for h in result['history']] == ['research', 'risk']
