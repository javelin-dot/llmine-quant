"""Load and mutate Explain screen data from relational tables."""

from __future__ import annotations

from statistics import mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_class import now_utc
from app.domains.explain.models import (
    AttributionItem,
    BiasGateCheck,
    ConfidenceRadarAxis,
    DecisionStep,
    LineageRecord,
    SignalExplanation,
    SimilarCase,
)
from app.domains.explain.schemas import (
    AttributionItemOut,
    AttributionOut,
    BiasGateOut,
    ConfidenceRadar,
    DecisionChainStep,
    ExplainApproveOut,
    ExplainScreen,
    LineageStep,
    RadarAxis,
    SignalHeader,
    SimilarCaseOut,
    SimilarHistory,
)

_PENDING_HITL_SUMMARY = "待人工确认"
_PENDING_HITL_DETAIL = "该信号名义金额超过单票限额 80%，需人工审批"
_APPROVED_HITL_SUMMARY = "人工审批已通过"
_APPROVED_HITL_DETAIL = (
    "Explain 工作台已确认放行；决策链闭环。系统将推送至 Execution Agent，按 trace "
    "幂等与审计策略排队执行。"
)


def _signal_action(act: str) -> str:
    up = act.strip().upper()
    return up if up in {"BUY", "SELL", "HOLD"} else "HOLD"


def _tone_signal_header(raw: str | None) -> str:
    return raw if raw in {"green", "yellow", "red", "blue"} else "yellow"


def _tone_attribution(raw: str | None) -> str:
    return raw if raw in {"green", "yellow", "red"} else "yellow"


def _tone_chain(raw: str | None) -> str:
    return raw if raw in {"green", "yellow", "red", "blue", "purple"} else "blue"


def _tone_lineage_perm(raw: str | None) -> str:
    return raw if raw in {"green", "yellow", "red"} else "green"


def _bias_status(raw: str) -> str:
    return raw if raw in {"pass", "watch", "fail", "enforced"} else "pass"


async def fetch_explanation(session: AsyncSession, trace_id: str | None) -> SignalExplanation | None:
    base = select(SignalExplanation).where(SignalExplanation.deleted_at.is_(None))
    if trace_id:
        stmt = base.where(SignalExplanation.trace_id == trace_id).limit(1)
        return await session.scalar(stmt)
    stmt = base.order_by(SignalExplanation.updated_at.desc()).limit(1)
    return await session.scalar(stmt)


async def explanation_to_screen(session: AsyncSession, exp: SignalExplanation) -> ExplainScreen:
    attribution_items_result = (
        await session.scalars(
            select(AttributionItem)
            .where(AttributionItem.explanation_id == exp.id, AttributionItem.deleted_at.is_(None))
            .order_by(AttributionItem.sort_order, AttributionItem.id)
        )
    ).all()

    radar_axes_rows = (
        await session.scalars(
            select(ConfidenceRadarAxis)
            .where(ConfidenceRadarAxis.explanation_id == exp.id, ConfidenceRadarAxis.deleted_at.is_(None))
            .order_by(ConfidenceRadarAxis.sort_order, ConfidenceRadarAxis.id)
        )
    ).all()

    chain_rows = (
        await session.scalars(
            select(DecisionStep)
            .where(DecisionStep.explanation_id == exp.id, DecisionStep.deleted_at.is_(None))
            .order_by(DecisionStep.step)
        )
    ).all()

    lineage_rows = (
        await session.scalars(
            select(LineageRecord)
            .where(LineageRecord.explanation_id == exp.id, LineageRecord.deleted_at.is_(None))
            .order_by(LineageRecord.created_at)
        )
    ).all()

    bias_rows = (
        await session.scalars(
            select(BiasGateCheck)
            .where(BiasGateCheck.explanation_id == exp.id, BiasGateCheck.deleted_at.is_(None))
            .order_by(BiasGateCheck.created_at)
        )
    ).all()

    similar_case_rows = (
        await session.scalars(
            select(SimilarCase)
            .where(SimilarCase.explanation_id == exp.id, SimilarCase.deleted_at.is_(None))
            .order_by(SimilarCase.date.desc())
        )
    ).all()

    trace_disp = exp.trace_id or ""

    strat_label = exp.strategy_name or ""

    attribution = AttributionOut(
        base=exp.attribution_base if exp.attribution_base is not None else 0.0,
        items=[
            AttributionItemOut(name=i.name, value=i.value, desc=i.detail or "")
            for i in attribution_items_result
        ],
        final=exp.attribution_final if exp.attribution_final is not None else 0.0,
        decision=(exp.attribution_decision or "—"),
        decisionTone=_tone_attribution(exp.attribution_decision_tone),  # type: ignore[arg-type]
    )

    radar_axis_schemas = [
        RadarAxis(name=a.axis_name, score=a.score, desc=a.axis_detail or "") for a in radar_axes_rows
    ]
    if not radar_axis_schemas:
        radar_axis_schemas = [RadarAxis(name="—", score=0.0, desc="未配置置信度轴")]
    avg = (
        exp.radar_avg
        if exp.radar_avg is not None
        else mean([a.score for a in radar_axis_schemas]) if radar_axis_schemas else 0.0
    )
    radar = ConfidenceRadar(axes=radar_axis_schemas, avg=avg)

    chain = [
        DecisionChainStep(
            step=r.step,
            title=r.title,
            desc=r.summary or "",
            detail=r.detail or "",
            tag=r.tag or "",
            tone=_tone_chain(r.tone),  # type: ignore[arg-type]
        )
        for r in chain_rows
    ]

    lineage = [
        LineageStep(
            step=row.step,
            version=row.version,
            hash=row.content_hash,
            permission=row.permission,
            permissionTone=_tone_lineage_perm(row.permission_tone),  # type: ignore[arg-type]
            detail=row.detail or "",
        )
        for row in lineage_rows
    ]

    gates = [
        BiasGateOut(
            check=b.gate_name,
            status=_bias_status(b.status),  # type: ignore[arg-type]
            desc=b.gate_detail or "",
        )
        for b in bias_rows
    ]

    cases = [_similar_case_to_out(c) for c in similar_case_rows]

    hist = SimilarHistory(
        summary=exp.similar_summary or "",
        winRate=exp.similar_win_rate or 0.0,
        avgReturn=exp.similar_avg_return or 0.0,
        cases=cases,
    )

    header = SignalHeader(
        strategy=strat_label,
        action=_signal_action(exp.action),  # type: ignore[arg-type]
        target=exp.target,
        size=exp.size,
        confidence=float(exp.confidence),
        riskGrade=exp.risk_grade or "—",
        traceId=trace_disp,
        timestamp=exp.timestamp,
        status=exp.status,
        statusTone=_tone_signal_header(exp.status_tone),  # type: ignore[arg-type]
    )

    return ExplainScreen(
        signalHeader=header,
        attribution=attribution,
        confidenceRadar=radar,
        decisionChain=chain,
        lineage=lineage,
        biasGate=gates,
        similarHistory=hist,
    )


