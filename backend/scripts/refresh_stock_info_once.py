"""一次性脚本: 从 AKShare 拉一次全 A 股快照, UPSERT 进 stock_info 表.

用法 (在 backend 目录下):
    python scripts/refresh_stock_info_once.py
"""

from __future__ import annotations

import asyncio
import sys
import traceback


async def main() -> int:
    from app.services.market_data_full_sync import (
        _fetch_market_symbols,
        upsert_stock_info,
    )

    print("[1/2] AKShare stock_zh_a_spot 拉取...", flush=True)
    scan = await _fetch_market_symbols()
    print(f"      拿到 {len(scan)} 条 (symbol, name, is_st)", flush=True)
    if scan:
        sample = scan[:3]
        print(f"      样例: {sample}", flush=True)

    print("[2/2] UPSERT 进 stock_info ...", flush=True)
    n = await upsert_stock_info(scan)
    print(f"      已写入 {n} 行", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
