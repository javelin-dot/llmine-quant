"""Collaboration domain models — reviews, diffs, A/B tests, approval flows."""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class StrategyReview(BaseModel):
    """Strategy version review request."""

    __tablename__ = "strategy_reviews"

    strategy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    from_version: Mapped[str] = mapped_column(String(32), nullable=False)
    to_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending / in_review / approved / rejected
    priority: Mapped[str] = mapped_column(String(16), default="medium")  # high / medium / low
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ReviewerDecision(BaseModel):
    """Individual reviewer decision."""

    __tablename__ = "reviewer_decisions"

    review_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), default="pending")  # approve / request_changes / pending


class ABTest(BaseModel):
    """A/B test experiment."""

    __tablename__ = "ab_tests"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    control_strategy: Mapped[str] = mapped_column(String(36), nullable=False)
    variant_strategy: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # running / completed / pending
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    samples: Mapped[int] = mapped_column(Integer, default=0)
    improvement: Mapped[float] = mapped_column(Float, default=0.0)