def _similar_case_to_out(row: SimilarCase) -> SimilarCaseOut:
    ret = row.return_pct
    ret_f = float(ret) if ret is not None else 0.0
    note_text = row.note or row.outcome or ""
    success = row.success
    if success is None and ret_f > 0:
        success = True
    elif success is None:
        success = False
    return SimilarCaseOut(
        id=row.id,
        date=row.date or "",
        action=row.action or "—",
        ret=ret_f,
        days=row.days or 5,
        success=bool(success),
        note=note_text,
    )


def explain_empty_screen() -> ExplainScreen:
    """Placeholder screen when no persisted signal explanation exists."""
    return ExplainScreen(
        signalHeader=SignalHeader(
            strategy="",
            action="HOLD",
            target="",
            size="",
            confidence=0.0,
            riskGrade="—",
            traceId="",
            timestamp="—",
            status="暂无数据",
            statusTone="yellow",
        ),
        attribution=AttributionOut(
            base=0.0,
            items=[],
            final=0.0,
            decision="—",
            decisionTone="yellow",
        ),
        confidenceRadar=ConfidenceRadar(
            axes=[RadarAxis(name="—", score=0.0, desc="暂无解释数据")],
            avg=0.0,
        ),
        decisionChain=[],
        lineage=[],
        biasGate=[],
        similarHistory=SimilarHistory(summary="", winRate=0.0, avgReturn=0.0, cases=[]),
    )


async def get_explain_screen(session: AsyncSession, trace_id: str | None = None) -> ExplainScreen:
    exp = await fetch_explanation(session, trace_id)
    if exp is None:
        return explain_empty_screen()
    return await explanation_to_screen(session, exp)


async def approve_explain_trace(session: AsyncSession, trace_id: str) -> ExplainApproveOut:
    exp = await fetch_explanation(session, trace_id)
    if exp is None or exp.trace_id != trace_id:
        from app.core.errors import LLMineException

        raise LLMineException(message="未知的 trace。", status_code=404, code="explain_invalid_trace")

    if exp.approved_at is not None:
        await session.refresh(exp)
        return ExplainApproveOut(traceId=trace_id, status="already_approved")

    exp.status = "已批准"
    exp.status_tone = "green"
    exp.approved_at = now_utc()
    exp.updated_at = now_utc()

    step5 = await session.scalar(
        select(DecisionStep).where(
            DecisionStep.explanation_id == exp.id,
            DecisionStep.step == 5,
            DecisionStep.deleted_at.is_(None),
        )
    )
    if step5 is not None:
        step5.summary = _APPROVED_HITL_SUMMARY
        step5.detail = _APPROVED_HITL_DETAIL
        step5.tone = "green"
        step5.tag = step5.tag or "HITL"
        step5.updated_at = now_utc()

    await session.commit()
    await session.refresh(exp)
    return ExplainApproveOut(traceId=trace_id, status="approved")
