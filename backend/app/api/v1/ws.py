"""WebSocket API — real-time event stream."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.core.websocket import manager

router = APIRouter()
logger = get_logger("ws_api")


def _make_ws_handler(topic: str):
    async def handler(websocket: WebSocket) -> None:
        await manager.connect(websocket, topic=topic)
        try:
            while True:
                data = await websocket.receive_text()
                await manager.send_personal({"type": "pong", "echo": data}, websocket)
        except WebSocketDisconnect:
            manager.disconnect(websocket, topic=topic)
        except Exception as e:
            logger.warning("ws_error", topic=topic, error=str(e))
            manager.disconnect(websocket, topic=topic)
    handler.__name__ = f"ws_{topic.replace('-', '_')}"
    return handler


@router.websocket("/events")
async def event_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for general real-time events."""
    await _make_ws_handler("events")(websocket)


@router.websocket("/strategy-events")
async def strategy_event_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for strategy pipeline events."""
    await _make_ws_handler("strategy-events")(websocket)


@router.websocket("/execution-events")
async def execution_event_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for execution approval events."""
    await _make_ws_handler("execution-events")(websocket)


@router.websocket("/risk-events")
async def risk_event_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for risk / circuit breaker events."""
    await _make_ws_handler("risk-events")(websocket)
