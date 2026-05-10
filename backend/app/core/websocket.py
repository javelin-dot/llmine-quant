"""WebSocket connection manager for real-time event broadcast."""

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger("websocket")


class ConnectionManager:
    """Manage WebSocket connections with topic-based subscription."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic: str = "broadcast") -> None:
        await websocket.accept()
        self._connections.setdefault(topic, []).append(websocket)
        logger.info("ws_connected", topic=topic, connections=len(self._connections.get(topic, [])))

    def disconnect(self, websocket: WebSocket, topic: str = "broadcast") -> None:
        conns = self._connections.get(topic, [])
        if websocket in conns:
            conns.remove(websocket)
        logger.info("ws_disconnected", topic=topic, connections=len(conns))

    async def broadcast(self, message: dict, topic: str = "broadcast") -> None:
        """Broadcast a message to all connections on a topic."""
        conns = self._connections.get(topic, [])
        for conn in list(conns):
            try:
                await conn.send_json(message)
            except Exception:
                conns.remove(conn)

    async def send_personal(self, message: dict, websocket: WebSocket) -> None:
        """Send a message to a single connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass


manager = ConnectionManager()
