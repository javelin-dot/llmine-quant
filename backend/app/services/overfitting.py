"""Overfitting score for a completed backtest run.

The score is built from up to four signals (each in [0, 1] where 1 = least
overfit), then averaged into a 0–100 score and bucketed into low / medium /
high. Missing components are skipped, so a baseline run with no IS/OOS split
still gets a partial score.

Components:
    - IS/OOS Sharpe ratio decay
    - IS/OOS drawdown consistency
    - Walk-forward train→test return continuity
    - Parameter sensitivity stability (std of cumulative returns)
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.backtest.models import (
    BacktestMetric,
    SensitivityRun,
    WalkForwardFold,
)


@dataclass(frozen=True, slots=True)
class OverfitComponent:
    name: str
    score: float  # 0..1, 1 = least overfit
    detail: str


@dataclass(frozen=True, slots=True)
class OverfitAssessment:
    score: int  # 0..100
    level: str  # low / medium / high
    components: list[OverfitComponent]


def _bucket(score_0_to_100: int) -> str:
    if score_0_to_100 >= 70:
        return "low"
    if score_0_to_100 >= 40:
        return "medium"
    return "high"


def _is_oos_sharpe_component(metrics_by_seg: dict[str, BacktestMetric]) -> OverfitComponent | None:
    if "is" not in metrics_by_seg or "oos" not in metrics_by_seg:
        return None
    is_sharpe = metrics_by_seg["is"].sharpe_ratio or 0.0
    oos_sharpe = metrics_by_seg["oos"].sharpe_ratio or 0.0
    if is_sharpe <= 0:
        # IS already lossy; OOS is a free pass unless it's worse.
        return OverfitComponent(
            name="sharpe_decay",
            score=1.0 if oos_sharpe >= is_sharpe else 0.5,
            detail=f"is_sharpe={is_sharpe:.2f}, oos_sharpe={oos_sharpe:.2f}",
        )
    ratio = max(0.0, oos_sharpe / is_sharpe)
    score = max(0.0, min(1.0, ratio))  # ratio >= 1 -> 1.0
    return OverfitComponent(
        name="sharpe_decay",
        score=score,
        detail=f"oos_sharpe/is_sharpe={ratio:.2f}",
    )


def _is_oos_drawdown_component(metrics_by_seg: dict[str, BacktestMetric]) -> OverfitComponent | None:
    if "is" not in metrics_by_seg or "oos" not in metrics_by_seg:
        return None
    is_dd = abs(metrics_by_seg["is"].max_drawdown or 0.0)
    oos_dd = abs(metrics_by_seg["oos"].max_drawdown or 0.0)
    denom = max(is_dd, 0.01)
    diff_ratio = abs(is_dd - oos_dd) / denom
    score = max(0.0, 1.0 - min(1.0, diff_ratio))
    return OverfitComponent(
        name="drawdown_consistency",
        score=score,
        detail=f"is_dd={is_dd:.3f}, oos_dd={oos_dd:.3f}",
    )


def _walk_forward_component(folds: list[WalkForwardFold]) -> OverfitComponent | None:
    if not folds:
        return None
    ratios: list[float] = []
    for f in folds:
        train_ret = f.train_return or 0.0
        test_ret = f.test_return or 0.0
        if abs(train_ret) < 1e-6:
            ratios.append(1.0 if test_ret >= 0 else 0.3)
            continue
        # Sign agreement is the strongest signal here.
        same_sign = (train_ret >= 0 and test_ret >= 0) or (train_ret < 0 and test_ret < 0)
        magnitude_ratio = max(0.0, min(1.0, test_ret / train_ret)) if train_ret > 0 else 0.5
        ratios.append((1.0 if same_sign else 0.2) * 0.6 + magnitude_ratio * 0.4)
    avg = sum(ratios) / len(ratios)
    return OverfitComponent(
        name="walk_forward_continuity",
        score=max(0.0, min(1.0, avg)),
        detail=f"folds={len(folds)}, mean_score={avg:.2f}",
    )


def _sensitivity_component(rows: list[SensitivityRun]) -> OverfitComponent | None:
    param_rows = [r for r in rows if r.kind == "param" and not r.is_baseline]
    baseline = next((r for r in rows if r.is_baseline), None)
    if not param_rows or baseline is None or baseline.cumulative_return is None:
        return None
    baseline_ret = baseline.cumulative_return
    diffs = [
        abs((r.cumulative_return or 0.0) - baseline_ret)
        / max(abs(baseline_ret), 0.01)
        for r in param_rows
    ]
    avg_diff = sum(diffs) / len(diffs)
    score = max(0.0, 1.0 - min(1.0, avg_diff))
    return OverfitComponent(
        name="param_stability",
        score=score,
        detail=f"variants={len(param_rows)}, mean_rel_diff={avg_diff:.2f}",
    )


async def assess_overfitting(session: AsyncSession, run_id: str) -> OverfitAssessment:
    """Build and persist an overfitting assessment for ``run_id``."""
    metric_rows = (
        await session.execute(select(BacktestMetric).where(BacktestMetric.run_id == run_id))
    ).scalars().all()
    metrics_by_seg = {m.segment: m for m in metric_rows}

    folds = (
        await session.execute(select(WalkForwardFold).where(WalkForwardFold.run_id == run_id))
    ).scalars().all()
    sens = (
        await session.execute(select(SensitivityRun).where(SensitivityRun.parent_run_id == run_id))
    ).scalars().all()

    components: list[OverfitComponent] = []
    for comp in (
        _is_oos_sharpe_component(metrics_by_seg),
        _is_oos_drawdown_component(metrics_by_seg),
        _walk_forward_component(list(folds)),
        _sensitivity_component(list(sens)),
    ):
        if comp is not None:
            components.append(comp)

    if not components:
        return OverfitAssessment(score=0, level="high", components=[])

    avg = sum(c.score for c in components) / len(components)
    score = int(round(avg * 100))
    level = _bucket(score)

    # Persist back onto the "all" segment row (or first available).
    target = metrics_by_seg.get("all") or (metric_rows[0] if metric_rows else None)
    if target is not None:
        target.oos_score = avg
        target.overfit_level = level
        await session.commit()

    return OverfitAssessment(score=score, level=level, components=components)
