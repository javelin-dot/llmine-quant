"""Mock market data provider — deterministic, no network calls.

Used automatically when no real provider is installed or configured.
Generates realistic synthetic A-share price movement for a fixed set
of blue-chip stocks so that UI / integration tests always have data.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from .base import OHLCV, HistoryResult, MarketDataProvider, Quote

_STOCKS: list[tuple[str, str, float]] = [
    ("000001.SZ", "平安银行",  12.5),
    ("000002.SZ", "万科A",      7.2),
    ("000858.SZ", "五粮液",   158.0),
    ("000333.SZ", "美的集团",  52.3),
    ("000725.SZ", "京东方A",    4.3),
    ("600519.SH", "贵州茅台", 1780.0),
    ("601318.SH", "中国平安",  42.8),
    ("600036.SH", "招商银行",  34.5),
    ("600276.SH", "恒瑞医药",  28.1),
    ("601166.SH", "兴业银行",  18.7),
]


class MockMarketDataProvider(MarketDataProvider):
    """Deterministic mock — no external dependencies."""

    name = "mock"
    supports_realtime = True
    supports_intraday = True

    def __init__(self) -> None:
        # Seeded per-symbol price state so drift accumulates across calls
        self._prices: dict[str, float] = {s: p for s, _, p in _STOCKS}

    async def get_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        freq: str = "1d",
        adjust: str = "qfq",
    ) -> HistoryResult:
        base = next((p for s, _, p in _STOCKS if s == symbol), 50.0)
        rng = random.Random(symbol)   # deterministic per symbol
        price = base * 0.8

        bars: list[OHLCV] = []
        d = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        while d <= end:
            if d.weekday() < 5:  # skip weekends
                chg = rng.gauss(0.0002, 0.014)
                o = price * (1 + rng.gauss(0, 0.002))
                h = max(o, price * (1 + abs(rng.gauss(0, 0.007))))
                l = min(o, price * (1 - abs(rng.gauss(0, 0.007))))
                c = price * (1 + chg)
                vol = int(rng.uniform(5e5, 3e7))
                bars.append(OHLCV(
                    date=d.strftime("%Y-%m-%d"),
                    open=round(o, 2),
                    high=round(h, 2),
                    low=round(l, 2),
                    close=round(c, 2),
                    volume=vol,
                    amount=round(c * vol, 2),
                    change_pct=round(chg, 6),
                ))
                price = c
            d += timedelta(days=1)

        return HistoryResult(symbol=symbol, freq=freq, adjust=adjust, bars=bars)

    async def get_snapshot(self, symbols: list[str]) -> list[Quote]:
        sym_set = set(symbols)
        all_q = await self.get_market_snapshot()
        return [q for q in all_q if q.symbol in sym_set]

    async def get_market_snapshot(self) -> list[Quote]:
        quotes: list[Quote] = []
        for symbol, name, _ in _STOCKS:
            drift = random.gauss(0, 0.004)
            self._prices[symbol] *= 1 + drift
            price = round(self._prices[symbol], 2)
            prev = round(price / (1 + drift), 2)
            change = round(price - prev, 2)
            quotes.append(Quote(
                symbol=symbol,
                name=name,
                price=price,
                change=change,
                change_pct=round(drift, 6),
                volume=random.randint(1_000_000, 50_000_000),
                amount=round(price * random.uniform(1e6, 5e7), 2),
                high=round(price * (1 + abs(random.gauss(0, 0.005))), 2),
                low=round(price * (1 - abs(random.gauss(0, 0.005))), 2),
                open=round(prev * (1 + random.gauss(0, 0.002)), 2),
                prev_close=prev,
                turnover_rate=random.uniform(0.005, 0.05),
                pe_ratio=random.uniform(10.0, 50.0),
                market_cap=price * random.uniform(5e9, 5e12),
                timestamp=datetime.now(),
            ))
        return quotes
