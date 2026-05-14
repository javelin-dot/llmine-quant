"""Market quote API — historical bars, real-time snapshot, WebSocket stream."""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.core.websocket import manager
from app.integrations.market_data.factory import get_market_data_provider
from app.services.quote_stream import _TOPIC, quote_stream, quote_to_dict

router = APIRouter()
logger = get_logger("quotes_api")


# ── REST ───────────────────────────────────────────────────────────────

@router.get("/history")
async def get_history(
    symbol: str = Query(..., description="Symbol with market suffix, e.g. 000001.SZ"),
    start_date: str = Query(..., alias="startDate", description="YYYY-MM-DD"),
    end_date: str = Query(..., alias="endDate", description="YYYY-MM-DD"),
    freq: str = Query(default="1d", description="1d | 1w | 1m | 60min | 30min | 15min | 5min | 1min"),
    adjust: str = Query(default="qfq", description="qfq | hfq | none"),
):
    """Fetch historical OHLCV bars for one symbol."""
    provider = get_market_data_provider()
    result = await provider.get_history(symbol, start_date, end_date, freq, adjust)
    return {
        "symbol": result.symbol,
        "freq": result.freq,
        "adjust": result.adjust,
        "bars": [
            {
                "date": b.date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "amount": b.amount,
                "changePct": round(b.change_pct * 100, 4) if b.change_pct is not None else None,
            }
            for b in result.bars
        ],
        "count": len(result.bars),
    }


@router.get("/snapshot")
async def get_snapshot(
    symbols: str = Query(..., description="Comma-separated symbols, e.g. 000001.SZ,600519.SH"),
):
    """Real-time price snapshot for the requested symbols.

    Returns from in-memory cache when available (populated by background
    polling).  Falls through to a live provider call on cache miss.
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    cached = quote_stream.get_cached(symbol_list)
    if len(cached) == len(symbol_list):
        return {"quotes": [quote_to_dict(q) for q in cached], "source": "cache"}

    provider = get_market_data_provider()
    quotes = await provider.get_snapshot(symbol_list)
    return {"quotes": [quote_to_dict(q) for q in quotes], "source": "live"}


@router.get("/market")
async def get_market_snapshot():
    """Full market snapshot — all liquid A-share stocks.

    Serves from cache when the background poller has populated it;
    otherwise triggers a live fetch (may be slow on first call).
    """
    cached = quote_stream.get_all_cached()
    if cached:
        return {"quotes": [quote_to_dict(q) for q in cached], "count": len(cached), "source": "cache"}

    provider = get_market_data_provider()
    quotes = await provider.get_market_snapshot()
    return {"quotes": [quote_to_dict(q) for q in quotes], "count": len(quotes), "source": "live"}


# ── WebSocket ──────────────────────────────────────────────────────────

@router.websocket("/ws")
async def quote_ws(websocket: WebSocket) -> None:
    """Real-time quote push over WebSocket.

    Client → server messages:
      {"action": "subscribe",   "symbols": ["000001.SZ", "600519.SH"]}
      {"action": "unsubscribe", "symbols": ["000001.SZ"]}
      {"action": "ping"}

    Server → client messages:
      {"type": "snapshot", "data": [...]}   — cached quotes on subscribe
      {"type": "quotes",   "data": [...], "ts": <ms>}  — periodic push
      {"type": "pong"}
    """
    await manager.connect(websocket, topic=_TOPIC)
    try:
        while True:
            msg = await websocket.receive_json()
            action = msg.get("action")

            if action == "subscribe":
                symbols: list[str] = msg.get("symbols", [])
                quote_stream.subscribe(websocket, symbols)
                cached = quote_stream.get_cached(symbols)
                if cached:
                    await manager.send_personal(
                        {"type": "snapshot", "data": [quote_to_dict(q) for q in cached]},
                        websocket,
                    )

            elif action == "unsubscribe":
                symbols_unsub: list[str] = msg.get("symbols", [])
                quote_stream.unsubscribe(websocket, symbols_unsub or None)

            elif action == "ping":
                await manager.send_personal({"type": "pong"}, websocket)

    except WebSocketDisconnect:
        quote_stream.unsubscribe(websocket)
        manager.disconnect(websocket, topic=_TOPIC)
    except Exception as exc:  # noqa: BLE001
        logger.warning("quote_ws_error", error=str(exc))
        quote_stream.unsubscribe(websocket)
        manager.disconnect(websocket, topic=_TOPIC)
