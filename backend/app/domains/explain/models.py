"""Explain domain models — signal attribution, decision chain, lineage."""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class SignalExplanation(BaseModel):
    """Explanation for a single trading signal."""

    __tablename__ = "signal_explanations"

    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    strategy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # BUY / SELL / HOLD
    target: Mapped[str] = mapped_column(String(32), nullable=False)
    size: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    risk_grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")


class AttributionItem(BaseModel):
    """Individual attribution factor."""

    __tablename__ = "attribution_items"

    explanation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class DecisionStep(BaseModel):
    """Decision chain step."""

    __tablename__ = "decision_steps"

    explanation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    desc: Mapped[str] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tone: Mapped[str] = mapped_column(String(16), default="blue")


class LineageRecord(BaseModel):
    """Data lineage step for a signal."""

    __tablename__ = "lineage_records"

    explanation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    permission: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class BiasGateCheck(BaseModel):
    """Bias gate check result."""

    __tablename__ = "bias_gate_checks"

    explanation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    check: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pass")  # pass / watch / fail / enforced
    desc: Mapped[str | None] = mapped_column(Text, nullable=True)


class SimilarCase(BaseModel):
    """Historical similar signal case."""

    __tablename__ = "similar_cases"

    explanation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    case_date: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    ret: Mapped[float] = mapped_column(Float, default=0.0)
    days: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
