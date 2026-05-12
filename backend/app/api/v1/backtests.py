"""Backtest Service API — backtest tasks, runs, reports, equity curves."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.backtest.models import (
    BacktestMetric,
    BacktestRun,
    BacktestTask,
    BacktestTrade,
    EquityPoint,
    SensitivityRun as SensitivityRunModel,
    WalkForwardFold as WalkForwardFoldModel,
)
from app.domains.data.models import FeatureSet, FeatureUsage, LineageEdge
from app.domains.backtest.schemas import (
    BacktestComparisonRow,
    BacktestCostIn,
    BacktestCreateIn,
    BacktestEquityPointOut,
    BacktestMetricOut,
    BacktestReportOut,
    BacktestScreen,
    BacktestTaskListItem,
    BacktestTaskResultOut,
    BacktestTradeOut,
    ConfidenceFeature,
    ConfidenceTower,
    CurvePoint,
    EquityCurve,
    Kpi,
    ParameterHeatmap,
    StressScenario,
    OverfitAssessmentOut,
    OverfitComponentOut,
    SensitivityCreateIn,
    SensitivityResultOut,
    SensitivityRunOut,
    WalkForwardCreateIn,
    WalkForwardFold,
    WalkForwardFoldOut,
    WalkForwardResultOut,
)
from app.services.daily_backtest import BacktestCostConfig, BacktestDataError, DailyBacktestConfig, DailyBacktestEngine
from app.services.overfitting import assess_overfitting
from app.services.sensitivity import run_sensitivity_analysis

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]

_KPIS = [
    Kpi(label="累计收益", value="+37.0%", trend="▲", tone="green"),
    Kpi(label="年化收益", value="+18.5%", trend="▲", tone="green"),
    Kpi(label="最大回撤", value="-12.3%", trend="▼", tone="yellow"),
    Kpi(label="夏普比率", value="1.34", trend="▲", tone="green"),
    Kpi(label="胜率", value="58.2%", trend="▲", tone="green"),
    Kpi(label="盈亏比", value="1.82", trend="▲", tone="green"),
]

_EQUITY_CURVE = EquityCurve(
    label="MA趋势策略",
    inSample=[
        CurvePoint(date="2024-01-02", value=1.0),
        CurvePoint(date="2024-02-01", value=1.05),
        CurvePoint(date="2024-03-01", value=1.12),
        CurvePoint(date="2024-04-01", value=1.18),
        CurvePoint(date="2024-05-01", value=1.25),
        CurvePoint(date="2024-06-01", value=1.30),
        CurvePoint(date="2024-07-01", value=1.28),
        CurvePoint(date="2024-08-01", value=1.35),
    ],
    outSample=[
        CurvePoint(date="2024-09-01", value=1.38),
        CurvePoint(date="2024-10-01", value=1.32),
        CurvePoint(date="2024-11-01", value=1.40),
        CurvePoint(date="2024-12-01", value=1.37),
    ],
    drawdown=[
        CurvePoint(date="2024-01-02", value=0.0),
        CurvePoint(date="2024-02-01", value=-0.02),
        CurvePoint(date="2024-03-01", value=-0.01),
        CurvePoint(date="2024-04-01", value=-0.05),
        CurvePoint(date="2024-05-01", value=-0.03),
        CurvePoint(date="2024-06-01", value=-0.08),
        CurvePoint(date="2024-07-01", value=-0.12),
        CurvePoint(date="2024-08-01", value=-0.09),
        CurvePoint(date="2024-09-01", value=-0.06),
        CurvePoint(date="2024-10-01", value=-0.10),
        CurvePoint(date="2024-11-01", value=-0.04),
        CurvePoint(date="2024-12-01", value=-0.07),
    ],
)

_CONFIDENCE = ConfidenceTower(
    score=78,
    label="稳健",
    features=[
        ConfidenceFeature(title="IS/OOS 比率", desc="样本外收益 / 样本内收益", score="0.68", tone="green"),
        ConfidenceFeature(title="参数稳定性", desc="参数扰动后收益变化", score="0.72", tone="green"),
        ConfidenceFeature(title="滑点敏感性", desc="+1‰ 滑点对收益影响", score="-3.2%", tone="yellow"),
        ConfidenceFeature(title="夏普比率衰减", desc="OOS 夏普 / IS 夏普", score="0.65", tone="green"),
        ConfidenceFeature(title="最大回撤一致性", desc="IS 与 OOS 回撤差异", score="+2.1%", tone="yellow"),
    ],
)

_WALK_FORWARD = {
    "folds": [
        WalkForwardFold(period="2023 Q1", isReturn=0.08, oosReturn=0.06),
        WalkForwardFold(period="2023 Q2", isReturn=0.12, oosReturn=0.09),
        WalkForwardFold(period="2023 Q3", isReturn=0.05, oosReturn=0.04),
        WalkForwardFold(period="2023 Q4", isReturn=0.10, oosReturn=0.08),
        WalkForwardFold(period="2024 Q1", isReturn=0.15, oosReturn=0.11),
    ]
}

_COMPARISON = [
    BacktestComparisonRow(id="s1", name="MA趋势", family="trend", annualReturn=0.185, maxDd=-0.123, sharpe=1.34, oosScore=78, overfit="low", status="live", sparkline=[1.0, 1.02, 1.05, 1.08, 1.12, 1.15, 1.18]),
    BacktestComparisonRow(id="s2", name="价值选股", family="value", annualReturn=0.221, maxDd=-0.098, sharpe=1.56, oosScore=85, overfit="low", status="paper", sparkline=[1.0, 1.03, 1.06, 1.09, 1.13, 1.17, 1.20]),
    BacktestComparisonRow(id="s3", name="行业轮动", family="rotation", annualReturn=0.152, maxDd=-0.156, sharpe=1.12, oosScore=72, overfit="medium", status="live", sparkline=[1.0, 1.01, 1.03, 1.02, 1.05, 1.08, 1.10]),
    BacktestComparisonRow(id="s4", name="XGBoost", family="ml", annualReturn=0.284, maxDd=-0.189, sharpe=1.42, oosScore=91, overfit="low", status="backtest", sparkline=[1.0, 1.04, 1.08, 1.12, 1.16, 1.20, 1.24]),
]

_SCENARIOS = [
    StressScenario(id="sc1", name="2015 股灾", severity="high", loss="-18.5%", maxDd="-25.3%", fuse="触发 L2", fuseTone="red", suggestion="降低仓位至 50%，暂停新开仓", human="需人工确认"),
    StressScenario(id="sc2", name="2018 熊市", severity="medium", loss="-12.1%", maxDd="-15.8%", fuse="触发 L1", fuseTone="yellow", suggestion="减仓至 70%，加强监控", human="自动处理"),
    StressScenario(id="sc3", name="2020 疫情", severity="high", loss="-22.3%", maxDd="-28.1%", fuse="触发 L3", fuseTone="red", suggestion="清仓观察", human="需人工确认"),
    StressScenario(id="sc4", name="2024 震荡", severity="low", loss="-5.2%", maxDd="-8.1%", fuse="未触发", fuseTone="green", suggestion="维持当前仓位", human="自动处理"),
]

_HEATMAP = ParameterHeatmap(
    xLabel="MA短周期",
    yLabel="MA长周期",
    xTicks=["3", "5", "10", "15", "20"],
    yTicks=["10", "20", "30", "60", "120"],
    cells=[
        [0.12, 0.15, 0.18, 0.14, 0.10],
        [0.14, 0.19, 0.22, 0.18, 0.13],
        [0.11, 0.16, 0.20, 0.17, 0.12],
        [0.09, 0.13, 0.16, 0.15, 0.11],
        [0.07, 0.10, 0.12, 0.11, 0.08],
    ],
    bestX=2,
    bestY=1,
)


@router.get("/overview", response_model=BacktestScreen)
async def get_backtest_overview(db: DbSession) -> BacktestScreen:
    """Return the complete Backtest Lab screen data."""
    return BacktestScreen(
        kpis=_KPIS,
        equityCurves=_EQUITY_CURVE,
        confidence=_CONFIDENCE,
        walkForward=_WALK_FORWARD,
        comparison=_COMPARISON,
        scenarios=_SCENARIOS,
        parameterHeatmap=_HEATMAP,
    )


@router.post("/", response_model=BacktestTaskResultOut)
async def create_backtest_task(
    payload: BacktestCreateIn,
    db: DbSession,
) -> BacktestTaskResultOut:
    """Create, execute and persist a research backtest task."""
    engine = DailyBacktestEngine(db)
    try:
        result = await engine.run_and_persist(_daily_backtest_config(payload))
    except (BacktestDataError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _result_out(result)


@router.post("/sensitivity", response_model=SensitivityResultOut)
async def create_sensitivity_analysis(
    payload: SensitivityCreateIn,
    db: DbSession,
) -> SensitivityResultOut:
    """Run baseline backtest + small parameter and slippage sweep."""
    engine = DailyBacktestEngine(db)
    config = DailyBacktestConfig(
        universe=tuple(payload.universe),
        start_date=payload.start_date,
        end_date=payload.end_date,
        strategy_name=payload.strategy_name,
        initial_cash=payload.initial_cash,
        strategy_params=payload.strategy_params,
        cost_config=_cost_config(payload.cost_config),
    )
    try:
        baseline = await engine.run_and_persist(config)
        assert baseline.run_id is not None
        summaries = await run_sensitivity_analysis(engine, config, parent_run_id=baseline.run_id)
    except (BacktestDataError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SensitivityResultOut(
        task_id=baseline.task_id or "",
        run_id=baseline.run_id,
        runs=[
            SensitivityRunOut(
                kind=s.kind,
                label=s.label,
                is_baseline=s.is_baseline,
                cumulative_return=s.metrics.cumulative_return,
                annual_return=s.metrics.annual_return,
                max_drawdown=s.metrics.max_drawdown,
                sharpe_ratio=s.metrics.sharpe_ratio,
                win_rate=s.metrics.win_rate,
                turnover=s.metrics.turnover,
            )
            for s in summaries
        ],
    )


@router.post("/walk-forward", response_model=WalkForwardResultOut)
async def create_walk_forward_backtest(
    payload: WalkForwardCreateIn,
    db: DbSession,
) -> WalkForwardResultOut:
    """Run a walk-forward analysis and persist folds + parent backtest."""
    engine = DailyBacktestEngine(db)
    config = DailyBacktestConfig(
        universe=tuple(payload.universe),
        start_date=payload.start_date,
        end_date=payload.end_date,
        strategy_name=payload.strategy_name,
        initial_cash=payload.initial_cash,
        strategy_params=payload.strategy_params,
        cost_config=_cost_config(payload.cost_config),
    )
    try:
        result, summaries = await engine.run_walk_forward(
            config, folds=payload.folds, train_ratio=payload.train_ratio
        )
    except (BacktestDataError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return WalkForwardResultOut(
        task_id=result.task_id or "",
        run_id=result.run_id or "",
        aggregate=BacktestMetricOut(
            cumulative_return=result.metrics.cumulative_return,
            annual_return=result.metrics.annual_return,
            max_drawdown=result.metrics.max_drawdown,
            sharpe_ratio=result.metrics.sharpe_ratio,
            win_rate=result.metrics.win_rate,
            turnover=result.metrics.turnover,
        ),
        folds=[
            WalkForwardFoldOut(
                fold_index=s.fold_index,
                train_start=s.train_start,
                train_end=s.train_end,
                test_start=s.test_start,
                test_end=s.test_end,
                train_return=s.train_metrics.cumulative_return,
                test_return=s.test_metrics.cumulative_return,
                train_sharpe=s.train_metrics.sharpe_ratio,
                test_sharpe=s.test_metrics.sharpe_ratio,
                train_max_dd=s.train_metrics.max_drawdown,
                test_max_dd=s.test_metrics.max_drawdown,
            )
            for s in summaries
        ],
    )


@router.get("/{task_id}", response_model=BacktestTaskResultOut)
async def get_backtest_task(task_id: str, db: DbSession) -> BacktestTaskResultOut:
    """Get a persisted backtest task and its latest run result."""
    task = await db.get(BacktestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="backtest task not found")

    run = (
        await db.execute(
            select(BacktestRun)
            .where(BacktestRun.task_id == task.id)
            .order_by(BacktestRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        return BacktestTaskResultOut(task_id=task.id, status=task.status)

    metrics = (
        await db.execute(select(BacktestMetric).where(BacktestMetric.run_id == run.id))
    ).scalars().all()
    equity_points = (
        await db.execute(
            select(EquityPoint)
            .where(EquityPoint.run_id == run.id)
            .order_by(EquityPoint.trade_date)
        )
    ).scalars().all()
    return _persisted_result_out(
        task, run, list(metrics), list(equity_points), _split_date_from_task(task)
    )


@router.get("/", response_model=list[BacktestTaskListItem])
async def list_backtest_tasks(db: DbSession, limit: int = 20) -> list[BacktestTaskListItem]:
    """List recent backtest tasks with summary metrics for the workbench history panel."""
    import json as _json

    task_rows = (
        await db.execute(
            select(BacktestTask)
            .where(BacktestTask.deleted_at.is_(None))
            .order_by(BacktestTask.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    items: list[BacktestTaskListItem] = []
    for t in task_rows:
        config_payload: dict = {}
        if t.config:
            try:
                config_payload = _json.loads(t.config)
            except Exception:  # noqa: BLE001
                config_payload = {}
        run = (
            await db.execute(
                select(BacktestRun)
                .where(BacktestRun.task_id == t.id)
                .order_by(BacktestRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        metric = None
        if run is not None:
            metric = (
                await db.execute(
                    select(BacktestMetric).where(
                        BacktestMetric.run_id == run.id, BacktestMetric.segment == "all"
                    )
                )
            ).scalar_one_or_none()
        items.append(
            BacktestTaskListItem(
                task_id=t.id,
                run_id=run.id if run else None,
                status=t.status,
                strategy_version_id=t.strategy_version_id,
                strategy_name=config_payload.get("strategy_name"),
                start_date=config_payload.get("start_date"),
                end_date=config_payload.get("end_date"),
                in_sample_end_date=config_payload.get("in_sample_end_date"),
                universe=list(config_payload.get("universe", [])),
                cumulative_return=metric.cumulative_return if metric else None,
                sharpe_ratio=metric.sharpe_ratio if metric else None,
                max_drawdown=metric.max_drawdown if metric else None,
                overfit_level=metric.overfit_level if metric else None,
                created_at=t.created_at.isoformat() if t.created_at else "",
            )
        )
    return items


@router.get("/{task_id}/trades", response_model=list[BacktestTradeOut])
async def get_backtest_trades(
    task_id: str,
    db: DbSession,
    limit: int = 500,
) -> list[BacktestTradeOut]:
    """Return persisted trades for a backtest task — each carries the rule reason."""
    task = await db.get(BacktestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="backtest task not found")
    run = (
        await db.execute(
            select(BacktestRun)
            .where(BacktestRun.task_id == task.id)
            .order_by(BacktestRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        return []
    trades = (
        await db.execute(
            select(BacktestTrade)
            .where(BacktestTrade.run_id == run.id)
            .order_by(BacktestTrade.trade_date.asc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        BacktestTradeOut(
            trade_date=t.trade_date,
            symbol=t.symbol,
            side=t.side,
            quantity=t.quantity,
            price=t.price,
            amount=t.amount,
            target_weight=t.target_weight,
            total_cost=t.total_cost,
            net_cash_flow=t.net_cash_flow,
            reason=t.reason,
        )
        for t in trades
    ]


@router.get("/{task_id}/report", response_model=BacktestReportOut)
async def get_backtest_report(task_id: str, db: DbSession) -> BacktestReportOut:
    """Unified Phase 3 report — IS/OOS + walk-forward + sensitivity + overfit + trades + lineage."""
    task = await db.get(BacktestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="backtest task not found")
    summary = await get_backtest_task(task_id, db)
    run_id = summary.run_id

    folds: list[WalkForwardFoldOut] = []
    sens: list[SensitivityRunOut] = []
    overfit: OverfitAssessmentOut | None = None
    trades: list[BacktestTradeOut] = []
    feature_rows: list[dict[str, str | None]] = []
    lineage_node_count = 0
    lineage_edge_count = 0

    if run_id:
        fold_rows = (
            await db.execute(
                select(WalkForwardFoldModel)
                .where(WalkForwardFoldModel.run_id == run_id)
                .order_by(WalkForwardFoldModel.fold_index)
            )
        ).scalars().all()
        folds = [
            WalkForwardFoldOut(
                fold_index=f.fold_index,
                train_start=f.train_start,
                train_end=f.train_end,
                test_start=f.test_start,
                test_end=f.test_end,
                train_return=f.train_return or 0.0,
                test_return=f.test_return or 0.0,
                train_sharpe=f.train_sharpe or 0.0,
                test_sharpe=f.test_sharpe or 0.0,
                train_max_dd=f.train_max_dd or 0.0,
                test_max_dd=f.test_max_dd or 0.0,
            )
            for f in fold_rows
        ]

        sens_rows = (
            await db.execute(
                select(SensitivityRunModel).where(SensitivityRunModel.parent_run_id == run_id)
            )
        ).scalars().all()
        sens = [
            SensitivityRunOut(
                kind=s.kind,
                label=s.label,
                is_baseline=bool(s.is_baseline),
                cumulative_return=s.cumulative_return or 0.0,
                annual_return=s.annual_return or 0.0,
                max_drawdown=s.max_drawdown or 0.0,
                sharpe_ratio=s.sharpe_ratio or 0.0,
                win_rate=s.win_rate or 0.0,
                turnover=s.turnover or 0.0,
            )
            for s in sens_rows
        ]

        # Re-compute (and persist) overfit so the report is always fresh.
        assessment = await assess_overfitting(db, run_id)
        overfit = OverfitAssessmentOut(
            score=assessment.score,
            level=assessment.level,
            components=[
                OverfitComponentOut(name=c.name, score=c.score, detail=c.detail)
                for c in assessment.components
            ],
        )

        trade_rows = (
            await db.execute(
                select(BacktestTrade)
                .where(BacktestTrade.run_id == run_id)
                .order_by(BacktestTrade.trade_date.asc())
            )
        ).scalars().all()
        trades = [
            BacktestTradeOut(
                trade_date=t.trade_date,
                symbol=t.symbol,
                side=t.side,
                quantity=t.quantity,
                price=t.price,
                amount=t.amount,
                target_weight=t.target_weight,
                total_cost=t.total_cost,
                net_cash_flow=t.net_cash_flow,
                reason=t.reason,
            )
            for t in trade_rows
        ]

        usage_rows = (
            await db.execute(
                select(FeatureUsage, FeatureSet)
                .join(FeatureSet, FeatureSet.id == FeatureUsage.feature_id)
                .where(FeatureUsage.backtest_run_id == run_id)
            )
        ).all()
        feature_rows = [
            {
                "featureId": u.feature_id,
                "featureName": f.name,
                "featureVersion": f.version,
                "role": u.role,
            }
            for (u, f) in usage_rows
        ]

        edge_rows = (
            await db.execute(select(LineageEdge).where(LineageEdge.backtest_run_id == run_id))
        ).scalars().all()
        lineage_edge_count = len(edge_rows)
        lineage_node_count = len({e.from_node_id for e in edge_rows} | {e.to_node_id for e in edge_rows})

    return BacktestReportOut(
        task_id=task_id,
        run_id=run_id,
        summary=summary,
        walk_forward_folds=folds,
        sensitivity_runs=sens,
        overfit=overfit,
        trades=trades,
        feature_usage=feature_rows,
        lineage_node_count=lineage_node_count,
        lineage_edge_count=lineage_edge_count,
    )


@router.get("/{task_id}/overfit", response_model=OverfitAssessmentOut)
async def get_overfit_assessment(task_id: str, db: DbSession) -> OverfitAssessmentOut:
    """Compute (or recompute) the overfitting score for a backtest task."""
    task = await db.get(BacktestTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="backtest task not found")
    run = (
        await db.execute(
            select(BacktestRun)
            .where(BacktestRun.task_id == task.id)
            .order_by(BacktestRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="no run found for task")

    assessment = await assess_overfitting(db, run.id)
    return OverfitAssessmentOut(
        score=assessment.score,
        level=assessment.level,
        components=[
            OverfitComponentOut(name=c.name, score=c.score, detail=c.detail)
            for c in assessment.components
        ],
    )


def _split_date_from_task(task: BacktestTask) -> str | None:
    import json as _json

    if not task.config:
        return None
    try:
        return _json.loads(task.config).get("in_sample_end_date")
    except Exception:  # noqa: BLE001
        return None


def _daily_backtest_config(payload: BacktestCreateIn) -> DailyBacktestConfig:
    return DailyBacktestConfig(
        universe=tuple(payload.universe),
        start_date=payload.start_date,
        end_date=payload.end_date,
        strategy_name=payload.strategy_name,
        initial_cash=payload.initial_cash,
        strategy_params=payload.strategy_params,
        cost_config=_cost_config(payload.cost_config),
        in_sample_end_date=payload.in_sample_end_date,
    )


def _cost_config(payload: BacktestCostIn) -> BacktestCostConfig:
    return BacktestCostConfig(
        commission_rate=payload.commission_rate,
        min_commission=payload.min_commission,
        stamp_tax_rate=payload.stamp_tax_rate,
        slippage_bps=payload.slippage_bps,
    )


def _result_out(result) -> BacktestTaskResultOut:
    def _runtime_metrics(m) -> BacktestMetricOut:
        return BacktestMetricOut(
            cumulative_return=m.cumulative_return,
            annual_return=m.annual_return,
            max_drawdown=m.max_drawdown,
            sharpe_ratio=m.sharpe_ratio,
            win_rate=m.win_rate,
            turnover=m.turnover,
        )

    split_date = result.in_sample_end_date

    def _phase_for(date_str: str) -> str:
        return "oos" if split_date is not None and date_str > split_date else "is"

    return BacktestTaskResultOut(
        task_id=result.task_id or "",
        status="completed",
        run_id=result.run_id,
        metrics=_runtime_metrics(result.metrics),
        in_sample_metrics=_runtime_metrics(result.is_metrics) if result.is_metrics else None,
        out_sample_metrics=_runtime_metrics(result.oos_metrics) if result.oos_metrics else None,
        in_sample_end_date=split_date,
        equity_curve=[
            BacktestEquityPointOut(
                trade_date=point.trade_date,
                value=point.value,
                drawdown=point.drawdown,
                phase=_phase_for(point.trade_date),
            )
            for point in result.equity_curve
        ],
    )


def _persisted_result_out(
    task: BacktestTask,
    run: BacktestRun,
    metrics: list[BacktestMetric],
    equity_points: list[EquityPoint],
    in_sample_end_date: str | None,
) -> BacktestTaskResultOut:
    by_segment: dict[str, BacktestMetric] = {m.segment: m for m in metrics}
    return BacktestTaskResultOut(
        task_id=task.id,
        status=task.status,
        run_id=run.id,
        metrics=_metric_out(by_segment.get("all")) if "all" in by_segment else None,
        in_sample_metrics=_metric_out(by_segment.get("is")) if "is" in by_segment else None,
        out_sample_metrics=_metric_out(by_segment.get("oos")) if "oos" in by_segment else None,
        in_sample_end_date=in_sample_end_date,
        equity_curve=[
            BacktestEquityPointOut(
                trade_date=point.trade_date,
                value=point.value,
                drawdown=point.drawdown,
                phase=point.phase or "is",
            )
            for point in equity_points
        ],
    )


def _metric_out(metric: BacktestMetric | None) -> BacktestMetricOut | None:
    if metric is None:
        return None
    return BacktestMetricOut(
        cumulative_return=metric.cumulative_return or 0.0,
        annual_return=metric.annual_return or 0.0,
        max_drawdown=metric.max_drawdown or 0.0,
        sharpe_ratio=metric.sharpe_ratio or 0.0,
        win_rate=metric.win_rate or 0.0,
        turnover=metric.turnover or 0.0,
    )
