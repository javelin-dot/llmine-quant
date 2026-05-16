"""LangChain/LangGraph runtime compiler for configurable agents and workflows."""
from __future__ import annotations

import json
from typing import Any
from typing_extensions import TypedDict

from jsonschema import ValidationError as JsonSchemaValidationError, validate
from langchain.chat_models import init_chat_model
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.agents.models import AgentDefinition, WorkflowDefinition, WorkflowEdge, WorkflowNode


class ContractValidationError(ValueError):
    """Raised when configured workflow contracts are violated at runtime."""


class WorkflowState(TypedDict, total=False):
    traceId: str
    payload: dict[str, Any]
    current: dict[str, Any]
    currentNodeId: str
    nodeResults: dict[str, dict[str, Any]]
    history: list[dict[str, Any]]


def _loads(raw: str | None, default: Any) -> Any:
    try:
        return json.loads(raw) if raw else default
    except Exception:
        return default


def _validate(instance: Any, schema: dict[str, Any], label: str) -> None:
    if not schema:
        return
    try:
        validate(instance=instance, schema=schema)
    except JsonSchemaValidationError as exc:
        path = ".".join(str(p) for p in exc.absolute_path) or "$"
        raise ContractValidationError(f"{label} 校验失败 @ {path}: {exc.message}") from exc


def _get_path(data: Any, path: str) -> Any:
    cur = data
    for part in [p for p in path.split(".") if p]:
        if not isinstance(cur, dict) or part not in cur:
            raise ContractValidationError(f"映射源字段不存在: {path}")
        cur = cur[part]
    return cur


def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
    parts = [p for p in path.split(".") if p]
    if not parts:
        raise ContractValidationError("映射目标字段不能为空")
    cur = data
    for part in parts[:-1]:
        nxt = cur.setdefault(part, {})
        if not isinstance(nxt, dict):
            raise ContractValidationError(f"映射目标路径冲突: {path}")
        cur = nxt
    cur[parts[-1]] = value


