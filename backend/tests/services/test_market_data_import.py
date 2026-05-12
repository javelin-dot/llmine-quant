"""Tests for market data import service."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.data.models import MarketBarDaily
from app.services.market_data_import import MarketDataImportService


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as test_session:
        yield test_session

    await engine.dispose()


async def test_import_rows_cleans_dedupes_and_marks_a_share_flags(session):
    service = MarketDataImportService(session)

    result = await service.import_rows(
        [
            {
                "symbol": "000001.SZ",
                "trade_date": "2024-01-02",
                "open": "10.0",
                "high": "10.2",
                "low": "9.8",
                "close": "10.0",
                "volume": "100",
                "amount": "1000",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "2024-01-03",
                "open": "10.5",
                "high": "11.0",
                "low": "10.5",
                "close": "11.0",
                "volume": "120",
                "amount": "1200",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "2024-01-03",
                "open": "10.5",
                "high": "11.0",
                "low": "10.5",
                "close": "11.0",
                "volume": "130",
                "amount": "1300",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "2024-01-04",
                "open": "11.0",
                "high": "11.0",
                "low": "11.0",
                "close": "11.0",
                "volume": "0",
                "amount": "0",
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "2024-01-05",
                "open": "-1",
                "high": "11.0",
                "low": "10.0",
                "close": "10.5",
                "volume": "100",
            },
        ],
        source="unit",
    )

    assert result.total_rows == 5
    assert result.imported_rows == 3
    assert result.inserted_rows == 3
    assert result.updated_rows == 0
    assert result.skipped_rows == 2
    assert result.symbols == ["000001.SZ"]
    assert result.start_date == "2024-01-02"
    assert result.end_date == "2024-01-04"
    assert len(result.errors) == 1

    rows = (
        await session.execute(
            select(MarketBarDaily).order_by(MarketBarDaily.trade_date)
        )
    ).scalars().all()

    assert [row.trade_date for row in rows] == ["2024-01-02", "2024-01-03", "2024-01-04"]
    assert rows[1].amount == 1300
    assert rows[1].prev_close == 10.0
    assert rows[1].is_limit_up is True
    assert rows[1].can_buy is False
    assert rows[2].is_suspended is True
    assert rows[2].can_buy is False
    assert rows[2].can_sell is False


async def test_import_rows_replaces_existing_symbol_date(session):
    service = MarketDataImportService(session)
    base_row = {
        "symbol": "600000.SH",
        "trade_date": "2024-01-02",
        "open": "10.0",
        "high": "10.2",
        "low": "9.8",
        "close": "10.0",
        "volume": "100",
    }

    await service.import_rows([base_row], source="unit")
    result = await service.import_rows(
        [{**base_row, "close": "10.1", "high": "10.3"}],
        source="unit",
    )

    assert result.imported_rows == 1
    assert result.inserted_rows == 0
    assert result.updated_rows == 1

    rows = (await session.execute(select(MarketBarDaily))).scalars().all()
    assert len(rows) == 1
    assert rows[0].close == 10.1
