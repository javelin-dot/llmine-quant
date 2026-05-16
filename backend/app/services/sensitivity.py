"""Parameter & slippage sensitivity analysis on top of DailyBacktestEngine.

Given a baseline backtest config, sweep a small set of perturbations and record
each variant's metrics in ``sensitivity_runs``. The variants are intentionally
small (≤ ~10 runs total) so the API can stay synchronous.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from app.domains.backtest.models import SensitivityRun
from app.services.daily_backtest import (
    BacktestCostConfig,
    BacktestMetrics,
    DailyBacktestConfig,
    DailyBacktestEngine,
    DailyBacktestResult,
)


@dataclass(frozen=True, slots=True)
class SensitivitySummary:
    """In-memory view of one perturbation outcome."""

    kind: str  # "param" / "slippage"
    label: str
    variant: dict[str, Any]
    is_baseline: bool
    metrics: BacktestMetrics


def _dual_ma_param_variants(strategy_params: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Generate small +/- step variants for short/long windows.

    Skips invalid combinations (short >= long).
    """
    short = int(strategy_params.get("short_window", 5))
    long_ = int(strategy_params.get("long_window", 20))
    out: list[tuple[str, dict[str, Any]]] = []
    for delta_short in (-1, 0, 1):
        for delta_long in (-5, 0, 5):
            if delta_short == 0 and delta_long == 0:
                continue
            new_short = max(2, short + delta_short)
            new_long = max(new_short + 1, long_ + delta_long)
            label = f"short={new_short},long={new_long}"
            variant = {**strategy_params, "short_window": new_short, "long_window": new_long}
            out.append((label, variant))
    return out


def _momentum_param_variants(strategy_params: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Sweep lookback / skip / max_positions around momentum baseline."""
    lookback = int(strategy_params.get("lookback", 20))
    skip = int(strategy_params.get("skip", 1))
    max_pos = int(strategy_params.get("max_positions", 5))
    out: list[tuple[str, dict[str, Any]]] = []
    for new_lb in {max(5, lookback - 5), max(5, lookback - 10), lookback + 5, lookback + 10}:
        if new_lb == lookback:
            continue
        variant = {**strategy_params, "lookback": new_lb}
        out.append((f"lookback={new_lb}", variant))
    for new_skip in {max(0, skip - 1), skip + 1, skip + 2}:
        if new_skip == skip:
            continue
        variant = {**strategy_params, "skip": new_skip}
        out.append((f"skip={new_skip}", variant))
    for new_max in {max(1, max_pos - 2), max_pos + 2, max_pos + 5}:
        if new_max == max_pos:
            continue
        variant = {**strategy_params, "max_positions": new_max}
        out.append((f"max_positions={new_max}", variant))
    return out


def _mean_reversion_param_variants(strategy_params: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Sweep lookback / z_threshold around mean-reversion baseline."""
    lookback = int(strategy_params.get("lookback", 20))
    z = float(strategy_params.get("z_threshold", 1.5))
    out: list[tuple[str, dict[str, Any]]] = []
    for new_lb in {max(5, lookback - 5), max(5, lookback - 10), lookback + 5, lookback + 10}:
        if new_lb == lookback:
            continue
        variant = {**strategy_params, "lookback": new_lb}
        out.append((f"lookback={new_lb}", variant))
    for delta in (-0.5, -0.25, 0.25, 0.5):
        new_z = round(max(0.5, z + delta), 2)
        if new_z == z:
            continue
        variant = {**strategy_params, "z_threshold": new_z}
        out.append((f"z_threshold={new_z}", variant))
    return out


def _param_variants(
    strategy_name: str, strategy_params: dict[str, Any]
) -> list[tuple[str, dict[str, Any]]]:
    if strategy_name == "dual_ma":
        return _dual_ma_param_variants(strategy_params)
    if strategy_name == "momentum":
        return _momentum_param_variants(strategy_params)
    if strategy_name == "mean_reversion":
        return _mean_reversion_param_variants(strategy_params)
    return []


def _slippage_variants(baseline_bps: float) -> list[tuple[str, float]]:
    """Five-point slippage sweep around the baseline."""
    candidates = sorted({0.0, max(0.0, baseline_bps - 5), baseline_bps, baseline_bps + 5, baseline_bps + 20})
    return [(f"slippage={bps:.1f}bps", bps) for bps in candidates if bps != baseline_bps]


async def run_sensitivity_analysis(
    engine: DailyBacktestEngine,
    config: DailyBacktestConfig,
    *,
    parent_run_id: str,
    baseline_result: DailyBacktestResult | None = None,
) -> list[SensitivitySummary]:
    """Persist baseline + perturbation rows for the supplied config.

    The baseline must already correspond to ``parent_run_id`` (the caller runs it).
    When the caller already has the baseline result it should pass it via
    ``baseline_result`` to avoid running the baseline twice.
    """
    summaries: list[SensitivitySummary] = []

    # Reuse the caller's baseline if provided — otherwise run it once.
    if baseline_result is None:
        baseline_result = await engine.run(config)
    summaries.append(
        SensitivitySummary(
            kind="param",
            label="baseline",
            variant=dict(config.strategy_params),
            is_baseline=True,
            metrics=baseline_result.metrics,
        )
    )

    for label, variant in _param_variants(config.strategy_name, dict(config.strategy_params)):
        try:
            r = await engine.run(replace(config, strategy_params=variant))
        except Exception:  # noqa: BLE001
            continue
        summaries.append(
            SensitivitySummary(
                kind="param", label=label, variant=variant, is_baseline=False, metrics=r.metrics
            )
        )

    # Slippage sweep.
    baseline_cost = config.cost_config
    for label, bps in _slippage_variants(baseline_cost.slippage_bps):
        new_cost = BacktestCostConfig(
            commission_rate=baseline_cost.commission_rate,
            min_commission=baseline_cost.min_commission,
            stamp_tax_rate=baseline_cost.stamp_tax_rate,
            slippage_bps=bps,
        )
        try:
            r = await engine.run(replace(config, cost_config=new_cost))
        except Exception:  # noqa: BLE001
            continue
        summaries.append(
            SensitivitySummary(
                kind="slippage",
                label=label,
                variant={"slippage_bps": bps},
                is_baseline=False,
                metrics=r.metrics,
            )
        )

    for s in summaries:
        engine.session.add(
            SensitivityRun(
                parent_run_id=parent_run_id,
                kind=s.kind,
                label=s.label,
                variant_json=json.dumps(s.variant, ensure_ascii=False),
                is_baseline=s.is_baseline,
                cumulative_return=s.metrics.cumulative_return,
                annual_return=s.metrics.annual_return,
                max_drawdown=s.metrics.max_drawdown,
                sharpe_ratio=s.metrics.sharpe_ratio,
                win_rate=s.metrics.win_rate,
                turnover=s.metrics.turnover,
            )
        )
    await engine.session.commit()
    return summaries
