"""全 A 股日线行情同步 service.

首次空库 = 全量, 之后按 max(trade_date) 增量. 同一时刻仅允许一个任务,
进度由 module-level singleton state 暴露给 API 轮询.

子进程 fetch 走新浪 stock_zh_a_daily (mini_racer V8 非线程安全, 必须 process pool).
"""

from __future__ import annotations

import asyncio
import importlib
import time
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.session import AsyncSessionLocal
from app.domains.data.models import MarketBarDaily, StockInfo
from app.services._market_fetch_worker import fetch_one_history as _fetch_one_sync
from app.services.market_data_import import MarketDataImportService

SyncPhase = Literal["idle", "scanning", "syncing", "retrying", "st_flags", "completed", "failed"]


# ── Symbol helpers ────────────────────────────────────────────────────

def _sina_to_standard(sina_code: str) -> str:
    mkt = sina_code[:2].lower()
    code = sina_code[2:]
    if mkt == "bj":
        return f"{code}.BJ"
    if mkt == "sh":
        return f"{code}.SH"
    return f"{code}.SZ"


def _to_sina_code(symbol: str) -> str:
    code, _, suffix = symbol.partition(".")
    return f"{suffix.lower()}{code}"


def _board_for(symbol: str) -> str:
    code, _, suffix = symbol.partition(".")
    if suffix.upper() == "BJ":
        return "bse"
    if code.startswith("688"):
        return "star"
    if code.startswith(("300", "301")):
        return "chinext"
    return "main"


# ── Dataclasses ────────────────────────────────────────────────────────

@dataclass(slots=True)
class SymbolMeta:
    symbol: str
    name: str
    is_st: bool
    start: str
    end: str


@dataclass(slots=True)
class FullSyncRequest:
    start_date: str
    end_date: str
    adjust: str = "qfq"
    concurrency: int = 8
    boards: list[str] = field(default_factory=list)
    incremental: bool = True


@dataclass(slots=True)
class FullSyncProgress:
    task_id: str | None = None
    phase: SyncPhase = "idle"
    started_at: str | None = None
    finished_at: str | None = None
    total: int = 0
    done: int = 0
    skipped: int = 0
    inserted_rows: int = 0
    updated_rows: int = 0
    failures: int = 0
    rate_per_sec: float = 0.0
    eta_seconds: float | None = None
    last_symbol: str | None = None
    error: str | None = None

    @property
    def is_running(self) -> bool:
        return self.phase in ("scanning", "syncing", "st_flags")


# ── Helpers (DB) ──────────────────────────────────────────────────────

async def _fetch_market_symbols() -> list[tuple[str, str, bool]]:
    # uvicorn 启动后 pip install 装的新包需要 invalidate_caches 才能被 importlib 看到
    importlib.invalidate_caches()
    ak = importlib.import_module("akshare")
    df = await asyncio.to_thread(ak.stock_zh_a_spot)
    if df is None or df.empty:
        raise RuntimeError("AKShare stock_zh_a_spot returned empty")
    out: list[tuple[str, str, bool]] = []
    for _, row in df.iterrows():
        sina = str(row.get("代码", "")).strip()
        if len(sina) < 4:
            continue
        symbol = _sina_to_standard(sina)
        name = str(row.get("名称", "")).strip()
        is_st = "ST" in name.upper()
        out.append((symbol, name, is_st))
    return out


async def _existing_max_dates(symbols: Iterable[str]) -> dict[str, str]:
    symbols_list = list(symbols)
    if not symbols_list:
        return {}
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MarketBarDaily.symbol, func.max(MarketBarDaily.trade_date))
            .where(MarketBarDaily.symbol.in_(symbols_list))
            .group_by(MarketBarDaily.symbol)
        )
        return {row[0]: row[1] for row in result.all()}


async def _persist_rows(rows: list[dict[str, Any]]) -> tuple[int, int]:
    if not rows:
        return 0, 0
    async with AsyncSessionLocal() as session:
        service = MarketDataImportService(session)
        result = await service.import_rows(rows, source="akshare-full-sync")
        return result.inserted_rows, result.updated_rows


