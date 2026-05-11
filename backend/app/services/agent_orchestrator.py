"""Agent orchestrator — dispatches tasks and messages across the agent fleet."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tracing import get_trace_id
from app.db.base_class import now_utc
from app.domains.agents.models import AgentMessage, AgentRegistry, AgentTask


class AgentOrchestrator:
    """Wraps AgentTask / AgentMessage persistence with role resolution."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _agent_id_for_role(self, role: str) -> str | None:
        """Return the first matching agent id for a role."""
        result = await self.session.execute(
            select(AgentRegistry.id)
            .where(AgentRegistry.role == role)
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None

    async def dispatch(
        self,
        *,
        agent_role: str,
        task_type: str,
        payload: dict,
        priority: int = 0,
        correlation_id: str | None = None,
    ) -> AgentTask:
        """Persist a new AgentTask for the agent with the given role."""
        agent_id = await self._agent_id_for_role(agent_role) or agent_role

        task = AgentTask(
            agent_id=agent_id,
            task_type=task_type,
            payload_json=json.dumps(payload, ensure_ascii=False),
            priority=priority,
            status="running",
            started_at=now_utc().isoformat(),
            trace_id=get_trace_id(),
        )
        if correlation_id:
            task.metadata_json = json.dumps(
                {"correlation_id": correlation_id}, ensure_ascii=False
            )

        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def complete_task(
        self,
        task_id: str,
        *,
        result: dict | None = None,
        status: str = "succeeded",
    ) -> AgentTask | None:
        """Mark an AgentTask completed and stash its result."""
        task = await self.session.get(AgentTask, task_id)
        if task is None:
            return None
        task.status = status
        if result is not None:
            task.result_json = json.dumps(result, ensure_ascii=False)
        task.completed_at = now_utc().isoformat()
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def send_message(
        self,
        *,
        from_agent: str,
        to_agent: str | None,
        topic: str,
        payload: dict,
        correlation_id: str | None = None,
        msg_type: str = "event",
    ) -> AgentMessage:
        """Append a single agent-to-agent message."""
        message = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            msg_type=msg_type,
            topic=topic,
            payload_json=json.dumps(payload, ensure_ascii=False),
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message
