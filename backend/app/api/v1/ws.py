"""WebSocket API — real-time event stream."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.core.websocket import manager

router = APIRouter()
logger = get_logger("ws_api")


@router.websocket("/events")
async def event_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time events.

    Clients receive broadcasts for:
    - trade_signals: new buy/sell signals
    - risk_alerts: risk threshold breaches
    - order_updates: order fill/partial/reject status
    - system_health: periodic health heartbeat
    """
    await manager.connect(websocket, topic="events")
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/heartbeat, or handle client commands
            await manager.send_personal({"type": "pong", "echo": data}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, topic="events")
    except Exception as e:
        logger.warning("ws_error", error=str(e))
        manager.disconnect(websocket, topic="events")