def apply_mapping(source: dict[str, Any], mapping: list[dict[str, Any]], *, seed: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply dot-path mappings from source to a new payload."""
    if not mapping:
        return dict(source)
    target = dict(seed or {})
    for item in mapping:
        from_path = str(item.get("from", ""))
        to_path = str(item.get("to", ""))
        _set_path(target, to_path, _get_path(source, from_path))
    return target


def _merge_override(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    merged.update(override)
    return merged


def build_langchain_runnable(
    definition: AgentDefinition,
    *,
    node_id: str,
    incoming_edges: list[WorkflowEdge],
    config_override: dict[str, Any] | None = None,
):
    """Compile one persisted agent definition into a LangChain runnable."""
    override = config_override or {}
    model_cfg = _merge_override(_loads(definition.model_config_json, {}), override.get("modelConfig", {}))
    provider = str(model_cfg.get("provider") or settings.llm_provider or "mock").lower()
    model_name = str(model_cfg.get("model") or settings.openai_model)
    normalized_input_schema = override.get("normalizedInputSchema", _loads(definition.normalized_input_schema_json, {}))
    normalized_output_schema = override.get("normalizedOutputSchema", _loads(definition.normalized_output_schema_json, {}))
    output_schema = override.get("outputSchema", _loads(definition.output_schema_json, {}))
    input_mapping = override.get("inputMapping", _loads(definition.input_mapping_json, []))
    output_mapping = override.get("outputMapping", _loads(definition.output_mapping_json, []))
    system_prompt = str(override.get("systemPrompt", definition.system_prompt))
    user_prompt_template = str(override.get("userPromptTemplate", definition.user_prompt_template))

    if provider == "mock" or settings.llm_provider == "mock":
        model = FakeListChatModel(responses=[json.dumps({"result": {"agent": definition.role}, "status": "ok"})])
    else:
        model = init_chat_model(
            model_name,
            model_provider=provider,
            temperature=model_cfg.get("temperature", 0.2),
            max_tokens=model_cfg.get("maxTokens", settings.llm_max_tokens),
        )

    async def invoke(state: WorkflowState) -> dict[str, Any]:
        current = state.get("current") or state.get("payload") or {}
        source = current
        if incoming_edges:
            source_node = state.get("currentNodeId")
            matching = [e for e in incoming_edges if e.source_node_id == source_node]
            edge_mapping = _loads((matching[0] if matching else incoming_edges[0]).mapping_json, [])
            source = apply_mapping(current, edge_mapping, seed={"traceId": state.get("traceId", "")})
        else:
            source = (
                {"traceId": state.get("traceId", ""), **current}
                if "payload" in current
                else {"traceId": state.get("traceId", ""), "payload": current}
            )
        normalized_input = apply_mapping(source, input_mapping, seed={"traceId": state.get("traceId", "")}) if input_mapping else source
        _validate(normalized_input, normalized_input_schema, f"{definition.role}.normalizedInput")

        user_prompt = user_prompt_template.replace("{{normalized_input}}", json.dumps(normalized_input, ensure_ascii=False))
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await model.ainvoke(messages)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(str(item) for item in content)
        try:
            raw_output = json.loads(str(content))
        except Exception:
            raw_output = {"result": {"text": str(content)}, "status": "ok"}
        _validate(raw_output, output_schema, f"{definition.role}.output")
        normalized_output_payload = apply_mapping(raw_output, output_mapping) if output_mapping else {"payload": raw_output.get("result", raw_output)}
        result = {"traceId": state.get("traceId", ""), "status": raw_output.get("status", "ok"), **normalized_output_payload}
        _validate(result, normalized_output_schema, f"{definition.role}.normalizedOutput")
        prior_results = dict(state.get("nodeResults", {}))
        prior_results[definition.role] = result
        history = [*state.get("history", []), {"agent": definition.role, "result": result}]
        return {"current": result, "currentNodeId": node_id, "nodeResults": prior_results, "history": history}

    return RunnableLambda(invoke).with_config({"run_name": f"agent:{definition.role}"})


async def build_langgraph_workflow(session: AsyncSession, workflow_id: str):
    """Compile persisted workflow nodes/edges into a LangGraph graph."""
    workflow = await session.get(WorkflowDefinition, workflow_id)
    if workflow is None:
        raise ValueError(f"Workflow {workflow_id} not found")
    nodes = (await session.execute(select(WorkflowNode).where(WorkflowNode.workflow_id == workflow_id))).scalars().all()
    edges = (await session.execute(select(WorkflowEdge).where(WorkflowEdge.workflow_id == workflow_id))).scalars().all()
    defs = {
        row.id: row for row in (
            await session.execute(select(AgentDefinition).where(AgentDefinition.id.in_([n.agent_definition_id for n in nodes])))
        ).scalars().all()
    }
    incoming_by_node: dict[str, list[WorkflowEdge]] = {}
    for edge in edges:
        incoming_by_node.setdefault(edge.target_node_id, []).append(edge)

    graph = StateGraph(WorkflowState)
    for node in nodes:
        definition = defs[node.agent_definition_id]
        graph.add_node(
            node.id,
            build_langchain_runnable(
                definition,
                node_id=node.id,
                incoming_edges=incoming_by_node.get(node.id, []),
                config_override=_loads(node.config_override_json, {}),
            ),
        )

    incoming = {edge.target_node_id for edge in edges}
    outgoing = {edge.source_node_id for edge in edges}
    roots = [node.id for node in nodes if node.id not in incoming]
    leaves = [node.id for node in nodes if node.id not in outgoing]
    for root in roots:
        graph.add_edge(START, root)
    for edge in edges:
        graph.add_edge(edge.source_node_id, edge.target_node_id)
    for leaf in leaves:
        graph.add_edge(leaf, END)
    return graph.compile()
