"""全 A 股日线增量入库 (AKShare) - CLI 包装.

核心逻辑在 app.services.market_data_full_sync, 也供前端"实时行情同步"按钮共用.
本脚本是命令行入口, 不支持 --retry / --symbols-file 等子命令 (那些用历史脚本 import_market_data.py).

典型用法
--------
    python scripts/import_all_market.py --start 2020-01-01
    python scripts/import_all_market.py --boards main,star  # 仅主板 + 科创
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import date, timedelta

from app.services.market_data_full_sync import (
    FullSyncRequest,
    current_status,
    start_full_sync,
)


async def run(args: argparse.Namespace) -> int:
    boards = [b.strip() for b in args.boards.split(",")] if args.boards else []
    req = FullSyncRequest(
        start_date=args.start,
        end_date=args.end,
        adjust=args.adjust,
        concurrency=args.concurrency,
        boards=boards,
        incremental=args.incremental,
    )
    task_id = await start_full_sync(req)
    print(f"Started sync task: {task_id}")
    print(f"  range: {args.start} → {args.end}  adjust={args.adjust}  concurrency={args.concurrency}")
    if boards:
        print(f"  boards: {','.join(boards)}")

    # Poll progress
    last_done = -1
    while True:
        p = current_status()
        if p.phase == "scanning":
            print("scanning A-share spot snapshot …", flush=True)
        elif p.done != last_done or p.phase in ("completed", "failed", "st_flags"):
            elapsed = (p.eta_seconds or 0)
            print(
                f"[{p.phase:>10s}] {p.done:>5d}/{p.total}  "
                f"插入 {p.inserted_rows:>7d}  更新 {p.updated_rows:>7d}  "
                f"失败 {p.failures:>4d}  速率 {p.rate_per_sec:.2f}/s  "
                f"ETA {elapsed / 60:.1f}min",
                flush=True,
            )
            last_done = p.done
        if p.phase in ("completed", "failed"):
            break
        await asyncio.sleep(2)

    p = current_status()
    print()
    if p.phase == "failed":
        print(f"FAILED: {p.error}", file=sys.stderr)
        return 1
    print(f"完成 · 插入 {p.inserted_rows}  更新 {p.updated_rows}  失败 {p.failures}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    today = date.today().isoformat()
    five_y = (date.today() - timedelta(days=365 * 5)).isoformat()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default=five_y)
    p.add_argument("--end", default=today)
    p.add_argument("--adjust", default="qfq", choices=["qfq", "hfq", "none"])
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--boards", help="main,star,chinext,bse")
    p.add_argument(
        "--incremental",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return p


if __name__ == "__main__":
    started = time.monotonic()
    rc = asyncio.run(run(_build_parser().parse_args()))
    print(f"\nTotal wall: {(time.monotonic() - started) / 60:.1f} min")
    sys.exit(rc)
