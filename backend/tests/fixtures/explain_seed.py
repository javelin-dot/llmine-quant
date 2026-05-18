"""Explain DB rows used only by API tests — production no longer seeds signal explanations."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import delete, select
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
from app.services.explain_persistence import fetch_explanation

FIXTURE_TRACE_ID = "trace-20260510-093115"
FIXTURE_SIGNAL_ID = "exp-signal-ma-trend-demo"

_PENDING_HITL_SUMMARY = "待人工确认"
_PENDING_HITL_DETAIL = "该信号名义金额超过单票限额 80%，需人工审批"


async def purge_explain_records(session: AsyncSession) -> None:
    """Hard-delete Explain domain rows so tests can observe an empty Explain API."""
    for model in (
        AttributionItem,
        ConfidenceRadarAxis,
        DecisionStep,
        LineageRecord,
        BiasGateCheck,
        SimilarCase,
        SignalExplanation,
    ):
        await session.execute(delete(model))
    await session.flush()


async def seed_explain_fixture_signal(session: AsyncSession) -> SignalExplanation | None:
    """Insert a deterministic Explain snapshot if missing."""
    existing = await fetch_explanation(session, FIXTURE_TRACE_ID)
    if existing is not None:
        return existing

    now = now_utc()
    exp = SignalExplanation(
        id=FIXTURE_SIGNAL_ID,
        org_id=None,
        created_at=now,
        updated_at=now,
        trace_id=FIXTURE_TRACE_ID,
        strategy_id="str-demo-ma-trend",
        strategy_name="MA趋势",
        action="BUY",
        target="贵州茅台 (600519)",
        size="100股 / ¥16.8万",
        confidence=0.92,
        risk_grade="A",
        timestamp="2026-05-10 09:31:15",
        status="待审批",
        status_tone="yellow",
        approved_at=None,
        attribution_base=0.50,
        attribution_final=0.98,
        attribution_decision="强烈买入",
        attribution_decision_tone="green",
        similar_summary="过去 3 年中，该策略在相似条件下共发出 24 次买入信号",
        similar_win_rate=0.68,
        similar_avg_return=0.052,
        radar_avg=0.88,
    )
    session.add(exp)
    await session.flush()

    attr_specs: Sequence[tuple[int, str, float, str]] = (
        (0, "趋势动量", 0.25, "MA5 > MA20，短期趋势向上"),
        (1, "成交量确认", 0.12, "成交量放大 1.8x，确认突破"),
        (2, "行业景气度", 0.08, "白酒板块动量排名前 10%"),
        (3, "估值修复", 0.05, "PE 处于历史 35% 分位"),
        (4, "情绪指标", -0.02, "市场情绪偏谨慎，轻微扣分"),
    )
    for order, name, val, d in attr_specs:
        session.add(
            AttributionItem(
                id=str(uuid4()),
                explanation_id=exp.id,
                name=name,
                value=val,
                detail=d,
                sort_order=order,
                created_at=now,
                updated_at=now,
                trace_id=None,
            )
        )

    radar_specs: Sequence[tuple[int, str, float, str]] = (
        (0, "数据质量", 0.95, "数据源完整，无缺失"),
        (1, "模型稳定性", 0.88, "过去 30 天信号一致性高"),
        (2, "因子显著性", 0.92, "动量因子 t-stat > 2.5"),
        (3, "回测表现", 0.85, "样本外夏普 1.34"),
        (4, "风险控制", 0.90, "止损位合理，仓位可控"),
        (5, "可解释性", 0.78, "决策链逻辑清晰"),
    )
    for order, nm, score, txt in radar_specs:
        session.add(
            ConfidenceRadarAxis(
                id=str(uuid4()),
                explanation_id=exp.id,
                sort_order=order,
                axis_name=nm,
                score=score,
                axis_detail=txt,
                created_at=now,
                updated_at=now,
            )
        )

    chain_specs = (
        (
            1,
            "信号生成",
            "MA趋势策略扫描全市场",
            "识别出 600519 满足 MA5 > MA20 且成交量放大",
            "Strategy",
            "blue",
        ),
        (
            2,
            "因子打分",
            "多因子模型综合评分",
            "趋势动量 0.25 + 成交量 0.12 + 行业 0.08 + 估值 0.05 = 0.50",
            "Model",
            "purple",
        ),
        (
            3,
            "风险检查",
            "三层风控系统审查",
            "通过集中度检查、VaR 检查、涨跌停检查",
            "Risk",
            "green",
        ),
        (
            4,
            "组合影响",
            "预估对组合的影响",
            "权重将从 7.2% 升至 8.5%，夏普比率预计 +0.02",
            "Portfolio",
            "yellow",
        ),
        (
            5,
            "人类审批",
            _PENDING_HITL_SUMMARY,
            _PENDING_HITL_DETAIL,
            "HITL",
            "red",
        ),
    )
    for step_no, ttl, summary, detail, tag, tone in chain_specs:
        session.add(
            DecisionStep(
                id=str(uuid4()),
                explanation_id=exp.id,
                step=step_no,
                title=ttl,
                summary=summary,
                detail=detail,
                tag=tag,
                tone=tone,
                created_at=now,
                updated_at=now,
            )
        )

    lineage_specs = (
        ("原始数据", "AKShare v2.1.0", "a1b2c3", "read", "green", "日线行情、成交量、复权因子"),
        ("特征工程", "FeatureSet v4.2.0", "d4e5f6", "read", "green", "MA5、MA20、成交量比率、行业动量"),
        ("模型推理", "MA趋势 v1.0.0", "g7h8i9", "execute", "yellow", "XGBoost 分类模型，预测 5 日收益方向"),
        ("信号生成", "Signal v1.0.0", "j0k1l2", "read", "green", "BUY 600519 100股 @ 1680.00"),
        ("风控审查", "RiskEngine v3.0.0", "m3n4o5", "execute", "green", "通过所有风控检查"),
    )
    for st, ver, hk, perm, tone, det in lineage_specs:
        session.add(
            LineageRecord(
                id=str(uuid4()),
                explanation_id=exp.id,
                step=st,
                version=ver,
                content_hash=hk,
                permission=perm,
                permission_tone=tone,
                detail=det,
                created_at=now,
                updated_at=now,
            )
        )

    bias_specs = (
        ("未来函数检测", "pass", "特征计算未使用未来数据"),
        ("幸存者偏差", "pass", "已排除退市股票"),
        ("数据窥探", "watch", "该因子在 50 个因子中被选中，可能存在过拟合风险"),
        ("回测偏差", "pass", "滑点、佣金已按实盘标准计入"),
    )
    for lbl, stat, txt in bias_specs:
        session.add(
            BiasGateCheck(
                id=str(uuid4()),
                explanation_id=exp.id,
                gate_name=lbl,
                status=stat,
                gate_detail=txt,
                created_at=now,
                updated_at=now,
            )
        )

    cases = (
        ("2025-08-12", "BUY", None, True, "突破后 5 日上涨 8.5%", 0.085, 5),
        ("2025-03-20", "BUY", None, False, "突破失败，5 日下跌 2.1%", -0.021, 5),
        ("2024-11-05", "BUY", None, True, "震荡后 5 日上涨 4.2%", 0.042, 5),
        ("2024-06-18", "BUY", None, True, "温和上涨 3.1%", 0.031, 5),
    )
    for dt, act, _tgt, succ, nt, pct, dys in cases:
        session.add(
            SimilarCase(
                id=str(uuid4()),
                explanation_id=exp.id,
                date=dt,
                action=act,
                target=None,
                outcome=None,
                return_pct=pct,
                days=dys,
                success=succ,
                note=nt,
                created_at=now,
                updated_at=now,
            )
        )

    await session.flush()
    return exp


async def reset_explain_fixture_pending(session: AsyncSession, trace_id: str = FIXTURE_TRACE_ID) -> None:
    """Restore pending HITL state for deterministic Explain API tests."""
    exp = await fetch_explanation(session, trace_id)
    if exp is None:
        return
    exp.status = "待审批"
    exp.status_tone = "yellow"
    exp.approved_at = None
    exp.updated_at = now_utc()

    step5 = await session.scalar(
        select(DecisionStep).where(
            DecisionStep.explanation_id == exp.id,
            DecisionStep.step == 5,
            DecisionStep.deleted_at.is_(None),
        )
    )
    if step5 is not None:
        step5.summary = _PENDING_HITL_SUMMARY
        step5.detail = _PENDING_HITL_DETAIL
        step5.tone = "red"
        step5.tag = step5.tag or "HITL"
        step5.updated_at = now_utc()

    await session.flush()
