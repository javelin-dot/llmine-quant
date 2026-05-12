"""Market data import service for research-grade daily bars."""

from __future__ import annotations

import asyncio
import csv
import importlib
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.data.models import MarketBarDaily


class MarketDataImportError(ValueError):
    """Raised when a market data import cannot be completed."""


@dataclass(slots=True)
class DailyBarRecord:
    """Normalized daily bar ready for persistence."""

    symbol: str
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float | None = None
    adjusted_close: float | None = None
    forward_factor: float | None = None
    is_st: bool = False
    prev_close: float | None = None
    limit_up_price: float | None = None
    limit_down_price: float | None = None
    is_limit_up: bool = False
    is_limit_down: bool = False
    is_suspended: bool = False
    can_buy: bool = True
    can_sell: bool = True

    def to_model_kwargs(self) -> dict[str, Any]:
        """Return ORM constructor kwargs."""
        return {
            "symbol": self.symbol,
            "trade_date": self.trade_date,
            "prev_close": self.prev_close,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "adjusted_close": self.adjusted_close,
            "forward_factor": self.forward_factor,
            "limit_up_price": self.limit_up_price,
            "limit_down_price": self.limit_down_price,
            "is_st": self.is_st,
            "is_limit_up": self.is_limit_up,
            "is_limit_down": self.is_limit_down,
            "is_suspended": self.is_suspended,
            "can_buy": self.can_buy,
            "can_sell": self.can_sell,
        }


@dataclass(frozen=True, slots=True)
class MarketDataImportResult:
    """Summary returned after an import run."""

    source: str
    total_rows: int
    imported_rows: int
    inserted_rows: int
    updated_rows: int
    skipped_rows: int
    symbols: list[str]
    start_date: str | None
    end_date: str | None
    errors: list[str]


_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "symbol": ("symbol", "code", "ticker", "sec_code", "股票代码", "代码"),
    "trade_date": ("trade_date", "date", "datetime", "time", "日期", "交易日期"),
    "open": ("open", "open_price", "开盘", "开盘价"),
    "high": ("high", "high_price", "最高", "最高价"),
    "low": ("low", "low_price", "最低", "最低价"),
    "close": ("close", "close_price", "收盘", "收盘价"),
    "volume": ("volume", "vol", "成交量"),
    "amount": ("amount", "turnover", "成交额"),
    "adjusted_close": ("adjusted_close", "adj_close", "复权收盘", "复权收盘价"),
    "forward_factor": ("forward_factor", "factor", "复权因子"),
    "is_st": ("is_st", "st", "是否st"),
}
_REQUIRED_FIELDS = ("symbol", "trade_date", "open", "high", "low", "close", "volume")
_TRUE_VALUES = {"1", "true", "t", "yes", "y", "是", "st"}


class LocalCsvDailyBarProvider:
    """Read daily bars from a local CSV file."""

    def read(self, path: str | Path) -> list[dict[str, Any]]:
        """Return raw rows from a CSV file."""
        csv_path = Path(path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file does not exist: {csv_path}")
        if not csv_path.is_file():
            raise MarketDataImportError(f"CSV path is not a file: {csv_path}")

        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))


