"""Agent Orchestrator API — agent registry, tasks, messages, tool registry."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.agents.models import (
    AgentDefinition,
    AgentMessage,
    AgentRegistry,
    AgentTask,
    ToolRegistry,
    WorkflowDefinition,
    WorkflowEdge,
    WorkflowNode,
    WorkflowVersion,
)
from app.domains.agents.schemas import (
    AgentDefinitionCreate,
    AgentDefinitionOut,
    AgentDefinitionUpdate,
    AgentMessageCreate,
    AgentMessageOut,
    AgentOut,
    AgentOverview,
    AgentTaskCreate,
    AgentTaskOut,
    ToolOut,
    WorkflowCreate,
    WorkflowEdgeOut,
    WorkflowNodeOut,
    WorkflowOut,
    WorkflowRunCreate,
    WorkflowRunOut,
    WorkflowPublishOut,
    WorkflowVersionOut,
    WorkflowUpdate,
)
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.agents.runtime import build_langgraph_workflow
from app.core.tracing import get_trace_id

router = APIRouter()


def _json_load(raw: str | None, default):
    try:
        return json.loads(raw) if raw else default
    except Exception:
        return default


def _agent_out(agent: AgentRegistry) -> AgentOut:
    return AgentOut(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        status=agent.status,
        statusTone="green" if agent.status == "active" else "gray" if agent.status == "idle" else "yellow",
        currentTask=agent.current_task or "—",
        metric=agent.metric or "—",
        heartbeat=agent.heartbeat_at or "—",
    )


def _task_out(task: AgentTask, agent_name: str = "") -> AgentTaskOut:
    tones = {
        "pending": "yellow",
        "running": "blue",
        "succeeded": "green",
        "failed": "red",
    }
    return AgentTaskOut(
        id=task.id,
        agentId=task.agent_id,
        agentName=agent_name,
        taskType=task.task_type,
        priority=task.priority,
        status=task.status,
        statusTone=tones.get(task.status, "gray"),
        createdAt=task.created_at.isoformat() if task.created_at else "",
        startedAt=task.started_at,
        completedAt=task.completed_at,
        result=task.result_json,
    )


def _message_out(msg: AgentMessage) -> AgentMessageOut:
    return AgentMessageOut(
        id=msg.id,
        fromAgent=msg.from_agent,
        toAgent=msg.to_agent,
        msgType=msg.msg_type,
        topic=msg.topic,
        payload=msg.payload_json,
        correlationId=msg.correlation_id,
        createdAt=msg.created_at.isoformat() if msg.created_at else "",
    )


def _tool_out(tool: ToolRegistry) -> ToolOut:
    try:
        allowed = json.loads(tool.allowed_agents) if tool.allowed_agents else []
    except Exception:
        allowed = []
    level_map = {"low": ("低风险", "green"), "medium": ("中风险", "yellow"), "high": ("高风险", "red")}
    label, tone = level_map.get(tool.level, ("未知", "gray"))
    return ToolOut(
        id=tool.id,
        name=tool.name,
        level=label,
        levelTone=tone,
        description=tool.description or "",
        allowedAgents=allowed,
        enabled=tool.enabled,
    )


def _definition_out(agent: AgentDefinition) -> AgentDefinitionOut:
    return AgentDefinitionOut(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        avatar=agent.avatar,
        description=agent.description or "",
        objective=agent.objective or "",
        downstreamHint=agent.downstream_hint or "",
        autonomy=agent.autonomy,
        status=agent.status,
        modelConfig=_json_load(agent.model_config_json, {}),
        systemPrompt=agent.system_prompt,
        userPromptTemplate=agent.user_prompt_template,
        inputSchema=_json_load(agent.input_schema_json, {}),
        outputSchema=_json_load(agent.output_schema_json, {}),
        normalizedInputSchema=_json_load(agent.normalized_input_schema_json, {}),
        normalizedOutputSchema=_json_load(agent.normalized_output_schema_json, {}),
        inputMapping=_json_load(agent.input_mapping_json, []),
        outputMapping=_json_load(agent.output_mapping_json, []),
        toolPolicy=_json_load(agent.tool_policy_json, []),
        constraints=_json_load(agent.constraints_json, []),
        runtimePolicy=_json_load(agent.runtime_policy_json, {}),
    )


def _apply_definition_payload(agent: AgentDefinition, payload: AgentDefinitionCreate | AgentDefinitionUpdate) -> None:
    agent.name = payload.name
    agent.role = payload.role
    agent.avatar = payload.avatar
    agent.description = payload.description
    agent.objective = payload.objective
    agent.downstream_hint = payload.downstreamHint
    agent.autonomy = payload.autonomy
    agent.status = payload.status
    agent.model_config_json = json.dumps(payload.modelConfig, ensure_ascii=False)
    agent.system_prompt = payload.systemPrompt
    agent.user_prompt_template = payload.userPromptTemplate
    agent.input_schema_json = json.dumps(payload.inputSchema, ensure_ascii=False)
    agent.output_schema_json = json.dumps(payload.outputSchema, ensure_ascii=False)
    agent.normalized_input_schema_json = json.dumps(payload.normalizedInputSchema, ensure_ascii=False)
    agent.normalized_output_schema_json = json.dumps(payload.normalizedOutputSchema, ensure_ascii=False)
    agent.input_mapping_json = json.dumps(payload.inputMapping, ensure_ascii=False)
    agent.output_mapping_json = json.dumps(payload.outputMapping, ensure_ascii=False)
    agent.tool_policy_json = json.dumps(payload.toolPolicy, ensure_ascii=False)
    agent.constraints_json = json.dumps(payload.constraints, ensure_ascii=False)
    agent.runtime_policy_json = json.dumps(payload.runtimePolicy, ensure_ascii=False)


async def _workflow_out(db: AsyncSession, workflow: WorkflowDefinition) -> WorkflowOut:
    node_rows = (
        await db.execute(select(WorkflowNode).where(WorkflowNode.workflow_id == workflow.id))
    ).scalars().all()
    edge_rows = (
        await db.execute(select(WorkflowEdge).where(WorkflowEdge.workflow_id == workflow.id))
    ).scalars().all()
    return WorkflowOut(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description or "",
        version=workflow.version,
        status=workflow.status,
        isDefault=workflow.is_default,
        nodes=[
            WorkflowNodeOut(
                id=n.id,
                agentDefinitionId=n.agent_definition_id,
                label=n.label,
                positionX=n.position_x,
                positionY=n.position_y,
                configOverride=_json_load(n.config_override_json, {}),
            )
            for n in node_rows
        ],
        edges=[
            WorkflowEdgeOut(
                id=e.id,
                sourceNodeId=e.source_node_id,
                targetNodeId=e.target_node_id,
                mapping=_json_load(e.mapping_json, []),
                condition=_json_load(e.condition_json, {}),
            )
            for e in edge_rows
        ],
    )


def _workflow_version_out(row: WorkflowVersion) -> WorkflowVersionOut:
    return WorkflowVersionOut(
        id=row.id,
        workflowId=row.workflow_id,
        version=row.version,
        status=row.status,
        publishedAt=row.created_at.isoformat() if row.created_at else "",
        snapshot=_json_load(row.snapshot_json, {}),
    )


def _schema_fields(schema: dict) -> set[str]:
    properties = schema.get("properties", {})
    return set(properties.keys()) if isinstance(properties, dict) else set()


def _required_fields(schema: dict) -> list[str]:
    required = schema.get("required", [])
    return [str(item) for item in required] if isinstance(required, list) else []


async def _workflow_contract_issues(db: AsyncSession, workflow: WorkflowDefinition) -> list[str]:
    graph = await _workflow_out(db, workflow)
    definitions = {
        row.id: row
        for row in (
            await db.execute(select(AgentDefinition))
        ).scalars().all()
    }
    issues: list[str] = []
    node_ids = {node.id for node in graph.nodes}
    if not graph.nodes:
        issues.append("工作流至少需要一个节点")
    for edge in graph.edges:
        if edge.sourceNodeId not in node_ids or edge.targetNodeId not in node_ids:
            issues.append(f"边 {edge.id} 存在缺失节点")
            continue
        source_node = next(node for node in graph.nodes if node.id == edge.sourceNodeId)
        target_node = next(node for node in graph.nodes if node.id == edge.targetNodeId)
        source = definitions.get(source_node.agentDefinitionId)
        target = definitions.get(target_node.agentDefinitionId)
        if source is None or target is None:
            issues.append(f"边 {edge.id} 引用了不存在的 Agent")
            continue
        source_fields = _schema_fields(_json_load(source.normalized_output_schema_json, {}))
        target_required = [
            field
            for field in _required_fields(_json_load(target.normalized_input_schema_json, {}))
            if field != "traceId"
        ]
        mapped_from = [str(item.get("from", "")) for item in edge.mapping]
        mapped_to = {str(item.get("to", "")) for item in edge.mapping}
        for field in mapped_from:
            if field and field not in source_fields:
                issues.append(f"{source.name} → {target.name}: 上游字段 {field} 不存在")
        for field in target_required:
            if field not in mapped_to:
                issues.append(f"{source.name} → {target.name}: 下游必填字段 {field} 未映射")
    return issues


def _next_patch_version(raw: str) -> str:
    parts = raw.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return "1.0.0"
    major, minor, patch = (int(part) for part in parts)
    return f"{major}.{minor}.{patch + 1}"


async def _build_workflow_snapshot(db: AsyncSession, workflow: WorkflowDefinition) -> dict:
    graph = await _workflow_out(db, workflow)
    definition_ids = {node.agentDefinitionId for node in graph.nodes}
    definitions = (
        await db.execute(select(AgentDefinition).where(AgentDefinition.id.in_(definition_ids)))
    ).scalars().all()
    return {
        "workflow": graph.model_dump(),
        "agentDefinitions": [_definition_out(row).model_dump() for row in definitions],
    }


@router.get("/overview", response_model=AgentOverview)
async def get_agent_overview(db: AsyncSession = Depends(get_db)) -> AgentOverview:
    """Return the complete Agent Orchestrator overview (DB-driven)."""
    agents_result = await db.execute(select(AgentRegistry).order_by(AgentRegistry.name))
    agents = [_agent_out(a) for a in agents_result.scalars().all()]

    tasks_result = await db.execute(
        select(AgentTask).order_by(desc(AgentTask.created_at)).limit(20)
    )
    tasks = [_task_out(t) for t in tasks_result.scalars().all()]

    messages_result = await db.execute(
        select(AgentMessage).order_by(desc(AgentMessage.created_at)).limit(20)
    )
    messages = [_message_out(m) for m in messages_result.scalars().all()]

    tools_result = await db.execute(select(ToolRegistry).order_by(ToolRegistry.name))
    tools = [_tool_out(t) for t in tools_result.scalars().all()]

    return AgentOverview(agents=agents, tasks=tasks, messages=messages, tools=tools)


@router.post("/tasks", response_model=AgentTaskOut)
async def create_agent_task(
    payload: AgentTaskCreate,
    db: AsyncSession = Depends(get_db),
) -> AgentTaskOut:
    """Create a new agent task and dispatch it."""
    orchestrator = AgentOrchestrator(db)
    task = await orchestrator.dispatch(
        agent_role=payload.agent_role,
        task_type=payload.task_type,
        payload=payload.payload or {},
        priority=payload.priority,
        correlation_id=payload.correlation_id,
    )
    return _task_out(task)


@router.get("/tasks/{task_id}", response_model=AgentTaskOut)
async def get_agent_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> AgentTaskOut:
    """Get a single agent task."""
    task = await db.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_out(task)


@router.post("/messages", response_model=AgentMessageOut)
async def send_agent_message(
    payload: AgentMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> AgentMessageOut:
    """Send an inter-agent message."""
    orchestrator = AgentOrchestrator(db)
    msg = await orchestrator.send_message(
        from_agent=payload.from_agent,
        to_agent=payload.to_agent,
        topic=payload.topic,
        payload=payload.payload,
        correlation_id=payload.correlation_id,
        msg_type=payload.msg_type,
    )
    return _message_out(msg)


@router.get("/messages", response_model=list[AgentMessageOut])
async def get_agent_messages(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> list[AgentMessageOut]:
    """List recent inter-agent messages."""
    rows = await db.execute(
        select(AgentMessage).order_by(desc(AgentMessage.created_at)).limit(limit)
    )
    return [_message_out(m) for m in rows.scalars().all()]


@router.get("/definitions", response_model=list[AgentDefinitionOut])
async def list_agent_definitions(db: AsyncSession = Depends(get_db)) -> list[AgentDefinitionOut]:
    rows = await db.execute(select(AgentDefinition).order_by(AgentDefinition.name))
    return [_definition_out(row) for row in rows.scalars().all()]


@router.post("/definitions", response_model=AgentDefinitionOut)
async def create_agent_definition(
    payload: AgentDefinitionCreate,
    db: AsyncSession = Depends(get_db),
) -> AgentDefinitionOut:
    agent = AgentDefinition()
    _apply_definition_payload(agent, payload)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _definition_out(agent)


@router.put("/definitions/{agent_id}", response_model=AgentDefinitionOut)
async def update_agent_definition(
    agent_id: str,
    payload: AgentDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
) -> AgentDefinitionOut:
    agent = await db.get(AgentDefinition, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent definition not found")
    _apply_definition_payload(agent, payload)
    await db.commit()
    await db.refresh(agent)
    return _definition_out(agent)


@router.delete("/definitions/{agent_id}")
async def delete_agent_definition(agent_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    agent = await db.get(AgentDefinition, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent definition not found")
    await db.delete(agent)
    await db.commit()
    return {"status": "deleted"}


@router.get("/workflows", response_model=list[WorkflowOut])
async def list_workflows(db: AsyncSession = Depends(get_db)) -> list[WorkflowOut]:
    rows = await db.execute(select(WorkflowDefinition).order_by(desc(WorkflowDefinition.is_default), WorkflowDefinition.name))
    return [await _workflow_out(db, row) for row in rows.scalars().all()]


async def _replace_workflow_graph(db: AsyncSession, workflow: WorkflowDefinition, payload: WorkflowCreate | WorkflowUpdate) -> None:
    old_edges = (await db.execute(select(WorkflowEdge).where(WorkflowEdge.workflow_id == workflow.id))).scalars().all()
    old_nodes = (await db.execute(select(WorkflowNode).where(WorkflowNode.workflow_id == workflow.id))).scalars().all()
    for row in old_edges:
        await db.delete(row)
    for row in old_nodes:
        await db.delete(row)

    id_map: dict[str, str] = {}
    for node in payload.nodes:
        row = WorkflowNode(
            id=node.id or None,
            workflow_id=workflow.id,
            agent_definition_id=node.agentDefinitionId,
            label=node.label,
            position_x=node.positionX,
            position_y=node.positionY,
            config_override_json=json.dumps(node.configOverride, ensure_ascii=False),
        )
        db.add(row)
        await db.flush()
        if node.id:
            id_map[node.id] = row.id
    for edge in payload.edges:
        db.add(
            WorkflowEdge(
                id=edge.id or None,
                workflow_id=workflow.id,
                source_node_id=id_map.get(edge.sourceNodeId, edge.sourceNodeId),
                target_node_id=id_map.get(edge.targetNodeId, edge.targetNodeId),
                mapping_json=json.dumps(edge.mapping, ensure_ascii=False),
                condition_json=json.dumps(edge.condition, ensure_ascii=False),
            )
        )


@router.post("/workflows", response_model=WorkflowOut)
async def create_workflow(payload: WorkflowCreate, db: AsyncSession = Depends(get_db)) -> WorkflowOut:
    workflow = WorkflowDefinition(
        name=payload.name,
        description=payload.description,
        version=payload.version,
        status=payload.status,
        is_default=payload.isDefault,
    )
    db.add(workflow)
    await db.flush()
    await _replace_workflow_graph(db, workflow, payload)
    await db.commit()
    await db.refresh(workflow)
    return await _workflow_out(db, workflow)


@router.put("/workflows/{workflow_id}", response_model=WorkflowOut)
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
) -> WorkflowOut:
    workflow = await db.get(WorkflowDefinition, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow.name = payload.name
    workflow.description = payload.description
    workflow.version = payload.version
    workflow.status = "draft"
    workflow.is_default = payload.isDefault
    await _replace_workflow_graph(db, workflow, payload)
    await db.commit()
    await db.refresh(workflow)
    return await _workflow_out(db, workflow)


@router.get("/workflows/{workflow_id}/versions", response_model=list[WorkflowVersionOut])
async def list_workflow_versions(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowVersionOut]:
    workflow = await db.get(WorkflowDefinition, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    rows = (
        await db.execute(
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_id)
            .order_by(desc(WorkflowVersion.created_at))
        )
    ).scalars().all()
    return [_workflow_version_out(row) for row in rows]


@router.post("/workflows/{workflow_id}/publish", response_model=WorkflowPublishOut)
async def publish_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
) -> WorkflowPublishOut:
    workflow = await db.get(WorkflowDefinition, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    issues = await _workflow_contract_issues(db, workflow)
    if issues:
        raise HTTPException(status_code=422, detail={"message": "工作流契约校验失败", "issues": issues})

    latest = (
        await db.execute(
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow.id)
            .order_by(desc(WorkflowVersion.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    version = workflow.version if latest is None else _next_patch_version(latest.version)
    workflow.version = version
    workflow.status = "published"
    snapshot = await _build_workflow_snapshot(db, workflow)
    row = WorkflowVersion(
        workflow_id=workflow.id,
        version=version,
        snapshot_json=json.dumps(snapshot, ensure_ascii=False),
    )
    db.add(row)
    await db.flush()
    workflow.published_version_id = row.id
    await db.commit()
    await db.refresh(workflow)
    await db.refresh(row)
    return WorkflowPublishOut(workflow=await _workflow_out(db, workflow), version=_workflow_version_out(row))


@router.post("/workflows/{workflow_id}/run", response_model=WorkflowRunOut)
async def run_workflow(
    workflow_id: str,
    payload: WorkflowRunCreate,
    db: AsyncSession = Depends(get_db),
) -> WorkflowRunOut:
    """Execute a saved workflow through LangGraph."""
    graph = await build_langgraph_workflow(db, workflow_id)
    trace_id = payload.traceId or get_trace_id()
    result = await graph.ainvoke(
        {
            "traceId": trace_id,
            "payload": payload.payload,
            "current": payload.payload,
            "nodeResults": {},
            "history": [],
        }
    )
    return WorkflowRunOut(workflowId=workflow_id, traceId=trace_id, result=result)
