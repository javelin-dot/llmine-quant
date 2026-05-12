"""Feature Store + data lineage persistence helpers.

A strategy generation run produces:
    1. A DSL spec listing factors / filters → upsert into ``feature_sets`` and
       link via ``feature_usages`` to the StrategyVersion.
    2. A real backtest run → write a lineage chain
       raw(market_bars_daily) → feature(<each used feature>) → strategy(<version>) → run(<run id>)
       and the connecting edges.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.data.models import (
    FeatureSet,
    FeatureUsage,
    LineageEdge,
    LineageNode,
)
from app.domains.strategy.generation_dsl import StrategyGenerationSpec


_DEFAULT_WINDOW = {
    "momentum": 20,
    "value": 60,
    "quality": 60,
    "volatility": 20,
    "size": 20,
    "growth": 60,
    "sentiment": 5,
    "macro": 30,
    "ml_score": 0,
    "custom": 0,
}


async def upsert_features_from_spec(
    session: AsyncSession, spec: StrategyGenerationSpec
) -> list[FeatureSet]:
    """Ensure each factor in the spec has a row in ``feature_sets``.

    Returns the FeatureSet rows in spec-factor order. Versions are derived from
    factor params hash so the same factor with different params produces a new
    feature record.
    """
    out: list[FeatureSet] = []
    for factor in spec.factors:
        version = _factor_version(factor.params)
        existing = (
            await session.execute(
                select(FeatureSet).where(
                    FeatureSet.name == factor.name, FeatureSet.version == version
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            existing = FeatureSet(
                name=factor.name,
                version=version,
                kind=factor.kind,
                description=factor.description,
                dependencies_json=json.dumps(dict(factor.params), ensure_ascii=False),
                computation_window=_window_for(factor),
                permission_scope="research",
                validated=True,
            )
            session.add(existing)
            await session.flush()
        out.append(existing)
    return out


async def record_feature_usage(
    session: AsyncSession,
    *,
    features: list[FeatureSet],
    strategy_version_id: str,
    backtest_run_id: str | None = None,
    role: str = "factor",
) -> list[FeatureUsage]:
    """Write FeatureUsage rows linking features to a strategy version (and optionally a run)."""
    usages: list[FeatureUsage] = []
    for feature in features:
        usage = FeatureUsage(
            feature_id=feature.id,
            strategy_version_id=strategy_version_id,
            backtest_run_id=backtest_run_id,
            role=role,
        )
        session.add(usage)
        usages.append(usage)
    await session.flush()
    return usages


async def write_lineage_for_run(
    session: AsyncSession,
    *,
    features: list[FeatureSet],
    strategy_version_id: str,
    backtest_run_id: str,
    universe: tuple[str, ...],
) -> tuple[list[LineageNode], list[LineageEdge]]:
    """Build a lineage chain: raw → cleaned → feature(s) → strategy → run.

    Universe symbols collapse into a single "raw" node labelled by count so the
    chain stays compact even for large universes.
    """
    nodes: list[LineageNode] = []

    raw = LineageNode(
        node_type="raw",
        label=f"market_bars_daily/{len(universe)} symbols",
        version="v1",
        permission="research",
        ref_table="market_bars_daily",
        ref_id=",".join(universe[:10]),
    )
    session.add(raw)

    cleaned = LineageNode(
        node_type="cleaned",
        label="cleaned_bars",
        version="v1",
        permission="research",
        ref_table="market_bars_daily",
        ref_id=None,
    )
    session.add(cleaned)
    await session.flush()
    nodes.extend([raw, cleaned])

    feature_nodes: list[LineageNode] = []
    for f in features:
        fn = LineageNode(
            node_type="feature",
            label=f.name,
            version=f.version,
            permission="research",
            ref_table="feature_sets",
            ref_id=f.id,
        )
        session.add(fn)
        feature_nodes.append(fn)
    await session.flush()
    nodes.extend(feature_nodes)

    strat = LineageNode(
        node_type="strategy",
        label=f"version/{strategy_version_id[:8]}",
        version="v1",
        permission="research",
        ref_table="strategy_versions",
        ref_id=strategy_version_id,
    )
    session.add(strat)

    run = LineageNode(
        node_type="run",
        label=f"run/{backtest_run_id[:8]}",
        version="v1",
        permission="research",
        ref_table="backtest_runs",
        ref_id=backtest_run_id,
    )
    session.add(run)
    await session.flush()
    nodes.extend([strat, run])

    edges: list[LineageEdge] = []

    def _edge(from_node: LineageNode, to_node: LineageNode) -> None:
        e = LineageEdge(
            from_node_id=from_node.id,
            to_node_id=to_node.id,
            backtest_run_id=backtest_run_id,
        )
        session.add(e)
        edges.append(e)

    _edge(raw, cleaned)
    for fn in feature_nodes:
        _edge(cleaned, fn)
        _edge(fn, strat)
    if not feature_nodes:
        _edge(cleaned, strat)
    _edge(strat, run)

    await session.flush()
    return nodes, edges


# ── internals ────────────────────────────────────────────────────────────


def _factor_version(params: dict) -> str:
    """Stable short version string from factor params."""
    if not params:
        return "v1.0"
    canonical = json.dumps(params, sort_keys=True, ensure_ascii=False)
    h = abs(hash(canonical)) % 0xFFFFFF
    return f"v1.{h:06x}"


def _window_for(factor) -> int:
    raw = factor.params.get("window") or factor.params.get("lookback") or factor.params.get("days")
    if raw is not None:
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            pass
    return _DEFAULT_WINDOW.get(factor.kind, 20)
