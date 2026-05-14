"""Market data provider abstract base + shared data models.

Mirrors the LLMProvider pattern: one ABC, multiple concrete providers.
Add a new provider by subclassing MarketDataProvider and registering it
in factory.py — no other files need to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone


# ── Data models ────────────────────────────────────────────────────────

@dataclass
class Quote:
    """Real-time price snapshot for one instrument."""

    symbol: str           # "000001.SZ" / "600519.SH"
    name: str
    price: float
    change: float         # absolute price change vs prev_close
    change_pct: float     # decimal fraction  (0.03 = +3%)
    volume: int           # shares traded today
    amount: float         # notional traded today (CNY)
    high: float
    low: float
    open: float
    prev_close: float
    turnover_rate: float | None = None   # 换手率 as decimal
    pe_ratio: float | None = None        # 市盈率-动态
    market_cap: float | None = None      # 总市值 (CNY)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OHLCV:
    """One historical price bar."""

    date: str           # "2024-01-15"
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: float | None = None   # decimal fraction


@dataclass
class HistoryResult:
    """Historical bars for one symbol."""

    symbol: str
    freq: str     # "1d" | "1w" | "1m" | "60min" | "30min" | "15min" | "5min" | "1min"
    adjust: str   # "qfq" | "hfq" | "none"
    bars: list[OHLCV]


# ── Provider ABC ───────────────────────────────────────────────────────

class MarketDataProvider(ABC):
    """Abstract provider for historical and quasi-real-time A-share data.

    All methods are async; sync data sources (e.g. AKShare) must wrap
    blocking calls in asyncio.to_thread().
    """

    name: str = "abstract"
    supports_realtime: bool = True
    supports_intraday: bool = False   # sub-daily kline

    @abstractmethod
    async def get_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        freq: str = "1d",
        adjust: str = "qfq",
    ) -> HistoryResult:
        """Fetch historical OHLCV bars.

        Args:
            symbol:     Instrument code with market suffix, e.g. "000001.SZ".
            start_date: Inclusive start, "YYYY-MM-DD".
            end_date:   Inclusive end,   "YYYY-MM-DD".
            freq:       Bar frequency — "1d" (daily, default), "1w", "1m".
            adjust:     Price adjustment — "qfq" (前复权), "hfq" (后复权), "none".
        """

    @abstractmethod
    async def get_snapshot(self, symbols: list[str]) -> list[Quote]:
        """Real-time price snapshot for the requested symbols."""

    @abstractmethod
    async def get_market_snapshot(self) -> list[Quote]:
        """Full A-share market snapshot — all actively traded stocks."""

    # ── Utility ────────────────────────────────────────────────────────

    @staticmethod
    def is_trading_hours() -> bool:
        """True if current wall-clock time is inside A-share trading hours (CST)."""
        cst = timezone(timedelta(hours=8))
        now = datetime.now(cst)
        if now.weekday() >= 5:
            return False
        t = now.time()
        return time(9, 30) <= t <= time(11, 30) or time(13, 0) <= t <= time(15, 0)
