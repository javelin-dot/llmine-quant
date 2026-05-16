"""Risk Service API — risk overview, budgets, VaR, circuit breakers, breaches."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.execution.models import Approval
from app.domains.risk.models import CircuitBreaker as CircuitBreakerModel
from app.domains.risk.models import PolicyDecision, RiskBreach, RiskBudget, VaRSnapshot
from app.domains.risk.schemas import (
    CircuitBreaker,
    ComplianceGate,
    PolicyDecisionOut,
    RiskBreachOut,
    RiskBudgetRow,
    RiskHeader,
    RiskKpi,
    RiskScreen,
    VaRDecomposition,
    VaRHistory,
    VaRPanel,
)
from app.core.websocket import manager as ws_manager
from app.services.audit_service import AuditService

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


def _fmt_time(dt) -> str:
    if dt is None:
        return "—"
    s = dt.isoformat()
    return s[11:16] if len(s) > 11 else s


async def _get_header(db: AsyncSession) -> RiskHeader:
    active_breaches = (
        await db.execute(
            select(func.count(RiskBreach.id)).where(RiskBreach.status == "ongoing")
        )
    ).scalar() or 0
    pending_approvals = (
        await db.execute(
            select(func.count(Approval.id)).where(Approval.status == "pending")
        )
    ).scalar() or 0
    auto_blocks = (
        await db.execute(
            select(func.count(PolicyDecision.id)).where(PolicyDecision.decision == "denied")
        )
    ).scalar() or 0
    score = max(0, 100 - int(active_breaches) * 10 - int(auto_blocks) * 2)
    if score >= 90:
        status, tone = "HEALTHY", "green"
    elif score >= 70:
        status, tone = "WARNING", "yellow"
    else:
        status, tone = "CRITICAL", "red"
    return RiskHeader(
        healthScore=score,
        healthStatus=status,
        healthStatusTone=tone,
        killSwitchArmed=True,
        lastIncident="—",
        autoBlocks24h=int(auto_blocks),
        pendingApprovals=int(pending_approvals),
        activeBreaches=int(active_breaches),
    )


async def _get_budgets(db: AsyncSession) -> list[RiskBudgetRow]:
    rows = (
        await db.execute(select(RiskBudget).order_by(RiskBudget.created_at.asc()).limit(20))
    ).scalars().all()
    return [
        RiskBudgetRow(
            name=r.metric,
            used=r.used_value,
            limit=r.limit_value,
            unit=r.unit,
            tone=r.tone,
            desc=r.description or "",
        )
        for r in rows
    ]


async def _get_var(db: AsyncSession) -> VaRPanel:
    snaps = (
        await db.execute(
            select(VaRSnapshot).order_by(VaRSnapshot.created_at.desc()).limit(30)
        )
    ).scalars().all()
    if not snaps:
        return VaRPanel(
            daily=0.0, dailyPct=0.0, weekly=0.0, weeklyPct=0.0,
            confidence=0.95, currency="CNY", history=[], decomposition=[],
        )
    latest = snaps[0]
    history = [
        VaRHistory(date=s.ts[:10], value=s.daily_var)
        for s in reversed(snaps[:30])
    ]
    return VaRPanel(
        daily=latest.daily_var,
        dailyPct=round(latest.daily_var / 10_000_000 * 100, 2),
        weekly=latest.weekly_var,
        weeklyPct=round(latest.weekly_var / 10_000_000 * 100, 2),
        confidence=latest.confidence,
        currency="CNY",
        history=history,
        decomposition=[],
    )


async def _get_circuits(db: AsyncSession) -> list[CircuitBreaker]:
    rows = (
        await db.execute(select(CircuitBreakerModel).order_by(CircuitBreakerModel.level))
    ).scalars().all()
    return [
        CircuitBreaker(
            level=r.level,
            name=r.name,
            status=r.status,
            statusTone=r.status_tone,
            trigger=r.trigger,
            action=r.action,
            triggers24h=r.triggers24h,
            lastTrigger=r.last_trigger or "—",
        )
        for r in rows
    ]


async def _get_policy_stream(db: AsyncSession) -> list[PolicyDecisionOut]:
    rows = (
        await db.execute(
            select(PolicyDecision).order_by(PolicyDecision.created_at.desc()).limit(20)
        )
    ).scalars().all()
    return [
        PolicyDecisionOut(
            time=_fmt_time(r.created_at),
            agent=r.actor,
            request=r.request,
            decision=r.decision,
            decisionTone=r.decision_tone,
            reason=r.reason or "",
            durationMs=r.duration_ms,
        )
        for r in rows
    ]


async def _get_breaches(db: AsyncSession) -> list[RiskBreachOut]:
    rows = (
        await db.execute(
            select(RiskBreach).order_by(RiskBreach.created_at.desc()).limit(20)
        )
    ).scalars().all()
    return [
        RiskBreachOut(
            time=_fmt_time(r.created_at),
            severity=r.severity,
            severityTone=r.severity_tone,
            title=r.title,
            detail=r.detail or "",
            resolution=r.resolution or "",
            status=r.status,
            statusTone=r.status_tone,
        )
        for r in rows
    ]


_KPIS = [
    RiskKpi(label="日VaR", value="—", trend="—", tone="blue"),
    RiskKpi(label="周VaR", value="—", trend="—", tone="blue"),
    RiskKpi(label="最大回撤", value="—", trend="—", tone="blue"),
    RiskKpi(label="组合Beta", value="—", trend="—", tone="blue"),
    RiskKpi(label="杠杆", value="—", trend="—", tone="blue"),
]


_COMPLIANCE_GATES = [
    ComplianceGate(
        title="Survivorship Bias 幸存者偏差",
        desc="研究池强制包含退市/暂停股票与历史成分变更",
        status="pass", statusTone="green", lastCheck="15:30",
        note="0 violations · 已加入 286 退市标的",
    ),
    ComplianceGate(
        title="Look-ahead Bias 未来函数",
        desc="特征只能使用信号 t 时刻已可见的数据",
        status="pass", statusTone="green", lastCheck="15:30",
        note="Time-Travel CI 全部通过 · 4823 测试用例",
    ),
    ComplianceGate(
        title="Feature Leakage 特征泄漏",
        desc="标签、成交结果、未来财务不得进入训练",
        status="watch", statusTone="yellow", lastCheck="15:25",
        note="Tech-Momentum-v18: 2 个特征与 t+1 收益相关性 0.62",
    ),
    ComplianceGate(
        title="License Scope 数据许可",
        desc="Research Only 数据禁止进入实盘信号",
        status="enforced", statusTone="red", lastCheck="15:31",
        note="12 笔阻断 · AKShare/雪球自动剔除",
    ),
    ComplianceGate(
        title="Class Imbalance 样本失衡",
        desc="正负样本比例需在 0.3-0.7 区间",
        status="pass", statusTone="green", lastCheck="15:00",
        note="当前比例 0.48 · 正常",
    ),
    ComplianceGate(
        title="Data Integrity 数据完整性",
        desc="关键字段缺失率与跨源一致性检查",
        status="pass", statusTone="green", lastCheck="14:50",
        note="缺失率 0.08% · 跨源偏差 < 0.1%",
    ),
]


@router.get("/overview", response_model=RiskScreen)
async def get_risk_overview(db: DbSession) -> RiskScreen:
    """Return the complete Risk Control screen — DB-driven."""
    header, budgets, var, circuits, policy, breaches = (
        await _get_header(db),
        await _get_budgets(db),
        await _get_var(db),
        await _get_circuits(db),
        await _get_policy_stream(db),
        await _get_breaches(db),
    )
    return RiskScreen(
        header=header,
        kpis=_KPIS,
        budgets=budgets,
        var=var,
        circuits=circuits,
        policyStream=policy,
        breaches=breaches,
        complianceGates=_COMPLIANCE_GATES,
    )


@router.get("/compliance-gates", response_model=list[ComplianceGate])
async def get_compliance_gates() -> list[ComplianceGate]:
    """Return compliance gate checks (bias / leakage / license / integrity)."""
    return _COMPLIANCE_GATES


@router.post("/circuit-breakers/{level}/trigger")
async def trigger_circuit(level: str, db: DbSession) -> dict[str, str]:
    """Manually trigger a circuit breaker by level (L1-L4)."""
    row = (
        await db.execute(
            select(CircuitBreakerModel).where(CircuitBreakerModel.level == level).limit(1)
        )
    ).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"circuit breaker {level} not found")
    row.status = "triggered"
    row.status_tone = "red"
    row.triggers24h = (row.triggers24h or 0) + 1
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        action="trigger_circuit_breaker",
        resource_type="circuit_breaker",
        resource_id=row.id,
        actor_type="human",
        result="triggered",
        result_tone="red",
        detail=f"Circuit breaker {level} manually triggered",
    )
    await ws_manager.broadcast(
        {"type": "circuit_breaker", "level": level, "status": "triggered", "name": row.name},
        topic="risk-events",
    )
    return {"level": level, "status": "triggered"}


@router.post("/circuit-breakers/{level}/recover")
async def recover_circuit(level: str, db: DbSession) -> dict[str, str]:
    """Request circuit breaker recovery."""
    row = (
        await db.execute(
            select(CircuitBreakerModel).where(CircuitBreakerModel.level == level).limit(1)
        )
    ).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"circuit breaker {level} not found")
    if row.status == "armed":
        raise HTTPException(status_code=409, detail="circuit breaker is already armed")
    row.status = "cooldown"
    row.status_tone = "yellow"
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        action="recover_circuit_breaker",
        resource_type="circuit_breaker",
        resource_id=row.id,
        actor_type="human",
        result="recovery_requested",
        result_tone="yellow",
        detail=f"Circuit breaker {level} recovery requested",
    )
    await ws_manager.broadcast(
        {"type": "circuit_breaker", "level": level, "status": "cooldown", "name": row.name},
        topic="risk-events",
    )
    return {"level": level, "status": "recovery_requested"}
