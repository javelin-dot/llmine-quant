"""Strategy generation service — NL -> code -> backtest pipeline orchestration."""

from __future__ import annotations

import ast
import json
import random
import uuid
from typing import Any

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
from app.integrations.llm import get_llm_provider
from app.integrations.llm.prompts import (
    STRATEGY_GENERATION_SYSTEM_PROMPT,
    STRATEGY_GENERATION_USER_PROMPT,
    STRATEGY_METADATA_SYSTEM_PROMPT,
    STRATEGY_METADATA_USER_PROMPT,
)
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.audit_service import AuditService


_METADATA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "family": {"type": "string"},
        "description": {"type": "string"},
        "universe": {"type": "string"},
        "frequency": {"type": "string"},
        "expected_sharpe": {"type": "number"},
        "expected_max_dd": {"type": "number"},
    },
    "required": [
        "name",
        "family",
        "description",
        "universe",
        "frequency",
        "expected_sharpe",
        "expected_max_dd",
    ],
}

_MAX_DD_CAPS = {"conservative": 0.12, "balanced": 0.20, "aggressive": 0.35}


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

            # 3. static check
            try:
                ast.parse(code_text)
            except SyntaxError as exc:
                raise LLMException(f"LLM produced invalid python: {exc}") from exc
            await self._stage(
                task=task,
                stage="static_check",
                agent_role="strategy",
                event="code.static_check_passed",
                progress=50,
                detail={"checks": ["ast.parse"]},
                correlation_id=correlation_id,
            )

            # 4. backtest (mock)
            backtest = self._mock_backtest(task.id, task.market, task.risk_profile)
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
        provider = get_llm_provider()
        user_prompt = STRATEGY_GENERATION_USER_PROMPT.format(
            market=task.market,
            risk_profile=task.risk_profile,
            prompt=task.prompt,
        )
        code_resp = await provider.generate(
            prompt=user_prompt,
            system_prompt=STRATEGY_GENERATION_SYSTEM_PROMPT,
            temperature=0.2,
        )
        code_text = code_resp.text.strip()
        # Strip markdown fences if present
        if code_text.startswith("```"):
            lines = code_text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            code_text = "\n".join(lines).strip()

        try:
            meta = await provider.generate_structured(
                prompt=STRATEGY_METADATA_USER_PROMPT.format(
                    market=task.market,
                    risk_profile=task.risk_profile,
                    prompt=task.prompt,
                ),
                output_schema=_METADATA_SCHEMA,
                system_prompt=STRATEGY_METADATA_SYSTEM_PROMPT,
                temperature=0.2,
            )
        except Exception:  # noqa: BLE001
            meta = {}

        meta.setdefault("model", code_resp.model)
        meta.setdefault("provider", code_resp.provider)
        return code_text, meta

    def _mock_backtest(
        self, task_id: str, market: str, risk_profile: str
    ) -> dict[str, Any]:
        """Deterministic mock backtest keyed on task id."""
        rng = random.Random(f"{task_id}:{market}:{risk_profile}")
        sharpe = round(1.2 + rng.random() * 0.9, 2)
        max_dd = round(0.08 + rng.random() * 0.10, 3)
        annual = round(0.12 + rng.random() * 0.18, 3)
        oos = round(0.55 + rng.random() * 0.25, 2)
        confidence = round(min(1.0, sharpe / 2.5), 2)
        return {
            "sharpe": sharpe,
            "maxDd": max_dd,
            "annualReturn": annual,
            "oosScore": oos,
            "confidence": confidence,
        }

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