async def upsert_stock_info(scan: list[tuple[str, str, bool]]) -> int:
    """Upsert (symbol, name, is_st) rows into ``stock_info``.

    Uses SQLite ``INSERT ... ON CONFLICT(symbol) DO UPDATE`` so the same call
    works for both first-time inserts and refresh-only updates without losing
    the original ``id``/``created_at``.
    """
    if not scan:
        return 0
    now_iso = datetime.utcnow().isoformat() + "Z"
    payload: list[dict[str, Any]] = []
    for symbol, name, is_st in scan:
        if not symbol:
            continue
        payload.append(
            {
                "id": uuid4().hex,
                "symbol": symbol,
                "name": name or "",
                "board": _board_for(symbol),
                "is_st": bool(is_st),
                "last_synced_at": now_iso,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
    if not payload:
        return 0
    # SQLite 默认 SQLITE_MAX_VARIABLE_NUMBER 为 32766, 每行 8 列, 单批控制在 500 行 (4000 个参数) 留足余量.
    batch_size = 500
    async with AsyncSessionLocal() as session:
        for i in range(0, len(payload), batch_size):
            chunk = payload[i : i + batch_size]
            stmt = sqlite_insert(StockInfo).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=[StockInfo.symbol],
                set_={
                    "name": stmt.excluded.name,
                    "board": stmt.excluded.board,
                    "is_st": stmt.excluded.is_st,
                    "last_synced_at": stmt.excluded.last_synced_at,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            await session.execute(stmt)
        await session.commit()
    return len(payload)


async def _apply_st_flags(st_symbols: set[str]) -> int:
    if not st_symbols:
        return 0
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            update(MarketBarDaily)
            .where(MarketBarDaily.symbol.in_(list(st_symbols)))
            .values(is_st=True)
        )
        await session.commit()
        return int(res.rowcount or 0)


# ── Singleton service ──────────────────────────────────────────────────

class _SyncState:
    """In-memory singleton. Single FastAPI worker assumption."""

    def __init__(self) -> None:
        self.progress = FullSyncProgress()
        self.lock = asyncio.Lock()
        self.bg_task: asyncio.Task[None] | None = None

    def reset(self) -> None:
        self.progress = FullSyncProgress()


_STATE = _SyncState()


class AlreadyRunningError(RuntimeError):
    """Raised when caller tries to start while a sync is in progress."""


def current_status() -> FullSyncProgress:
    return _STATE.progress


async def start_full_sync(req: FullSyncRequest) -> str:
    """Start a sync; raise AlreadyRunningError if one is in progress."""
    async with _STATE.lock:
        if _STATE.progress.is_running:
            raise AlreadyRunningError(_STATE.progress.task_id or "running")
        task_id = uuid4().hex[:12]
        _STATE.progress = FullSyncProgress(
            task_id=task_id,
            phase="scanning",
            started_at=datetime.utcnow().isoformat() + "Z",
        )
        _STATE.bg_task = asyncio.create_task(_run(req))
    return task_id


# ── Main orchestration ────────────────────────────────────────────────

async def _run(req: FullSyncRequest) -> None:
    try:
        # 1) 扫描全市场
        scan = await _fetch_market_symbols()

        # 1b) 把 (symbol, name, is_st) 同步落 stock_info(供前端展示)
        try:
            await upsert_stock_info(scan)
        except Exception:  # noqa: BLE001
            # 名字落库失败不应阻断行情同步
            pass

        # 2) 板块过滤
        boards = set(req.boards) if req.boards else None
        if boards:
            scan = [t for t in scan if _board_for(t[0]) in boards]

        # 3) 增量起点
        max_dates: dict[str, str] = {}
        if req.incremental:
            max_dates = await _existing_max_dates([s for s, _, _ in scan])

        plan: list[SymbolMeta] = []
        for symbol, name, is_st in scan:
            start = req.start_date
            if req.incremental and (mx := max_dates.get(symbol)):
                try:
                    next_d = (date.fromisoformat(mx) + timedelta(days=1)).isoformat()
                except ValueError:
                    next_d = req.start_date
                if next_d > req.end_date:
                    continue
                start = next_d
            plan.append(SymbolMeta(symbol=symbol, name=name, is_st=is_st, start=start, end=req.end_date))

        total = len(plan)
        skipped = len(scan) - total
        _STATE.progress.total = total
        _STATE.progress.skipped = skipped
        _STATE.progress.phase = "syncing" if total else "completed"
        if total == 0:
            _STATE.progress.finished_at = datetime.utcnow().isoformat() + "Z"
            return

        # 4) 进程池并发 fetch + 串行落库 + 失败重试
        st_symbols: set[str] = set()
        batch_size = max(1, req.concurrency)
        t_start = time.monotonic()
        loop = asyncio.get_running_loop()

        # 收集 fetch 失败的标的, 同步结束后用单进程顺序补跑一遍
        retry_meta: list[SymbolMeta] = []

        def _make_pool() -> ProcessPoolExecutor:
            # max_tasks_per_child: 每个 worker 跑 N 次后重启, 防止 mini_racer/V8 累积状态污染
            return ProcessPoolExecutor(max_workers=req.concurrency, max_tasks_per_child=64)

        pool = _make_pool()
        try:
            for i in range(0, total, batch_size):
                batch = plan[i:i + batch_size]
                try:
                    futures = [
                        loop.run_in_executor(
                            pool, _fetch_one_sync, m.symbol, m.start, m.end, req.adjust,
                        )
                        for m in batch
                    ]
                    fetched = await asyncio.gather(*futures, return_exceptions=True)
                except Exception:  # noqa: BLE001
                    # ProcessPool 整体崩溃 (BrokenProcessPool 等) — 重建 pool, 整批进入重试队列
                    try:
                        pool.shutdown(wait=False, cancel_futures=True)
                    except Exception:  # noqa: BLE001
                        pass
                    pool = _make_pool()
                    retry_meta.extend(batch)
                    _STATE.progress.done += len(batch)
                    continue

                batch_rows: list[dict[str, Any]] = []
                for meta, payload in zip(batch, fetched, strict=True):
                    if isinstance(payload, BaseException):
                        retry_meta.append(meta)
                        continue
                    if not payload:
                        # 空数据 = 退市/新股/接口暂时缺数据 — 也放进重试一次, 多数会变非空
                        retry_meta.append(meta)
                        continue
                    batch_rows.extend(payload)
                    if meta.is_st:
                        st_symbols.add(meta.symbol)

                if batch_rows:
                    try:
                        ins, upd = await _persist_rows(batch_rows)
                        _STATE.progress.inserted_rows += ins
                        _STATE.progress.updated_rows += upd
                    except Exception:  # noqa: BLE001
                        retry_meta.extend(batch)

                _STATE.progress.done += len(batch)
                _STATE.progress.last_symbol = batch[-1].symbol
                elapsed = time.monotonic() - t_start
                if elapsed > 0:
                    rate = _STATE.progress.done / elapsed
                    _STATE.progress.rate_per_sec = round(rate, 2)
                    if rate > 0:
                        _STATE.progress.eta_seconds = round((total - _STATE.progress.done) / rate, 1)
        finally:
            try:
                pool.shutdown(wait=False, cancel_futures=True)
            except Exception:  # noqa: BLE001
                pass

        # 4.5) 重试阶段: 主进程内顺序 fetch (避开 ProcessPool 不稳定)
        if retry_meta:
            _STATE.progress.phase = "retrying"
            seen: set[str] = set()
            unique_retry = [m for m in retry_meta if not (m.symbol in seen or seen.add(m.symbol))]
            retry_total = len(unique_retry)
            retry_rows: list[dict[str, Any]] = []
            retry_failed = 0
            for idx, meta in enumerate(unique_retry, 1):
                try:
                    rows = await asyncio.to_thread(
                        _fetch_one_sync, meta.symbol, meta.start, meta.end, req.adjust,
                    )
                    if rows:
                        retry_rows.extend(rows)
                        if meta.is_st:
                            st_symbols.add(meta.symbol)
                    # 空就算空, 不再重试
                except Exception:  # noqa: BLE001
                    retry_failed += 1
                # 每攒 200 行落一次库, 防止占内存
                if len(retry_rows) >= 1000:
                    try:
                        ins, upd = await _persist_rows(retry_rows)
                        _STATE.progress.inserted_rows += ins
                        _STATE.progress.updated_rows += upd
                    except Exception:  # noqa: BLE001
                        retry_failed += len(retry_rows)
                    retry_rows = []
                _STATE.progress.last_symbol = f"retry {idx}/{retry_total} · {meta.symbol}"

            if retry_rows:
                try:
                    ins, upd = await _persist_rows(retry_rows)
                    _STATE.progress.inserted_rows += ins
                    _STATE.progress.updated_rows += upd
                except Exception:  # noqa: BLE001
                    retry_failed += len(retry_rows)
            _STATE.progress.failures = retry_failed

        # 5) ST 标记
        _STATE.progress.phase = "st_flags"
        await _apply_st_flags(st_symbols)

        _STATE.progress.phase = "completed"
        _STATE.progress.finished_at = datetime.utcnow().isoformat() + "Z"
        _STATE.progress.eta_seconds = 0
    except Exception as e:  # noqa: BLE001
        _STATE.progress.phase = "failed"
        _STATE.progress.error = repr(e)
        _STATE.progress.finished_at = datetime.utcnow().isoformat() + "Z"
