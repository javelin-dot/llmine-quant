"""ProcessPool worker 用的最小 fetch 函数.

为什么单独成模块:
multiprocessing.spawn 启动 worker 时, 会 import worker 函数所在的 module.
如果放在 market_data_full_sync.py 里, worker 启动会被迫 import 整个
app.db / app.domains / SQLAlchemy engine, 启动慢 + 偶发 BrokenProcessPool
(导致 SZ 大量丢失). 本模块刻意保持极简, 只依赖 akshare.
"""

from __future__ import annotations

from typing import Any


def _to_sina_code(symbol: str) -> str:
    code, _, suffix = symbol.partition(".")
    return f"{suffix.lower()}{code}"


def fetch_one_history(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str,
) -> list[dict[str, Any]]:
    """走新浪 stock_zh_a_daily 拉单只历史日线; 失败抛异常给上层计 failures."""
    import akshare as ak

    adj = "" if adjust == "none" else adjust
    df = ak.stock_zh_a_daily(
        symbol=_to_sina_code(symbol),
        start_date=start_date.replace("-", ""),
        end_date=end_date.replace("-", ""),
        adjust=adj,
    )
    if df is None or getattr(df, "empty", False):
        return []
    rows: list[dict[str, Any]] = df.to_dict("records")
    for r in rows:
        r["symbol"] = symbol
        val = r.get("date")
        r["date"] = val.isoformat() if hasattr(val, "isoformat") else str(val)[:10]
    return rows
