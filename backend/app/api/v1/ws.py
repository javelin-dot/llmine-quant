"""WebSocket API — real-time event stream."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.core.websocket import manager

router = APIRouter()
logger = get_logger("ws_api")


@router.websocket("/events")
async def event_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for general real-time events."""
    await manager.connect(websocket, topic="events")
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal({"type": "pong", "echo": data}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, topic="events")
    except Exception as e:
        logger.warning("ws_error", error=str(e))
        manager.disconnect(websocket, topic="events")


@router.websocket("/strategy-events")
async def strategy_event_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for strategy pipeline events."""
    await manager.connect(websocket, topic="strategy-events")
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal({"type": "pong", "echo": data}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, topic="strategy-events")
    except Exception as e:
        logger.warning("ws_error", error=str(e))
        manager.disconnect(websocket, topic="strategy-events")
