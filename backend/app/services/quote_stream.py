"""Background quote polling + WebSocket broadcast service.

Design
------
- Only symbols that at least one WebSocket client has subscribed to are
  fetched from the provider.  Full-market scans are avoided in the loop.
- The provider's get_snapshot(symbols) uses Sina Finance's hq.sinajs.cn
  batch API — one HTTP request, ~50ms for the typical 10-50 symbol universe.
- Poll interval: settings.market_data_poll_interval (default 3s) during
  trading hours; 30s outside to avoid pointless calls.

Lifecycle
---------
  quote_stream.start()   → called in FastAPI lifespan on startup
  quote_stream.stop()    → called in FastAPI lifespan on shutdown

WebSocket clients receive
--------------------------
  {"type": "quotes",   "data": [...], "ts": <ms epoch>}  — on price change
  {"type": "snapshot", "data": [...]}                     — on subscribe (from cache)
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime

from fastapi import WebSocket

from app.core.config import settings
from app.core.logging import get_logger
from app.core.websocket import manager
from app.integrations.market_data.base import MarketDataProvider, Quote
from app.integrations.market_data.factory import get_market_data_provider

logger = get_logger("quote_stream")

_TOPIC = "quotes"


def quote_to_dict(q: Quote) -> dict:
    return {
        "symbol": q.symbol,
        "name": q.name,
        "price": q.price,
        "change": q.change,
        "changePct": round(q.change_pct * 100, 4),
        "volume": q.volume,
        "amount": q.amount,
        "high": q.high,
        "low": q.low,
        "open": q.open,
        "prevClose": q.prev_close,
        "turnoverRate": round(q.turnover_rate * 100, 4) if q.turnover_rate is not None else None,
        "peRatio": q.pe_ratio,
        "marketCap": q.market_cap,
        "ts": int(q.timestamp.timestamp() * 1000),
    }


class QuoteStreamService:
    """Singleton background service: subscribe → poll subscribed symbols → broadcast."""

    def __init__(self) -> None:
        self._cache: dict[str, Quote] = {}
        self._subscriptions: dict[int, set[str]] = defaultdict(set)  # ws_id → symbols
        self._task: asyncio.Task | None = None
        self._provider: MarketDataProvider | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self) -> None:
        self._provider = get_market_data_provider()
        self._task = asyncio.create_task(self._loop(), name="quote_stream")
        logger.info("quote_stream_started", provider=self._provider.name)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        logger.info("quote_stream_stopped")

    # ── Subscription management ────────────────────────────────────────

    def subscribe(self, ws: WebSocket, symbols: list[str]) -> None:
        self._subscriptions[id(ws)].update(symbols)

    def unsubscribe(self, ws: WebSocket, symbols: list[str] | None = None) -> None:
        ws_id = id(ws)
        if symbols is None:
            self._subscriptions.pop(ws_id, None)
        else:
            self._subscriptions[ws_id].difference_update(symbols)

    def _all_subscribed(self) -> set[str]:
        result: set[str] = set()
        for syms in self._subscriptions.values():
            result.update(syms)
        return result

    # ── Cache access (for REST snapshot endpoint) ──────────────────────

    def get_cached(self, symbols: list[str]) -> list[Quote]:
        return [self._cache[s] for s in symbols if s in self._cache]

    def get_all_cached(self) -> list[Quote]:
        return list(self._cache.values())

    # ── Background loop ────────────────────────────────────────────────

    async def _loop(self) -> None:
        while True:
            try:
                await self._poll()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning("quote_poll_error", error=str(exc))

            is_trading = MarketDataProvider.is_trading_hours()
            interval = settings.market_data_poll_interval if is_trading else 30
            await asyncio.sleep(interval)

    async def _poll(self) -> None:
        if self._provider is None:
            return

        watched = self._all_subscribed()
        if not watched:
            return  # no subscribers — skip network call

        quotes = await self._provider.get_snapshot(list(watched))

        changed: list[dict] = []
        for q in quotes:
            prev = self._cache.get(q.symbol)
            if prev is None or prev.price != q.price:
                self._cache[q.symbol] = q
                changed.append(quote_to_dict(q))

        if changed:
            await manager.broadcast(
                {"type": "quotes", "data": changed, "ts": int(datetime.now().timestamp() * 1000)},
                topic=_TOPIC,
            )
            logger.debug("quotes_broadcast", updated=len(changed), watched=len(watched))


# Module-level singleton used by API endpoints and lifespan handler
quote_stream = QuoteStreamService()
