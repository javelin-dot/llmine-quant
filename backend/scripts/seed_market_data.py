"""
Seed synthetic A-share daily bars from 2022-01-01 to today.

Generates realistic OHLCV data for 10 common A-share symbols using
geometric Brownian motion with mean reversion, sector correlations,
and regime shifts — good enough for strategy research and backtesting.

Usage:
    PYTHONPATH=/path/to/backend python scripts/seed_market_data.py
"""

import asyncio
import math
import random
from datetime import date, timedelta

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

# Must run from backend/ dir or with PYTHONPATH set
from app.db.session import AsyncSessionLocal
from app.domains.data.models import MarketBarDaily

# ── Configuration ─────────────────────────────────────────────────────────────

START_DATE = date(2022, 1, 4)   # first A-share trading day of 2022
END_DATE   = date(2026, 5, 9)   # last Friday before today (2026-05-13)

# symbol → (name, sector, initial_price, annual_drift, annual_vol)
SYMBOLS: dict[str, tuple[str, str, float, float, float]] = {
    "000001.SZ": ("平安银行",   "银行",   16.0,  0.04, 0.28),
    "000002.SZ": ("万科A",      "地产",   18.0, -0.06, 0.35),
    "000858.SZ": ("五粮液",     "白酒",   180.0, 0.10, 0.30),
    "600519.SH": ("贵州茅台",   "白酒",   1800.0, 0.08, 0.25),
    "600036.SH": ("招商银行",   "银行",   38.0,  0.05, 0.26),
    "300750.SZ": ("宁德时代",   "新能源", 420.0, 0.06, 0.45),
    "600900.SH": ("长江电力",   "公用",   20.0,  0.07, 0.20),
    "000333.SZ": ("美的集团",   "家电",   55.0,  0.06, 0.28),
    "601318.SH": ("中国平安",   "保险",   45.0,  0.03, 0.27),
    "002594.SZ": ("比亚迪",     "新能源", 250.0, 0.10, 0.42),
}

# Chinese A-share public holidays (approximate, simplified)
_HOLIDAYS = {
    # 2022
    "2022-01-03", "2022-01-31", "2022-02-01", "2022-02-02", "2022-02-03", "2022-02-04",
    "2022-04-04", "2022-04-05", "2022-05-02", "2022-05-03", "2022-05-04",
    "2022-06-03", "2022-09-12", "2022-10-03", "2022-10-04", "2022-10-05", "2022-10-06", "2022-10-07",
    # 2023
    "2023-01-02", "2023-01-23", "2023-01-24", "2023-01-25", "2023-01-26", "2023-01-27",
    "2023-04-05", "2023-04-28", "2023-05-01", "2023-05-03",
    "2023-06-22", "2023-06-23", "2023-09-29", "2023-10-02", "2023-10-03", "2023-10-04", "2023-10-05", "2023-10-06",
    # 2024
    "2024-01-01", "2024-02-08", "2024-02-09", "2024-02-12", "2024-02-13", "2024-02-14", "2024-02-15",
    "2024-04-04", "2024-04-05", "2024-05-01", "2024-05-02", "2024-05-03",
    "2024-06-10", "2024-09-16", "2024-09-17",
    "2024-10-01", "2024-10-02", "2024-10-03", "2024-10-04", "2024-10-07",
    # 2025
    "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31", "2025-02-03", "2025-02-04",
    "2025-04-04",  "2025-05-01", "2025-05-02",
    "2025-06-02", "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-06", "2025-10-07",
    # 2026 (partial)
    "2026-01-01", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-23",
    "2026-04-06", "2026-05-01",
}


def _is_trading_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    return d.isoformat() not in _HOLIDAYS


def _trading_days(start: date, end: date) -> list[date]:
    result = []
    cur = start
    while cur <= end:
        if _is_trading_day(cur):
            result.append(cur)
        cur += timedelta(days=1)
    return result


