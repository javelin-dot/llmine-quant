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


def _slippage_variants(baseline_bps: float) -> list[tuple[str, float]]:
    """Five-point slippage sweep around the baseline."""
    candidates = sorted({0.0, max(0.0, baseline_bps - 5), baseline_bps, baseline_bps + 5, baseline_bps + 20})
    return [(f"slippage={bps:.1f}bps", bps) for bps in candidates if bps != baseline_bps]


async def run_sensitivity_analysis(
    engine: DailyBacktestEngine,
    config: DailyBacktestConfig,
    *,
    parent_run_id: str,
) -> list[SensitivitySummary]:
    """Persist baseline + perturbation rows for the supplied config.

    The baseline must already correspond to ``parent_run_id`` (the caller runs it).
    This function only runs the perturbations and writes ``SensitivityRun`` rows.
    """
    summaries: list[SensitivitySummary] = []

    # Re-run baseline once with raw engine.run() so metrics shape is identical.
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

    # Parameter sweep (only meaningful for dual_ma right now).
    if config.strategy_name == "dual_ma":
        for label, variant in _dual_ma_param_variants(dict(config.strategy_params)):
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
