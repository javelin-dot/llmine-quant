"""Error handling and custom exceptions."""

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger("errors")


class LLMineException(Exception):
    """Base exception for the application."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundException(LLMineException):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND, details=details)


class BadRequestException(LLMineException):
    """Bad request."""

    def __init__(self, message: str = "Bad request", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="BAD_REQUEST", status_code=status.HTTP_400_BAD_REQUEST, details=details)


class UnauthorizedException(LLMineException):
    """Unauthorized."""

    def __init__(self, message: str = "Unauthorized", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="UNAUTHORIZED", status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ForbiddenException(LLMineException):
    """Forbidden."""

    def __init__(self, message: str = "Forbidden", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN, details=details)


class ConflictException(LLMineException):
    """Resource conflict."""

    def __init__(self, message: str = "Conflict", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="CONFLICT", status_code=status.HTTP_409_CONFLICT, details=details)


class IdempotencyException(LLMineException):
    """Idempotency key conflict."""

    def __init__(self, message: str = "Idempotency key already used", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="IDEMPOTENCY_CONFLICT", status_code=status.HTTP_409_CONFLICT, details=details)


class LLMException(LLMineException):
    """LLM provider error — misconfiguration, network failure, parse error."""

    def __init__(self, message: str = "LLM request failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="LLM_ERROR", status_code=status.HTTP_502_BAD_GATEWAY, details=details)


async def handle_llmine_exception(request: Request, exc: LLMineException) -> JSONResponse:
    """Handle custom LLMine exceptions."""
    from app.core.tracing import get_trace_id

    trace_id = get_trace_id()
    logger.warning(
        "request_error",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        trace_id=trace_id,
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "trace_id": trace_id,
        },
    )


async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions."""
    from app.core.tracing import get_trace_id

    trace_id = get_trace_id()
    logger.exception(
        "unhandled_exception",
        trace_id=trace_id,
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred",
            "details": {},
            "trace_id": trace_id,
        },
    )
