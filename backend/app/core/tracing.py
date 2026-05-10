"""Request tracing and context management."""

import contextvars
import uuid

from fastapi import Request

_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
_actor_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("actor_id", default=None)
_org_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("org_id", default=None)


def get_trace_id() -> str:
    """Get current trace ID or generate a new one."""
    tid = _trace_id.get()
    return tid or _generate_trace_id()


def _generate_trace_id() -> str:
    """Generate a new trace ID."""
    return f"TRACE-{uuid.uuid4().hex[:12].upper()}"


def set_trace_id(tid: str) -> None:
    """Set the current trace ID."""
    _trace_id.set(tid)


def get_actor_id() -> str | None:
    """Get current actor ID."""
    return _actor_id.get()


def set_actor_id(actor_id: str) -> None:
    """Set the current actor ID."""
    _actor_id.set(actor_id)


def get_org_id() -> str | None:
    """Get current org ID."""
    return _org_id.get()


def set_org_id(org_id: str) -> None:
    """Set the current org ID."""
    _org_id.set(org_id)


async def tracing_middleware(request: Request, call_next):
    """FastAPI middleware to inject trace ID and actor context."""
    from app.core.logging import get_logger

    logger = get_logger("tracing")

    # Extract or generate trace ID
    tid = request.headers.get("X-Trace-ID") or _generate_trace_id()
    set_trace_id(tid)

    # Extract actor (simplified, will be from JWT in production)
    actor_id = request.headers.get("X-Actor-ID") or "system"
    set_actor_id(actor_id)

    org_id = request.headers.get("X-Org-ID")
    if org_id:
        set_org_id(org_id)

    logger.debug(
        "request_started",
        trace_id=tid,
        actor_id=actor_id,
        method=request.method,
        path=request.url.path,
    )

    response = await call_next(request)
    response.headers["X-Trace-ID"] = tid

    logger.debug(
        "request_completed",
        trace_id=tid,
        status_code=response.status_code,
        method=request.method,
        path=request.url.path,
    )

    return response
