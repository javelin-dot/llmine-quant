"""API tests for market data import endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as test_client:
            yield test_client
        app.dependency_overrides.clear()

    await engine.dispose()


async def test_import_market_bars_csv_and_query(client: AsyncClient, tmp_path):
    csv_path = tmp_path / "bars.csv"
    csv_path.write_text(
        "\n".join(
            [
                "symbol,trade_date,open,high,low,close,volume,amount,adjusted_close",
                "000001.SZ,2024-01-02,10,10.2,9.8,10,100,1000,10",
                "000001.SZ,2024-01-03,10.5,11,10.5,11,120,1200,11",
            ]
        ),
        encoding="utf-8",
    )

    import_resp = await client.post(
        "/api/v1/data/market-bars/import/csv",
        json={"path": str(csv_path)},
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["importedRows"] == 2

    query_resp = await client.get(
        "/api/v1/data/market-bars",
        params={"symbol": "000001.SZ", "startDate": "2024-01-02", "endDate": "2024-01-03"},
    )
    assert query_resp.status_code == 200
    bars = query_resp.json()
    assert [bar["tradeDate"] for bar in bars] == ["2024-01-02", "2024-01-03"]
    assert bars[1]["isLimitUp"] is True
    assert bars[1]["canBuy"] is False
