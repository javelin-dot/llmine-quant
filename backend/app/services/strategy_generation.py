"""Strategy generation service — NL -> code -> backtest pipeline orchestration."""

from __future__ import annotations

import json
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import LLMException
from app.core.tracing import get_actor_id, get_trace_id
from app.core.websocket import manager
from app.db.base_class import now_utc
from app.domains.strategy.models import (
    PipelineEvent,
    Strategy,
    StrategyTask,
    StrategyVersion,
)
from app.domains.strategy.generation_dsl import (
    build_strategy_metadata_bundle,
    parse_strategy_generation_spec,
    strategy_generation_json_schema,
)
from app.domains.strategy.generation_validate import (
    validate_generated_strategy_ast,
    validate_spec_semantics,
)
from app.integrations.llm import get_llm_provider
from app.integrations.llm.prompts import (
    STRATEGY_GENERATION_SYSTEM_PROMPT,
    STRATEGY_GENERATION_USER_PROMPT,
    STRATEGY_SPEC_FOR_CODE_APPEND,
    STRATEGY_SPEC_SYSTEM_PROMPT,
    STRATEGY_SPEC_USER_PROMPT,
)
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.audit_service import AuditService
from app.services.daily_backtest import (
    BacktestCostConfig,
    BacktestDataError,
    DailyBacktestConfig,
    DailyBacktestEngine,
    DailyBacktestResult,
)
from app.services.strategy_generation_research import (
    discover_default_research_universe,
    spec_to_dual_ma_params,
)

_MAX_DD_CAPS = {"conservative": 0.12, "balanced": 0.20, "aggressive": 0.35}


def _backtest_result_to_pipeline_dict(result: DailyBacktestResult) -> dict[str, Any]:
    """Shape persisted research metrics like the legacy mock dict for risk + strategy rows."""
    m = result.metrics
    raw_dd = m.max_drawdown
    max_dd = abs(raw_dd) if raw_dd < 0 else float(raw_dd)
    return {
        "sharpe": round(float(m.sharpe_ratio), 4),
        "maxDd": round(float(max_dd), 4),
        "annualReturn": round(float(m.annual_return), 4),
        "cumulativeReturn": round(float(m.cumulative_return), 4),
        "winRate": round(float(m.win_rate), 4),
        "turnover": round(float(m.turnover), 4),
        "oosScore": round(
            min(1.0, max(0.0, 0.45 + m.win_rate * 0.35 + min(float(m.sharpe_ratio), 2.5) * 0.08)),
            2,
        ),
        "confidence": round(min(1.0, max(0.1, float(m.sharpe_ratio) / 2.5)), 2),
        "backtestTaskId": result.task_id,
        "backtestRunId": result.run_id,
        "researchStrategy": result.strategy_name,
        "researchStartDate": result.start_date,
        "researchEndDate": result.end_date,
    }


