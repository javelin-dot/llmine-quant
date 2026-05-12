"""End-to-end test for AI strategy generation pipeline.

Covers the full path:
    natural-language prompt
      → DSL spec (mock LLM)
      → semantic + AST validation
      → research backtest on real seeded bars
      → DB persistence (StrategyTask ↔ BacktestTask ↔ BacktestRun)
      → PipelineEvent trail
      → Strategy + StrategyVersion finalisation
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.domains.backtest.models import (
    BacktestMetric,
    BacktestRun,
    BacktestTask,
    EquityPoint,
)
from app.domains.data.models import (
    FeatureSet,
    FeatureUsage,
    LineageEdge,
    LineageNode,
    MarketBarDaily,
)
from app.domains.strategy.models import (
    PipelineEvent,
    Strategy,
    StrategyTask,
    StrategyVersion,
)
from app.services.strategy_generation import StrategyGenerationService


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as test_session:
        yield test_session

    await engine.dispose()


async def _seed_bars(session, symbol: str, n_days: int = 60) -> None:
    """Seed `n_days` daily bars with a mild uptrend so dual_ma can produce trades."""
    start = date(2024, 1, 1)
    prev_close: float | None = None
    base = 10.0
    for i in range(n_days):
        d = start + timedelta(days=i)
        # Mild uptrend with small wiggle so MAs cross occasionally.
        close = base + i * 0.05 + (0.2 if i % 7 == 0 else 0.0)
        session.add(
            MarketBarDaily(
                symbol=symbol,
                trade_date=d.isoformat(),
                prev_close=prev_close,
                open=close,
                high=close + 0.05,
                low=close - 0.05,
                close=close,
                volume=1000,
                amount=close * 1000,
                adjusted_close=close,
                can_buy=True,
                can_sell=True,
            )
        )
        prev_close = close
    await session.commit()


async def test_full_nl_to_real_backtest_pipeline(session, monkeypatch):
    """Run the pipeline from a NL prompt and verify every artefact reaches the DB."""
    # Force mock LLM provider regardless of host configuration.
    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "llm_provider", "mock", raising=False)

    await _seed_bars(session, "000001.SZ", n_days=60)

    service = StrategyGenerationService(session)
    task = await service.create_task(
        prompt="构造一个 A 股价值精选策略，20 日动量过滤，等权 top 分位",
        market="A",
        risk_profile="balanced",
    )
    assert task.status == "queued"
    assert task.id

    result = await service.run_pipeline(task.id)

    # ── 1. StrategyTask reaches "succeeded" with full linkage ─────────
    assert result.status == "succeeded", f"pipeline failed: {result.error}"
    assert result.strategy_id is not None
    assert result.backtest_task_id is not None
    assert result.backtest_run_id is not None
    assert result.error is None

    payload = json.loads(result.result or "{}")
    assert payload["strategyId"] == result.strategy_id
    assert payload["backtestTaskId"] == result.backtest_task_id
    assert payload["backtestRunId"] == result.backtest_run_id
    assert "sharpe" in payload
    assert "maxDd" in payload

    # ── 2. Strategy + StrategyVersion finalised ──────────────────────
    strategy = await session.get(Strategy, result.strategy_id)
    assert strategy is not None
    assert strategy.status == "backtesting"
    assert strategy.sharpe is not None
    assert strategy.max_dd is not None

    versions = (
        await session.execute(
            select(StrategyVersion).where(StrategyVersion.strategy_id == strategy.id)
        )
    ).scalars().all()
    assert len(versions) == 1
    version = versions[0]
    assert version.status == "ready"
    assert version.code_text and "RuleBasedStrategy" in version.code_text
    assert version.params_schema and "factors" in version.params_schema
    assert version.risk_rules

    # ── 3. BacktestTask + Run + Metric + EquityPoints persisted ──────
    bt_task = await session.get(BacktestTask, result.backtest_task_id)
    assert bt_task is not None
    assert bt_task.status == "completed"
    assert bt_task.strategy_version_id == version.id  # real linkage, not strategy name

    bt_run = await session.get(BacktestRun, result.backtest_run_id)
    assert bt_run is not None
    assert bt_run.task_id == bt_task.id
    assert bt_run.status == "completed"

    metric = (
        await session.execute(
            select(BacktestMetric).where(BacktestMetric.run_id == bt_run.id)
        )
    ).scalar_one()
    assert metric.cumulative_return is not None
    assert metric.sharpe_ratio is not None
    assert metric.win_rate is not None

    equity_points = (
        await session.execute(
            select(EquityPoint).where(EquityPoint.run_id == bt_run.id).order_by(EquityPoint.trade_date)
        )
    ).scalars().all()
    assert len(equity_points) == 60
    assert equity_points[0].trade_date == "2024-01-01"

    # ── 4. PipelineEvent trail covers all stages ─────────────────────
    events = (
        await session.execute(
            select(PipelineEvent)
            .where(PipelineEvent.strategy_id == strategy.id)
            .order_by(PipelineEvent.created_at.asc())
        )
    ).scalars().all()
    stages = [e.stage for e in events]
    assert "research" in stages
    assert "code_gen" in stages
    assert "static_check" in stages
    assert "version" in stages
    assert "backtest" in stages
    assert "risk" in stages
    assert "done" in stages

    # The backtest event should reference the real task/run IDs.
    bt_events = [e for e in events if e.stage == "backtest"]
    assert len(bt_events) == 1
    bt_detail = json.loads(bt_events[0].detail or "{}")
    assert bt_detail["backtestTaskId"] == result.backtest_task_id
    assert bt_detail["backtestRunId"] == result.backtest_run_id

    # ── 5. Feature Store + lineage populated from the DSL spec ───────
    features = (await session.execute(select(FeatureSet))).scalars().all()
    assert features  # at least one factor produced a feature row
    usages = (
        await session.execute(
            select(FeatureUsage).where(FeatureUsage.strategy_version_id == version.id)
        )
    ).scalars().all()
    assert usages
    assert all(u.backtest_run_id == result.backtest_run_id for u in usages)

    lineage_nodes = (await session.execute(select(LineageNode))).scalars().all()
    lineage_edges = (
        await session.execute(
            select(LineageEdge).where(LineageEdge.backtest_run_id == result.backtest_run_id)
        )
    ).scalars().all()
    node_types = {n.node_type for n in lineage_nodes}
    assert {"raw", "cleaned", "feature", "strategy", "run"} <= node_types
    assert lineage_edges  # edges connect the chain


async def test_pipeline_failure_marks_task_and_records_stage(session, monkeypatch):
    """When no market data exists, the backtest stage fails cleanly with diagnostics."""
    from app.core.config import settings as app_settings

    monkeypatch.setattr(app_settings, "llm_provider", "mock", raising=False)

    # No bars seeded — research backtest will raise.
    service = StrategyGenerationService(session)
    task = await service.create_task(
        prompt="生成一个 A 股动量策略",
        market="A",
        risk_profile="balanced",
    )
    result = await service.run_pipeline(task.id)

    assert result.status == "failed"
    assert result.error
    assert result.strategy_id is not None  # placeholder strategy was created

    # The failure should produce a PipelineEvent with a recognised failure stage.
    events = (
        await session.execute(
            select(PipelineEvent).where(PipelineEvent.strategy_id == result.strategy_id)
        )
    ).scalars().all()
    fail_stages = {e.stage for e in events if "fail" in e.event or e.progress == 100 and "fail" in (e.event or "")}
    # At minimum, a failure event should be persisted; stages depend on classification.
    assert any(e.event.endswith("failed") for e in events)

    # Strategy reverts to draft on failure.
    strategy = await session.get(Strategy, result.strategy_id)
    assert strategy is not None
    assert strategy.status == "draft"
