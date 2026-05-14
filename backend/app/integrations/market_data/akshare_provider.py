"""AKShare market data provider — free, no registration required.

AKShare is a synchronous library; all blocking calls are offloaded to
asyncio.to_thread() so they don't stall the event loop.

Install: pip install akshare
Docs:    https://akshare.akfamily.xyz/

Real-time quote strategy
------------------------
- get_snapshot(symbols)     → Sina Finance hq.sinajs.cn batch API (one HTTP
                              request, ~50ms for 50 symbols; used by the
                              background polling loop for subscribed symbols)
- get_market_snapshot()     → akshare stock_zh_a_spot (Sina Finance paginated
                              scan of all 5000+ stocks; used for /market endpoint
                              and initial cache warm-up; takes ~20s)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from functools import partial

import pandas as pd
import requests as _requests

from .base import OHLCV, HistoryResult, MarketDataProvider, Quote

# ── Symbol helpers ─────────────────────────────────────────────────────

_FREQ_MAP: dict[str, str] = {
    "1d": "daily",
    "1w": "weekly",
    "1m": "monthly",
    "60min": "60",
    "30min": "30",
    "15min": "15",
    "5min":  "5",
    "1min":  "1",
}

_SINA_HEADERS = {
    "Referer": "http://finance.sina.com.cn",
    "User-Agent": "Mozilla/5.0",
}


def _strip_suffix(symbol: str) -> str:
    """'000001.SZ' → '000001'"""
    return symbol.split(".")[0]


def _to_standard(code: str) -> str:
    """Guess full symbol from bare code: '000001' → '000001.SZ'."""
    if "." in code:
        return code
    return f"{code}.SH" if code.startswith(("6", "9", "5")) else f"{code}.SZ"


def _to_sina_code(symbol: str) -> str:
    """'000001.SZ' → 'sz000001', '600519.SH' → 'sh600519'"""
    if "." in symbol:
        code, mkt = symbol.rsplit(".", 1)
        return f"{mkt.lower()}{code}"
    # Bare code — guess market
    return ("sh" if symbol.startswith(("6", "9", "5")) else "sz") + symbol


def _safe_float(val, default: float = 0.0) -> float:
    try:
        v = float(val)
        return v if pd.notna(v) and v == v else default
    except (TypeError, ValueError):
        return default


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ── Sina Finance batch quote ───────────────────────────────────────────

def _sina_batch_quote_sync(symbols: list[str]) -> list[Quote]:
    """Single HTTP request to hq.sinajs.cn for the given symbols.

    Returns one Quote per successfully parsed symbol.
    Typical latency: 30–80 ms for ≤100 symbols (no pagination).
    """
    sina_codes = [_to_sina_code(s) for s in symbols]
    url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
    try:
        resp = _requests.get(url, headers=_SINA_HEADERS, timeout=8)
        resp.encoding = "gbk"
        text = resp.text
    except Exception:  # noqa: BLE001
        return []

    quotes: list[Quote] = []
    for line in text.splitlines():
        # var hq_str_sh600519="贵州茅台,1750.00,1782.01,1751.99,1764.52,1749.58,...";
        if '="' not in line or line.strip().endswith('="";'):
            continue
        try:
            header, rest = line.split('="', 1)
            fields_str = rest.rstrip('";')
            fields = fields_str.split(",")
            if len(fields) < 10:
                continue
            # Decode sina code back to standard symbol
            sina_code = header.split("hq_str_")[-1]  # e.g. "sz000001"
            mkt = sina_code[:2].upper()   # "SZ" / "SH"
            code = sina_code[2:]          # "000001"
            symbol = f"{code}.{mkt}"

            price = _safe_float(fields[3])
            if price <= 0:
                continue
            prev_close = _safe_float(fields[2])
            quotes.append(Quote(
                symbol=symbol,
                name=fields[0],
                price=price,
                change=round(price - prev_close, 4),
                change_pct=(price - prev_close) / prev_close if prev_close else 0.0,
                volume=_safe_int(fields[8]),
                amount=_safe_float(fields[9]),
                high=_safe_float(fields[4]),
                low=_safe_float(fields[5]),
                open=_safe_float(fields[1]),
                prev_close=prev_close,
                timestamp=datetime.now(),
            ))
        except Exception:  # noqa: BLE001
            continue

    return quotes


# ── Provider ───────────────────────────────────────────────────────────

class AKShareProvider(MarketDataProvider):
    """Free market data via AKShare + Sina Finance hq API."""

    name = "akshare"
    supports_realtime = True
    supports_intraday = True

    async def get_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        freq: str = "1d",
        adjust: str = "qfq",
    ) -> HistoryResult:
        """Fetch daily/weekly/monthly OHLCV via akshare stock_zh_a_daily (Sina Finance).

        Uses Sina Finance as data source — does NOT hit eastmoney, which can return
        503 errors due to anti-scraping protection.  Sub-daily frequencies are not
        supported by this source; pass freq="1d"/"1w"/"1m" only.
        """
        import akshare as ak  # imported here so app starts without akshare installed

        # stock_zh_a_daily expects "sz000001" / "sh600519" format
        sina_symbol = _to_sina_code(symbol)
        start = start_date.replace("-", "")
        end = end_date.replace("-", "")
        adj = "" if adjust == "none" else adjust

        fn = partial(
            ak.stock_zh_a_daily,
            symbol=sina_symbol,
            start_date=start,
            end_date=end,
            adjust=adj,
        )
        df: pd.DataFrame = await asyncio.to_thread(fn)
        if df is None or df.empty:
            return HistoryResult(symbol=symbol, freq=freq, adjust=adjust, bars=[])

        # Compute change_pct from close prices (column not provided by this API)
        closes = df["close"].tolist()
        prev_closes = [None] + closes[:-1]

        bars: list[OHLCV] = []
        for (_, row), prev_c in zip(df.iterrows(), prev_closes):
            date_val = str(row.get("date", ""))
            chg = (row["close"] - prev_c) / prev_c if prev_c else 0.0
            bars.append(OHLCV(
                date=date_val,
                open=_safe_float(row.get("open")),
                high=_safe_float(row.get("high")),
                low=_safe_float(row.get("low")),
                close=_safe_float(row.get("close")),
                volume=_safe_int(row.get("volume")),
                amount=_safe_float(row.get("amount")),
                change_pct=round(chg, 6),
            ))

        return HistoryResult(symbol=symbol, freq=freq, adjust=adjust, bars=bars)

    async def get_snapshot(self, symbols: list[str]) -> list[Quote]:
        """Fast batch fetch via Sina Finance hq API — one request regardless of symbol count."""
        if not symbols:
            return []
        return await asyncio.to_thread(_sina_batch_quote_sync, symbols)

    async def get_market_snapshot(self) -> list[Quote]:
        """Full A-share market scan via akshare stock_zh_a_spot (Sina Finance paginated).

        Takes ~20s for ~5500 stocks. Use for initial warm-up and /market endpoint;
        do NOT call this in the tight polling loop — use get_snapshot(subscribed) instead.
        """
        import akshare as ak

        df: pd.DataFrame = await asyncio.to_thread(ak.stock_zh_a_spot)
        if df is None or df.empty:
            return []

        quotes: list[Quote] = []
        for _, row in df.iterrows():
            try:
                code = str(row.get("代码", "")).strip()
                if not code:
                    continue
                # Sina Finance codes look like "bj920000" or "sz000001"
                mkt_prefix = code[:2].lower()
                bare_code = code[2:]
                if mkt_prefix == "bj":
                    symbol = f"{bare_code}.BJ"
                elif mkt_prefix == "sh":
                    symbol = f"{bare_code}.SH"
                else:
                    symbol = f"{bare_code}.SZ"

                price = _safe_float(row.get("最新价"))
                if price <= 0:
                    continue
                prev_close = _safe_float(row.get("昨收"), price)
                quotes.append(Quote(
                    symbol=symbol,
                    name=str(row.get("名称", "")),
                    price=price,
                    change=_safe_float(row.get("涨跌额")),
                    change_pct=_safe_float(row.get("涨跌幅")) / 100,
                    volume=_safe_int(row.get("成交量")),
                    amount=_safe_float(row.get("成交额")),
                    high=_safe_float(row.get("最高"), price),
                    low=_safe_float(row.get("最低"), price),
                    open=_safe_float(row.get("今开"), price),
                    prev_close=prev_close,
                    timestamp=datetime.now(),
                ))
            except Exception:  # noqa: BLE001
                continue

        return quotes