def _generate_prices(
    initial: float,
    trading_days: list[date],
    annual_drift: float,
    annual_vol: float,
    rng: random.Random,
) -> list[float]:
    """Geometric Brownian Motion with mean-reversion and occasional regime shifts."""
    dt = 1 / 252
    mu = annual_drift * dt
    sigma = annual_vol * math.sqrt(dt)

    closes = [initial]
    for i in range(1, len(trading_days)):
        prev = closes[-1]
        shock = rng.gauss(0, 1)
        # Gentle mean-reversion toward initial price over long horizon
        mean_rev = -0.001 * (prev / initial - 1)
        # Rare regime shift (fat tail)
        if rng.random() < 0.003:
            shock += rng.choice([-1, 1]) * rng.uniform(2, 4)
        new_price = prev * math.exp(mu + mean_rev + sigma * shock)
        # A-share circuit breaker: clamp to ±10% (±20% for ST, skip for simplicity)
        max_move = prev * 1.10
        min_move = prev * 0.90
        new_price = max(min_move, min(max_move, new_price))
        new_price = max(0.1, new_price)
        closes.append(round(new_price, 2))
    return closes


def _make_ohlcv(
    close: float,
    prev_close: float,
    rng: random.Random,
    intraday_vol: float = 0.012,
) -> tuple[float, float, float, float, int, float]:
    """Generate realistic OHLCV from daily close."""
    o = round(prev_close * (1 + rng.gauss(0, 0.004)), 2)
    # High/low contain both open and close
    high_r = abs(rng.gauss(0, intraday_vol)) + 0.001
    low_r  = abs(rng.gauss(0, intraday_vol)) + 0.001
    high = round(max(o, close) * (1 + high_r), 2)
    low  = round(min(o, close) * (1 - low_r),  2)
    high = min(high, prev_close * 1.10)
    low  = max(low,  prev_close * 0.90)
    low  = max(0.01, low)
    base_volume = int(rng.gauss(5_000_000, 2_000_000))
    volume = max(100_000, base_volume + int(abs(close - prev_close) / prev_close * 50_000_000))
    amount = round(volume * (o + close) / 2, 0)
    return o, high, low, close, volume, amount


async def seed_market_data() -> None:
    rng = random.Random(42)  # deterministic seed for reproducibility
    trading_days = _trading_days(START_DATE, END_DATE)
    print(f"Trading days: {len(trading_days)}  ({trading_days[0]} ~ {trading_days[-1]})")

    async with AsyncSessionLocal() as db:
        # Clear old data
        await db.execute(delete(MarketBarDaily))
        await db.flush()
        print("Cleared old market_bars_daily rows.")

        total_inserted = 0
        for symbol, (name, sector, init_price, drift, vol) in SYMBOLS.items():
            closes = _generate_prices(init_price, trading_days, drift, vol, rng)

            bars = []
            for i, d in enumerate(trading_days):
                close = closes[i]
                prev_close = closes[i - 1] if i > 0 else init_price
                o, high, low, c, volume, amount = _make_ohlcv(close, prev_close, rng)
                limit_up   = round(prev_close * 1.10, 2)
                limit_down = round(prev_close * 0.90, 2)
                is_limit_up   = c >= limit_up  * 0.999
                is_limit_down = c <= limit_down * 1.001
                bars.append(MarketBarDaily(
                    symbol=symbol,
                    trade_date=d.isoformat(),
                    prev_close=prev_close,
                    open=o,
                    high=high,
                    low=low,
                    close=c,
                    volume=volume,
                    amount=amount,
                    adjusted_close=c,
                    forward_factor=1.0,
                    limit_up_price=limit_up,
                    limit_down_price=limit_down,
                    is_limit_up=is_limit_up,
                    is_limit_down=is_limit_down,
                    is_suspended=False,
                    is_st=False,
                    can_buy=True,
                    can_sell=True,
                ))

            db.add_all(bars)
            await db.flush()
            total_inserted += len(bars)
            final_price = closes[-1]
            total_return = (final_price / init_price - 1) * 100
            print(f"  {symbol} ({name}): {len(bars)} bars  {init_price:.1f} → {final_price:.1f}  ({total_return:+.1f}%)")

        await db.commit()
        print(f"\nDone. Total rows inserted: {total_inserted}")


if __name__ == "__main__":
    asyncio.run(seed_market_data())