class AKShareDailyBarProvider:
    """Fetch daily bars from AKShare when the optional package is installed."""

    async def fetch(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> list[dict[str, Any]]:
        """Fetch AKShare A-share daily bars for all symbols."""
        if not symbols:
            raise MarketDataImportError("At least one symbol is required for AKShare import.")
        try:
            akshare = importlib.import_module("akshare")
        except ImportError as exc:
            raise MarketDataImportError(
                "AKShare is not installed. Install the optional akshare package or use local CSV import."
            ) from exc

        start = _to_akshare_date(start_date)
        end = _to_akshare_date(end_date)
        rows: list[dict[str, Any]] = []
        for symbol in symbols:
            rows.extend(
                await asyncio.to_thread(
                    self._fetch_symbol,
                    akshare,
                    symbol,
                    start,
                    end,
                    adjust,
                )
            )
        return rows

    @staticmethod
    def _fetch_symbol(akshare: Any, symbol: str, start_date: str, end_date: str, adjust: str) -> list[dict[str, Any]]:
        ak_symbol = symbol.split(".")[0]
        df = akshare.stock_zh_a_hist(
            symbol=ak_symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        if df is None or getattr(df, "empty", False):
            return []
        records = df.to_dict("records")
        for record in records:
            record["symbol"] = symbol
        return records


class MarketDataImportService:
    """Normalize, clean and persist daily market bars."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.csv_provider = LocalCsvDailyBarProvider()
        self.akshare_provider = AKShareDailyBarProvider()

    async def import_csv_file(
        self,
        path: str | Path,
        *,
        default_symbol: str | None = None,
        source_name: str = "csv",
    ) -> MarketDataImportResult:
        """Import market bars from a UTF-8 CSV file."""
        rows = self.csv_provider.read(path)
        return await self.import_rows(rows, default_symbol=default_symbol, source=source_name)

    async def import_akshare(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> MarketDataImportResult:
        """Import market bars from AKShare."""
        rows = await self.akshare_provider.fetch(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        return await self.import_rows(rows, source="akshare")

    async def import_rows(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        default_symbol: str | None = None,
        source: str,
    ) -> MarketDataImportResult:
        """Import raw row mappings into ``MarketBarDaily``."""
        raw_rows = list(rows)
        bars, errors, duplicate_count = self._normalize_rows(raw_rows, default_symbol=default_symbol)
        updated_rows = await self._replace_existing_rows(bars)

        for bar in bars:
            self.session.add(MarketBarDaily(**bar.to_model_kwargs()))
        await self.session.commit()

        dates = [bar.trade_date for bar in bars]
        return MarketDataImportResult(
            source=source,
            total_rows=len(raw_rows),
            imported_rows=len(bars),
            inserted_rows=len(bars) - updated_rows,
            updated_rows=updated_rows,
            skipped_rows=len(errors) + duplicate_count,
            symbols=sorted({bar.symbol for bar in bars}),
            start_date=min(dates) if dates else None,
            end_date=max(dates) if dates else None,
            errors=errors,
        )

    def _normalize_rows(
        self,
        raw_rows: list[Mapping[str, Any]],
        *,
        default_symbol: str | None,
    ) -> tuple[list[DailyBarRecord], list[str], int]:
        errors: list[str] = []
        deduped: dict[tuple[str, str], DailyBarRecord] = {}
        duplicate_count = 0

        for row_number, row in enumerate(raw_rows, start=2):
            try:
                bar = _normalize_row(row, default_symbol=default_symbol)
                _validate_bar(bar)
            except MarketDataImportError as exc:
                errors.append(f"row {row_number}: {exc}")
                continue

            key = (bar.symbol, bar.trade_date)
            if key in deduped:
                duplicate_count += 1
            deduped[key] = bar

        bars = sorted(deduped.values(), key=lambda item: (item.symbol, item.trade_date))
        _apply_a_share_flags(bars)
        return bars, errors, duplicate_count

    async def _replace_existing_rows(self, bars: list[DailyBarRecord]) -> int:
        if not bars:
            return 0

        keys = {(bar.symbol, bar.trade_date) for bar in bars}
        result = await self.session.execute(
            select(MarketBarDaily).where(
                MarketBarDaily.symbol.in_({symbol for symbol, _ in keys}),
                MarketBarDaily.trade_date.in_({trade_date for _, trade_date in keys}),
            )
        )
        existing_rows = [
            row for row in result.scalars().all()
            if (row.symbol, row.trade_date) in keys
        ]
        for row in existing_rows:
            await self.session.delete(row)
        if existing_rows:
            await self.session.flush()
        return len(existing_rows)


def _normalize_row(row: Mapping[str, Any], *, default_symbol: str | None) -> DailyBarRecord:
    normal = {_normalize_header(key): value for key, value in row.items()}

    def get_value(field: str) -> Any:
        for alias in _COLUMN_ALIASES[field]:
            key = _normalize_header(alias)
            if key in normal and normal[key] not in (None, ""):
                return normal[key]
        return None

    missing = [field for field in _REQUIRED_FIELDS if field != "symbol" and get_value(field) in (None, "")]
    raw_symbol = get_value("symbol") or default_symbol
    if raw_symbol in (None, ""):
        missing.append("symbol")
    if missing:
        raise MarketDataImportError(f"missing required fields: {', '.join(missing)}")

    close = _parse_float(get_value("close"), "close")
    adjusted_close = _parse_optional_float(get_value("adjusted_close"), "adjusted_close")
    return DailyBarRecord(
        symbol=_normalize_symbol(raw_symbol),
        trade_date=_parse_trade_date(get_value("trade_date")),
        open=_parse_float(get_value("open"), "open"),
        high=_parse_float(get_value("high"), "high"),
        low=_parse_float(get_value("low"), "low"),
        close=close,
        volume=_parse_volume(get_value("volume")),
        amount=_parse_optional_float(get_value("amount"), "amount"),
        adjusted_close=adjusted_close if adjusted_close is not None else close,
        forward_factor=_parse_optional_float(get_value("forward_factor"), "forward_factor"),
        is_st=_parse_bool(get_value("is_st")),
    )


def _normalize_header(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_symbol(value: Any) -> str:
    symbol = str(value).strip().upper()
    if not symbol:
        raise MarketDataImportError("symbol is empty")
    return symbol


def _parse_trade_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    if not text:
        raise MarketDataImportError("trade_date is empty")
    text = text.split(" ")[0].replace("/", "-").replace(".", "-")
    if len(text) == 8 and text.isdigit():
        text = f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise MarketDataImportError(f"invalid trade_date: {value}") from exc


def _parse_float(value: Any, field: str) -> float:
    parsed = _parse_optional_float(value, field)
    if parsed is None:
        raise MarketDataImportError(f"{field} is empty")
    return parsed


def _parse_optional_float(value: Any, field: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise MarketDataImportError(f"invalid {field}: {value}") from exc
    if not math.isfinite(parsed):
        raise MarketDataImportError(f"invalid {field}: {value}")
    return parsed


def _parse_volume(value: Any) -> int:
    volume = _parse_float(value, "volume")
    if volume < 0:
        raise MarketDataImportError("volume cannot be negative")
    return int(volume)


def _parse_bool(value: Any) -> bool:
    if value in (None, ""):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUE_VALUES


def _validate_bar(bar: DailyBarRecord) -> None:
    for field in ("open", "high", "low", "close"):
        if getattr(bar, field) <= 0:
            raise MarketDataImportError(f"{field} must be positive")
    if bar.low > bar.high:
        raise MarketDataImportError("low cannot be greater than high")
    if bar.open > bar.high or bar.close > bar.high:
        raise MarketDataImportError("open/close cannot be greater than high")
    if bar.open < bar.low or bar.close < bar.low:
        raise MarketDataImportError("open/close cannot be lower than low")
    if bar.amount is not None and bar.amount < 0:
        raise MarketDataImportError("amount cannot be negative")
    if bar.adjusted_close is not None and bar.adjusted_close <= 0:
        raise MarketDataImportError("adjusted_close must be positive")


def _apply_a_share_flags(bars: list[DailyBarRecord]) -> None:
    previous_close_by_symbol: dict[str, float] = {}
    for bar in bars:
        prev_close = previous_close_by_symbol.get(bar.symbol)
        bar.prev_close = prev_close
        bar.is_suspended = bar.volume == 0

        if prev_close is not None and prev_close > 0:
            limit_ratio = 0.05 if bar.is_st else 0.10
            bar.limit_up_price = round(prev_close * (1 + limit_ratio), 2)
            bar.limit_down_price = round(prev_close * (1 - limit_ratio), 2)
            bar.is_limit_up = bar.close >= bar.limit_up_price * 0.999
            bar.is_limit_down = bar.close <= bar.limit_down_price * 1.001

        bar.can_buy = not bar.is_suspended and not bar.is_limit_up
        bar.can_sell = not bar.is_suspended and not bar.is_limit_down
        previous_close_by_symbol[bar.symbol] = bar.close


def _to_akshare_date(value: str) -> str:
    return _parse_trade_date(value).replace("-", "")
