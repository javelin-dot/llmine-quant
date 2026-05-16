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
        await _seed_agent_workflow(session)
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


async def _seed_agent_workflow(session: AsyncSession) -> None:
    """Seed full default agent definitions and the default trading workflow."""
    import json
    from app.domains.agents.models import AgentDefinition, WorkflowDefinition, WorkflowEdge, WorkflowNode

    common_runtime = {"timeoutSeconds": 120, "maxRetries": 2, "retryBackoffSeconds": 5, "humanApprovalRequired": False}
    default_model = {"provider": "openai", "model": "gpt-5.4", "temperature": 0.2, "topP": 1, "maxTokens": 4096}
    normalized_in = {
        "type": "object",
        "properties": {"traceId": {"type": "string"}, "marketContext": {"type": "object"}, "payload": {"type": "object"}},
        "required": ["traceId", "payload"],
    }
    normalized_out = {
        "type": "object",
        "properties": {"traceId": {"type": "string"}, "status": {"type": "string"}, "payload": {"type": "object"}},
        "required": ["traceId", "status", "payload"],
    }
    specs = [
        ("research", "研", "Research Agent", "扫描研究数据并生成研究摘要", "向 Strategy Agent 传递研究摘要"),
        ("strategy", "策", "Strategy Agent", "生成策略候选与参数空间", "向 Backtest Agent 传递策略草案"),
        ("backtest", "测", "Backtest Agent", "执行回测并产出验证结论", "向 Explain Agent 传递指标"),
        ("explain", "析", "Explain Agent", "生成归因与偏差解释", "向 Portfolio Agent 传递归因摘要"),
        ("portfolio", "组", "Portfolio Agent", "生成组合权重与再平衡建议", "向 Execution Agent 传递执行清单"),
        ("execution", "执", "Execution Agent", "生成订单草案并执行审批流", "向 Risk Agent 传递成交与订单状态"),
        ("risk", "险", "Risk Agent", "执行全链路风险校验", "向链路返回许可、降级或熔断"),
    ]
    rows: list[AgentDefinition] = []
    for role, avatar, name, objective, downstream in specs:
        rows.append(
            AgentDefinition(
                id=f"agent-def-{role}",
                name=name,
                role=role,
                avatar=avatar,
                description=f"{name} 默认定义",
                objective=objective,
                downstream_hint=downstream,
                autonomy="human_gate" if role == "execution" else "supervised",
                status="active",
                model_config_json=json.dumps(default_model, ensure_ascii=False),
                system_prompt=f"你是 {name}。必须遵守量化交易系统的安全、审计与结构化输出约束。",
                user_prompt_template="基于以下标准化输入执行任务：{{normalized_input}}",
                input_schema_json=json.dumps({"type": "object", "properties": {"payload": {"type": "object"}}}, ensure_ascii=False),
                output_schema_json=json.dumps({"type": "object", "properties": {"result": {"type": "object"}}}, ensure_ascii=False),
                normalized_input_schema_json=json.dumps(normalized_in, ensure_ascii=False),
                normalized_output_schema_json=json.dumps(normalized_out, ensure_ascii=False),
                input_mapping_json=json.dumps([{"from": "payload", "to": "payload"}], ensure_ascii=False),
                output_mapping_json=json.dumps([{"from": "result", "to": "payload"}], ensure_ascii=False),
                tool_policy_json=json.dumps([], ensure_ascii=False),
                constraints_json=json.dumps(
                    [{"name": "structured_output", "type": "schema", "rule": "必须返回 normalizedOutputSchema"}],
                    ensure_ascii=False,
                ),
                runtime_policy_json=json.dumps(common_runtime | {"humanApprovalRequired": role == "execution"}, ensure_ascii=False),
            )
        )
    session.add_all(rows)
    workflow = WorkflowDefinition(
        id="workflow-default-trading",
        name="默认交易链路",
        description="研究 → 策略 → 回测 → 解释 → 组合 → 执行 → 风控",
        version="1.0.0",
        status="draft",
        is_default=True,
    )
    session.add(workflow)
    nodes = [
        WorkflowNode(
            id=f"node-{role}",
            workflow_id=workflow.id,
            agent_definition_id=f"agent-def-{role}",
            label=name,
            position_x=40 + idx * 220,
            position_y=120,
            config_override_json="{}",
        )
        for idx, (role, _avatar, name, _objective, _downstream) in enumerate(specs)
    ]
    session.add_all(nodes)
    session.add_all(
        [
            WorkflowEdge(
                id=f"edge-{specs[idx][0]}-{specs[idx + 1][0]}",
                workflow_id=workflow.id,
                source_node_id=f"node-{specs[idx][0]}",
                target_node_id=f"node-{specs[idx + 1][0]}",
                mapping_json='[{"from":"payload","to":"payload"}]',
                condition_json="{}",
            )
            for idx in range(len(specs) - 1)
        ]
    )


if __name__ == "__main__":
    asyncio.run(seed())
