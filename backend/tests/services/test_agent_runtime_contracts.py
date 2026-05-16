import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.agents.models import AgentDefinition, WorkflowDefinition, WorkflowEdge, WorkflowNode
from app.services.agents.runtime import ContractValidationError, build_langgraph_workflow


@pytest.fixture
async def session():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def make_agent(agent_id: str, role: str, input_required='payload') -> AgentDefinition:
    return AgentDefinition(
        id=agent_id, name=role.title(), role=role, avatar='A',
        model_config_json='{"provider":"mock","model":"mock"}',
        system_prompt='system', user_prompt_template='{{normalized_input}}',
        output_schema_json='{"type":"object","properties":{"result":{"type":"object"},"status":{"type":"string"}},"required":["result","status"]}',
        normalized_input_schema_json='{"type":"object","properties":{"traceId":{"type":"string"},"payload":{"type":"object"}},"required":["traceId","'+input_required+'"]}',
        normalized_output_schema_json='{"type":"object","properties":{"traceId":{"type":"string"},"status":{"type":"string"},"payload":{"type":"object"}},"required":["traceId","status","payload"]}',
        input_mapping_json='[{"from":"payload","to":"payload"}]',
        output_mapping_json='[{"from":"result","to":"payload"}]',
    )


async def test_edge_mapping_preserves_contracts(session):
    session.add_all([make_agent('ad-a','a'), make_agent('ad-b','b')])
    session.add(WorkflowDefinition(id='wf', name='wf'))
    session.add_all([
        WorkflowNode(id='n1', workflow_id='wf', agent_definition_id='ad-a'),
        WorkflowNode(id='n2', workflow_id='wf', agent_definition_id='ad-b'),
        WorkflowEdge(id='e1', workflow_id='wf', source_node_id='n1', target_node_id='n2', mapping_json='[{"from":"payload","to":"payload"}]'),
    ])
    await session.commit()
    graph = await build_langgraph_workflow(session,'wf')
    result = await graph.ainvoke({'traceId':'t','payload':{'seed':1},'current':{'payload':{'seed':1}},'nodeResults':{},'history':[]})
    assert result['current']['payload']['agent'] == 'b'


async def test_invalid_mapping_fails_contract(session):
    session.add_all([make_agent('ad-a','a'), make_agent('ad-b','b')])
    session.add(WorkflowDefinition(id='wf', name='wf'))
    session.add_all([
        WorkflowNode(id='n1', workflow_id='wf', agent_definition_id='ad-a'),
        WorkflowNode(id='n2', workflow_id='wf', agent_definition_id='ad-b'),
        WorkflowEdge(id='e1', workflow_id='wf', source_node_id='n1', target_node_id='n2', mapping_json='[{"from":"missing","to":"payload"}]'),
    ])
    await session.commit()
    graph = await build_langgraph_workflow(session,'wf')
    with pytest.raises(ContractValidationError, match='映射源字段不存在'):
        await graph.ainvoke({'traceId':'t','payload':{'seed':1},'current':{'payload':{'seed':1}},'nodeResults':{},'history':[]})
