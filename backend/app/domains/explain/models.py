"""ORM models for Explain screen — aligns with migrations 20260513 / 20260518."""

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel

EXPL_SIGNAL_EXPL_TARGET = "signal_explanations.id"


class SignalExplanation(BaseModel):
    """Top-level Explain signal snapshot (strategy output pending / approved risk review)."""

    __tablename__ = "signal_explanations"

    strategy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    strategy_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    target: Mapped[str] = mapped_column(String(192), nullable=False)
    size: Mapped[str] = mapped_column(String(192), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    status_tone: Mapped[str] = mapped_column(String(16), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    attribution_base: Mapped[float | None] = mapped_column(Float, nullable=True)
    attribution_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    attribution_decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attribution_decision_tone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    similar_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    similar_win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    similar_avg_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    radar_avg: Mapped[float | None] = mapped_column(Float, nullable=True)


class AttributionItem(BaseModel):
    __tablename__ = "attribution_items"

    explanation_id: Mapped[str] = mapped_column(String(36), ForeignKey(EXPL_SIGNAL_EXPL_TARGET), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    detail: Mapped[str | None] = mapped_column("desc", Text(), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class DecisionStep(BaseModel):
    __tablename__ = "decision_steps"

    explanation_id: Mapped[str] = mapped_column(String(36), ForeignKey(EXPL_SIGNAL_EXPL_TARGET), index=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str | None] = mapped_column("desc", Text(), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tone: Mapped[str] = mapped_column(String(16), nullable=False)


class LineageRecord(BaseModel):
    __tablename__ = "lineage_records"

    explanation_id: Mapped[str] = mapped_column(String(36), ForeignKey(EXPL_SIGNAL_EXPL_TARGET), index=True)
    step: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str] = mapped_column("hash", String(64), nullable=False)
    permission: Mapped[str] = mapped_column(String(32), nullable=False)
    permission_tone: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class BiasGateCheck(BaseModel):
    __tablename__ = "bias_gate_checks"

    explanation_id: Mapped[str] = mapped_column(String(36), ForeignKey(EXPL_SIGNAL_EXPL_TARGET), index=True)
    gate_name: Mapped[str] = mapped_column("check", String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    gate_detail: Mapped[str | None] = mapped_column("desc", Text(), nullable=True)


class SimilarCase(BaseModel):
    __tablename__ = "similar_cases"

    explanation_id: Mapped[str] = mapped_column(String(36), ForeignKey(EXPL_SIGNAL_EXPL_TARGET), index=True)
    date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(256), nullable=True)
    return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ConfidenceRadarAxis(BaseModel):
    __tablename__ = "confidence_radar_axes"

    explanation_id: Mapped[str] = mapped_column(String(36), ForeignKey(EXPL_SIGNAL_EXPL_TARGET), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    axis_name: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    axis_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
