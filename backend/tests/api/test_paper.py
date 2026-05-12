"""API tests for /api/v1/paper/* — accounts, EOD run, persisted listings."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.domains.data.models import MarketBarDaily
from app.main import app


@pytest.fixture
async def client_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        async def override_get_db():
            yield session
        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, session
        app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_universe(session, symbols: list[str], n: int) -> str:
    last_date = ""
    for sym_idx, symbol in enumerate(symbols):
        base = 10.0 + sym_idx * 0.5
        for i in range(1, n + 1):
            date = f"2024-01-{i:02d}" if i <= 31 else f"2024-02-{i - 31:02d}"
            close = base + i * 0.1
            session.add(
                MarketBarDaily(
                    symbol=symbol,
                    trade_date=date,
                    prev_close=close - 0.1 if i > 1 else None,
                    open=close, high=close + 0.05, low=close - 0.05, close=close,
                    volume=1000, amount=close * 1000, adjusted_close=close,
                    can_buy=True, can_sell=True,
                )
            )
            last_date = date
    await session.commit()
    return last_date


async def test_paper_account_lifecycle_and_run_eod(client_session):
    client, session = client_session
    last_date = await _seed_universe(session, [f"00000{i}.SZ" for i in range(1, 13)], 25)

    # Create account
    resp = await client.post("/api/v1/paper/accounts", json={
        "name": "test-paper",
        "ownerId": "tester",
        "initialCash": 100_000,
    })
    assert resp.status_code == 200
    account = resp.json()
    aid = account["id"]
    assert account["status"] == "active"
    assert account["cash"] == 100_000

    # List
    list_resp = await client.get("/api/v1/paper/accounts")
    assert list_resp.status_code == 200
    assert any(a["id"] == aid for a in list_resp.json())

    # Run EOD
    run_resp = await client.post(
        f"/api/v1/paper/accounts/{aid}/run-eod",
        json={"tradeDate": last_date},
    )
    assert run_resp.status_code == 200
    summary = run_resp.json()
    assert summary["accountId"] == aid
    assert summary["tradeDate"] == last_date
    assert summary["ordersCreated"] >= 1
    assert summary["ordersFilled"] >= 1
    assert summary["nav"] is not None and summary["nav"] > 0

    # Positions / orders / fills / nav listing
    positions = (await client.get(f"/api/v1/paper/accounts/{aid}/positions")).json()
    assert positions  # at least one position now

    orders = (await client.get(f"/api/v1/paper/accounts/{aid}/orders")).json()
    assert orders
    assert all("status" in o for o in orders)

    fills = (await client.get(f"/api/v1/paper/accounts/{aid}/fills")).json()
    assert fills

    nav_points = (await client.get(f"/api/v1/paper/accounts/{aid}/nav")).json()
    assert len(nav_points) == 1
    assert nav_points[0]["nav"] == pytest.approx(summary["nav"])


async def test_paper_run_eod_returns_404_for_unknown_account(client_session):
    client, _session = client_session
    resp = await client.post(
        "/api/v1/paper/accounts/does-not-exist/run-eod",
        json={"tradeDate": "2024-01-25"},
    )
    assert resp.status_code == 404