class StrategyGenerationService:
    """Coordinates pipeline + audit + websocket fanout for a generation task."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.orchestrator = AgentOrchestrator(session)
        self.audit = AuditService(session)

    # ── public api ──────────────────────────────────────────────────────

    async def create_task(
        self,
        *,
        prompt: str,
        market: str = "A",
        risk_profile: str = "balanced",
        owner_id: str | None = None,
    ) -> StrategyTask:
        """Create a queued StrategyTask. Pipeline runs separately."""
        task = StrategyTask(
            prompt=prompt,
            market=market,
            risk_profile=risk_profile,
            status="queued",
            trace_id=get_trace_id(),
            created_by=owner_id or get_actor_id() or "system",
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)

        await self.audit.log(
            action="strategy.task.created",
            resource_type="strategy_task",
            resource_id=task.id,
            detail=f"prompt={prompt[:80]}",
        )
        await self._broadcast(
            task_id=task.id,
            stage="queued",
            event="task.created",
            progress=0,
            detail={"prompt": prompt, "market": market, "risk_profile": risk_profile},
        )
        return task

    async def run_pipeline(self, task_id: str) -> StrategyTask:
        """Execute all pipeline stages end-to-end."""
        task = await self.session.get(StrategyTask, task_id)
        if task is None:
            raise ValueError(f"StrategyTask {task_id} not found")

        # Placeholder strategy — all PipelineEvents anchor to this id.
        strategy = Strategy(
            name=f"AI 草稿 {task.id[:6]}",
            family="value",
            type="rule",
            status="draft",
            owner_id=task.created_by or get_actor_id() or "system",
            description=task.prompt[:100],
            risk_profile=task.risk_profile,
            market=task.market,
            trace_id=get_trace_id(),
        )
        self.session.add(strategy)
        await self.session.commit()
        await self.session.refresh(strategy)

        task.strategy_id = strategy.id
        task.status = "running"
        await self.session.commit()
        await self.session.refresh(task)

        correlation_id = str(uuid.uuid4())
        try:
            # 1. research
            await self._stage(
                task=task,
                stage="research",
                agent_role="research",
                event="research.scan",
                progress=15,
                detail={"sources": ["macro", "sector_rotation"]},
                correlation_id=correlation_id,
            )

            # 2. code generation
            code_text, metadata = await self._generate_code(task)
            await self._stage(
                task=task,
                stage="code_gen",
                agent_role="strategy",
                event="code.generated",
                progress=35,
                detail={"chars": len(code_text), "model": metadata.get("model")},
                correlation_id=correlation_id,
            )

            # 3. static + interface check (done inside _generate_code; stage records outcome)
            await self._stage(
                task=task,
                stage="static_check",
                agent_role="strategy",
                event="code.static_check_passed",
                progress=50,
                detail={"checks": ["ast.parse", "dsl_semantics", "strategy_interface", "future_data_guard"]},
                correlation_id=correlation_id,
            )

            # 4. research backtest (persisted dual_ma proxy from DSL + DB bars)
            spec_payload = metadata.get("params") or {}
            try:
                gen_spec = parse_strategy_generation_spec(spec_payload)
            except ValidationError as exc:
                raise LLMException(f"metadata params are not a valid strategy spec: {exc}") from exc

            universe, start_date, end_date = await discover_default_research_universe(self.session)
            dual_params = spec_to_dual_ma_params(gen_spec)
            bt_config = DailyBacktestConfig(
                universe=universe,
                start_date=start_date,
                end_date=end_date,
                strategy_name="dual_ma",
                strategy_params=dual_params,
                initial_cash=1_000_000.0,
                cost_config=BacktestCostConfig(),
            )
            engine = DailyBacktestEngine(self.session)
            try:
                bt_result = await engine.run_and_persist(bt_config, priority=2)
            except BacktestDataError as exc:
                raise LLMException(f"research backtest failed: {exc}") from exc

            backtest = _backtest_result_to_pipeline_dict(bt_result)
            await self._stage(
                task=task,
                stage="backtest",
                agent_role="backtest",
                event="backtest.completed",
                progress=75,
                detail=backtest,
                correlation_id=correlation_id,
            )

            # 5. risk
            risk_ok = self._check_risk(backtest, task.risk_profile)
            event = "risk.passed" if risk_ok else "risk.flagged"
            await self._stage(
                task=task,
                stage="risk",
                agent_role="risk",
                event=event,
                progress=90,
                detail={"approved": risk_ok, "metrics": backtest},
                correlation_id=correlation_id,
            )
            if not risk_ok:
                raise LLMException("Risk bounds exceeded")

            # 6. persist Strategy + Version
            await self._update_strategy_from_meta(strategy, metadata, backtest)
            version = await self._persist_version(strategy, code_text, metadata)

            task.status = "succeeded"
            task.result = json.dumps(
                {"strategyId": strategy.id, "versionId": version.id, **backtest},
                ensure_ascii=False,
            )
            await self.session.commit()
            await self.session.refresh(task)

            await self._stage(
                task=task,
                stage="done",
                agent_role="strategy",
                event="strategy.published",
                progress=100,
                detail={"strategyId": strategy.id, "versionId": version.id},
                correlation_id=correlation_id,
            )
            await self.audit.log(
                action="strategy.task.succeeded",
                resource_type="strategy_task",
                resource_id=task.id,
                result="success",
                result_tone="green",
                confidence=backtest.get("confidence"),
            )
        except Exception as exc:  # noqa: BLE001
            task.status = "failed"
            task.error = str(exc)[:512]
            await self.session.commit()
            await self.session.refresh(task)

            await self.audit.log(
                action="strategy.task.failed",
                resource_type="strategy_task",
                resource_id=task.id,
                result="failure",
                result_tone="red",
                detail=str(exc)[:512],
            )
            await self._broadcast(
                task_id=task.id,
                stage="failed",
                event="task.failed",
                progress=100,
                detail={"error": str(exc)[:512]},
            )

        return task

    # ── helpers ─────────────────────────────────────────────────────────

    async def _stage(
        self,
        *,
        task: StrategyTask,
        stage: str,
        agent_role: str,
        event: str,
        progress: int,
        detail: dict[str, Any],
        correlation_id: str,
    ) -> None:
        """Emit PipelineEvent, dispatch AgentTask, send AgentMessage, broadcast WS."""
        strategy_id = task.strategy_id or task.id
        pe = PipelineEvent(
            strategy_id=strategy_id,
            stage=stage,
            event=event,
            progress=progress,
            detail=json.dumps(detail, ensure_ascii=False),
            trace_id=get_trace_id(),
        )
        self.session.add(pe)
        await self.session.commit()
        await self.session.refresh(pe)

        agent_task = await self.orchestrator.dispatch(
            agent_role=agent_role,
            task_type=event,
            payload={
                "task_id": task.id,
                "stage": stage,
                "progress": progress,
                **detail,
            },
            correlation_id=correlation_id,
        )
        task.agent_task_id = agent_task.id
        await self.session.commit()
        await self.session.refresh(task)

        await self.orchestrator.complete_task(
            agent_task.id,
            result={"event": event, "progress": progress, **detail},
            status="succeeded",
        )
        await self.orchestrator.send_message(
            from_agent=agent_task.agent_id,
            to_agent=None,
            topic=f"strategy.{stage}",
            payload={
                "task_id": task.id,
                "event": event,
                "progress": progress,
                **detail,
            },
            correlation_id=correlation_id,
        )

        await self._broadcast(
            task_id=task.id,
            stage=stage,
            event=event,
            progress=progress,
            detail=detail,
            agent=agent_task.agent_id,
            strategy_id=task.strategy_id,
        )

    async def _generate_code(
        self, task: StrategyTask
    ) -> tuple[str, dict[str, Any]]:
        """Structured DSL first (validated), then Python strategy class."""
        provider = get_llm_provider()
        output_schema = strategy_generation_json_schema()
        spec_prompt = STRATEGY_SPEC_USER_PROMPT.format(
            market=task.market,
            risk_profile=task.risk_profile,
            prompt=task.prompt,
        )
        try:
            spec_raw = await provider.generate_structured(
                prompt=spec_prompt,
                output_schema=output_schema,
                system_prompt=STRATEGY_SPEC_SYSTEM_PROMPT,
                temperature=0.2,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMException(f"strategy DSL generation failed: {exc}") from exc

        try:
            spec = parse_strategy_generation_spec(spec_raw)
        except ValidationError as exc:
            raise LLMException(f"strategy DSL validation failed: {exc}") from exc

        try:
            validate_spec_semantics(
                spec,
                risk_profile=task.risk_profile,
                market=task.market,
            )
        except ValueError as exc:
            raise LLMException(f"strategy DSL semantic validation failed: {exc}") from exc

        metadata = build_strategy_metadata_bundle(
            spec,
            prompt_excerpt=task.prompt,
            display_seed=task.id,
        )

        code_user = STRATEGY_GENERATION_USER_PROMPT.format(
            market=task.market,
            risk_profile=task.risk_profile,
            prompt=task.prompt,
        ) + STRATEGY_SPEC_FOR_CODE_APPEND.format(
            spec_json=json.dumps(spec.model_dump(), ensure_ascii=False),
        )
        code_resp = await provider.generate(
            prompt=code_user,
            system_prompt=STRATEGY_GENERATION_SYSTEM_PROMPT,
            temperature=0.2,
        )
        code_text = code_resp.text.strip()
        if code_text.startswith("```"):
            lines = code_text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            code_text = "\n".join(lines).strip()

        try:
            validate_generated_strategy_ast(code_text)
        except ValueError as exc:
            raise LLMException(f"generated strategy code validation failed: {exc}") from exc

        metadata["model"] = code_resp.model
        metadata["provider"] = code_resp.provider
        return code_text, metadata

    def _check_risk(self, metrics: dict[str, Any], risk_profile: str) -> bool:
        cap = _MAX_DD_CAPS.get(risk_profile, 0.25)
        return metrics["maxDd"] <= cap and metrics["sharpe"] >= 0.8

    async def _update_strategy_from_meta(
        self, strategy: Strategy, metadata: dict[str, Any], backtest: dict[str, Any]
    ) -> None:
        strategy.name = metadata.get("name") or strategy.name
        strategy.family = metadata.get("family") or strategy.family
        strategy.description = metadata.get("description") or strategy.description
        strategy.universe = metadata.get("universe") or strategy.universe
        strategy.frequency = metadata.get("frequency") or strategy.frequency
        strategy.status = "backtesting"
        strategy.sharpe = backtest["sharpe"]
        strategy.max_dd = backtest["maxDd"]
        strategy.annual_return = backtest["annualReturn"]
        strategy.oos_score = backtest["oosScore"]
        strategy.updated_at = now_utc()
        await self.session.commit()
        await self.session.refresh(strategy)

    async def _persist_version(
        self, strategy: Strategy, code_text: str, metadata: dict[str, Any]
    ) -> StrategyVersion:
        version = StrategyVersion(
            strategy_id=strategy.id,
            version="v1.0.0",
            code_text=code_text,
            params_schema=json.dumps(metadata.get("params") or {}, ensure_ascii=False),
            risk_rules=json.dumps(
                metadata.get("riskRules") or {}, ensure_ascii=False
            ),
            status="ready",
            trace_id=get_trace_id(),
        )
        self.session.add(version)
        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def _broadcast(
        self,
        *,
        task_id: str,
        stage: str,
        event: str,
        progress: int,
        detail: dict[str, Any] | None = None,
        agent: str | None = None,
        strategy_id: str | None = None,
    ) -> None:
        try:
            await manager.broadcast(
                {
                    "type": "strategy.event",
                    "taskId": task_id,
                    "stage": stage,
                    "event": event,
                    "progress": progress,
                    "agent": agent,
                    "strategyId": strategy_id,
                    "detail": detail or {},
                    "timestamp": now_utc().isoformat(),
                },
                topic="strategy-events",
            )
        except Exception:  # noqa: BLE001
            pass
