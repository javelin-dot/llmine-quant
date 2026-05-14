"""API tests for persisted research backtests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.domains.backtest.models import BacktestMetric, BacktestRun, BacktestTask, EquityPoint
from app.domains.data.models import MarketBarDaily
from app.main import app


@pytest.fixture
async def client_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, session
        app.dependency_overrides.clear()

    await engine.dispose()


async def test_create_and_get_backtest_uses_persisted_results(client_session):
    client, session = client_session
    await _seed_bars(session, "000001.SZ", [10, 11, 12, 13, 14])

    create_resp = await client.post(
        "/api/v1/backtests/",
        json={
            "universe": ["000001.SZ"],
            "startDate": "2024-01-01",
            "endDate": "2024-01-05",
            "initialCash": 1_000,
            "strategyParams": {"short_window": 2, "long_window": 3, "target_gross": 0.5},
            "costConfig": {
                "commissionRate": 0,
                "minCommission": 0,
                "stampTaxRate": 0,
                "slippageBps": 0,
            },
        },
    )

    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["status"] == "completed"
    assert created["taskId"]
    assert created["runId"]
    assert created["metrics"]["cumulativeReturn"] > 0
    assert len(created["equityCurve"]) == 5

    task = await session.get(BacktestTask, created["taskId"])
    run = await session.get(BacktestRun, created["runId"])
    metric = (
        await session.execute(select(BacktestMetric).where(BacktestMetric.run_id == created["runId"]))
    ).scalar_one()
    first_equity = (
        await session.execute(select(EquityPoint).where(EquityPoint.run_id == created["runId"]).limit(1))
    ).scalar_one()
    assert task is not None
    assert run is not None
    assert metric is not None
    assert first_equity is not None

    # New extended metrics are returned from the live compute path.
    for field in ("calmarRatio", "sortinoRatio", "volatility", "profitFactor"):
        assert isinstance(created["metrics"][field], float)

    get_resp = await client.get(f"/api/v1/backtests/{created['taskId']}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["taskId"] == created["taskId"]
    assert fetched["runId"] == created["runId"]
    # Core persisted metrics must match; extended metrics are not stored in DB yet (return 0.0).
    base_fields = ("cumulativeReturn", "annualReturn", "maxDrawdown", "sharpeRatio", "winRate", "turnover")
    for f in base_fields:
        assert fetched["metrics"][f] == pytest.approx(created["metrics"][f], rel=1e-6)
    assert fetched["equityCurve"] == created["equityCurve"]


async def test_create_backtest_returns_400_when_no_market_data(client_session):
    client, _session = client_session

    response = await client.post(
        "/api/v1/backtests/",
        json={
            "universe": ["000001.SZ"],
            "startDate": "2024-01-01",
            "endDate": "2024-01-05",
        },
    )

    assert response.status_code == 400
    assert "no market bars" in response.json()["detail"]


async def test_imported_csv_data_can_run_example_strategy_backtest_with_metrics(client_session, tmp_path):
    client, _session = client_session
    csv_path = tmp_path / "bars.csv"
    csv_path.write_text(
        "\n".join(
            [
                "symbol,trade_date,open,high,low,close,volume,amount,adjusted_close",
                "000001.SZ,2024-01-01,10,10,10,10,1000,10000,10",
                "000001.SZ,2024-01-02,11,11,11,11,1000,11000,11",
                "000001.SZ,2024-01-03,12,12,12,12,1000,12000,12",
                "000001.SZ,2024-01-04,13,13,13,13,1000,13000,13",
                "000001.SZ,2024-01-05,14,14,14,14,1000,14000,14",
            ]
        ),
        encoding="utf-8",
    )

    import_resp = await client.post(
        "/api/v1/data/market-bars/import/csv",
        json={"path": str(csv_path)},
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["importedRows"] == 5

    backtest_resp = await client.post(
        "/api/v1/backtests/",
        json={
            "universe": ["000001.SZ"],
            "startDate": "2024-01-01",
            "endDate": "2024-01-05",
            "strategyName": "dual_ma",
            "initialCash": 1_000,
            "strategyParams": {"short_window": 2, "long_window": 3, "target_gross": 0.5},
            "costConfig": {
                "commissionRate": 0,
                "minCommission": 0,
                "stampTaxRate": 0,
                "slippageBps": 0,
            },
        },
    )

    assert backtest_resp.status_code == 200
    result = backtest_resp.json()
    assert result["status"] == "completed"
    assert result["metrics"]["cumulativeReturn"] > 0
    assert result["metrics"]["annualReturn"] > 0
    assert result["metrics"]["sharpeRatio"] > 0
    assert result["metrics"]["winRate"] == 1
    assert result["metrics"]["turnover"] > 0
    assert [point["tradeDate"] for point in result["equityCurve"]] == [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
        "2024-01-04",
        "2024-01-05",
    ]


async def test_create_backtest_with_in_sample_split_returns_segment_metrics(client_session):
    """API surfaces IS/OOS metrics when `inSampleEndDate` is provided."""
    client, session = client_session
    await _seed_bars(session, "000001.SZ", [10, 11, 12, 13, 14, 13.5, 14.5, 15.5])

    create_resp = await client.post(
        "/api/v1/backtests/",
        json={
            "universe": ["000001.SZ"],
            "startDate": "2024-01-01",
            "endDate": "2024-01-08",
            "inSampleEndDate": "2024-01-04",
            "initialCash": 1_000,
            "strategyParams": {"short_window": 2, "long_window": 3, "target_gross": 0.5},
            "costConfig": {
                "commissionRate": 0,
                "minCommission": 0,
                "stampTaxRate": 0,
                "slippageBps": 0,
            },
        },
    )
    assert create_resp.status_code == 200
    body = create_resp.json()
    assert body["inSampleEndDate"] == "2024-01-04"
    assert body["inSampleMetrics"] is not None
    assert body["outSampleMetrics"] is not None
    assert body["metrics"] is not None  # full-range metrics still present

    # Equity points carry the phase tag.
    phases = {p["tradeDate"]: p["phase"] for p in body["equityCurve"]}
    assert phases["2024-01-04"] == "is"
    assert phases["2024-01-05"] == "oos"

    # GET path returns the same shape from persisted rows.
    fetched = (await client.get(f"/api/v1/backtests/{body['taskId']}")).json()
    assert fetched["inSampleEndDate"] == "2024-01-04"
    assert fetched["inSampleMetrics"] is not None
    assert fetched["outSampleMetrics"] is not None
    phases_get = {p["tradeDate"]: p["phase"] for p in fetched["equityCurve"]}
    assert phases_get["2024-01-05"] == "oos"


async def test_trades_and_report_endpoints_aggregate_phase3_artefacts(client_session):
    """POST baseline + walk-forward + sensitivity, then GET /trades and /report."""
    client, session = client_session
    closes = [10 + i * 0.1 + (0.2 if i % 5 == 0 else 0.0) for i in range(20)]
    await _seed_bars(session, "000001.SZ", closes)

    # Baseline with IS/OOS split
    create_resp = await client.post(
        "/api/v1/backtests/",
        json={
            "universe": ["000001.SZ"],
            "startDate": "2024-01-01",
            "endDate": "2024-01-20",
            "inSampleEndDate": "2024-01-12",
            "initialCash": 1_000,
            "strategyParams": {"short_window": 2, "long_window": 3, "target_gross": 0.5},
            "costConfig": {
                "commissionRate": 0, "minCommission": 0, "stampTaxRate": 0, "slippageBps": 0
            },
        },
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["taskId"]

    # /trades
    trades_resp = await client.get(f"/api/v1/backtests/{task_id}/trades")
    assert trades_resp.status_code == 200
    trades = trades_resp.json()
    # The dual_ma strategy produces at least one trade on this curve.
    assert isinstance(trades, list)
    if trades:
        assert "reason" in trades[0]
        assert trades[0]["reason"]  # rule explanation populated

    # /report aggregates everything (walk-forward & sensitivity are empty here)
    report_resp = await client.get(f"/api/v1/backtests/{task_id}/report")
    assert report_resp.status_code == 200
    report = report_resp.json()
    assert report["taskId"] == task_id
    assert report["summary"]["inSampleEndDate"] == "2024-01-12"
    assert report["overfit"] is not None
    assert isinstance(report["walkForwardFolds"], list)
    assert isinstance(report["sensitivityRuns"], list)
    assert isinstance(report["trades"], list)
    assert report["labChecklist"]
    assert report["promotionGate"]["decision"] in {"pass", "review", "block"}
    assert any(check["id"] == "oos_split" and check["status"] == "pass" for check in report["labChecklist"])
    assert any(check["id"] == "walk_forward" and check["status"] == "warn" for check in report["labChecklist"])


async def test_walk_forward_endpoint_persists_folds(client_session):
    """POST /backtests/walk-forward returns N folds and writes them to DB."""
    client, session = client_session
    closes = [10 + i * 0.1 for i in range(20)]
    await _seed_bars(session, "000001.SZ", closes)

    resp = await client.post(
        "/api/v1/backtests/walk-forward",
        json={
            "universe": ["000001.SZ"],
            "startDate": "2024-01-01",
            "endDate": "2024-01-20",
            "initialCash": 1_000,
            "folds": 4,
            "trainRatio": 0.7,
            "strategyParams": {"short_window": 2, "long_window": 3, "target_gross": 0.5},
            "costConfig": {
                "commissionRate": 0,
                "minCommission": 0,
                "stampTaxRate": 0,
                "slippageBps": 0,
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["taskId"]
    assert body["runId"]
    assert len(body["folds"]) == 4
    assert all("trainStart" in f and "testEnd" in f for f in body["folds"])


async def test_universe_suggest_respects_min_bars_and_max_symbols(client_session):
    client, session = client_session
    await _seed_bars(session, "600519.SH", [10, 11, 12, 13, 14, 15, 16, 17])
    await _seed_bars(session, "300750.SZ", [20, 21, 22, 23, 24, 25, 26])
    await _seed_bars(session, "000333.SZ", [30, 31, 32, 33])

    resp = await client.post(
        "/api/v1/backtests/universe/suggest",
        json={
            "strategyFamily": "trend",
            "minBars": 6,
            "maxSymbols": 1,
            "diversify": True,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["symbols"]) == 1
    assert body["symbols"][0] in {"600519.SH", "300750.SZ"}
    assert all(c["bars"] >= 6 for c in body["candidates"])
    assert "000333.SZ" not in {c["symbol"] for c in body["candidates"]}


async def test_create_backtest_rejects_invalid_in_sample_end_date(client_session):
    """API returns 400 when split date is outside the run range."""
    client, session = client_session
    await _seed_bars(session, "000001.SZ", [10, 11, 12, 13, 14])

    resp = await client.post(
        "/api/v1/backtests/",
        json={
            "universe": ["000001.SZ"],
            "startDate": "2024-01-01",
            "endDate": "2024-01-05",
            "inSampleEndDate": "2024-01-05",  # equals end_date — leaves no OOS days
        },
    )
    assert resp.status_code == 400
    assert "in_sample_end_date" in resp.json()["detail"]


async def _seed_bars(session, symbol: str, closes: list[float]) -> None:
    for index, close in enumerate(closes, start=1):
        trade_date = f"2024-01-{index:02d}"
        session.add(
            MarketBarDaily(
                symbol=symbol,
                trade_date=trade_date,
                prev_close=closes[index - 2] if index > 1 else None,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=1000,
                amount=close * 1000,
                adjusted_close=close,
                can_buy=True,
                can_sell=True,
            )
        )
    await session.commit()
