"""Risk domain models — rules, checks, budgets, VaR, circuit breakers, breaches."""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class RiskRule(BaseModel):
    """Configurable risk rule."""

    __tablename__ = "risk_rules"

    scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # account / portfolio / strategy / order
    metric: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # max_drawdown / daily_loss / position_limit / var
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    action: Mapped[str] = mapped_column(String(32), default="alert")  # alert / block / kill_switch
    enabled: Mapped[bool] = mapped_column(default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class RiskCheck(BaseModel):
    """Recorded risk check result."""

    __tablename__ = "risk_checks"

    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(16), default="pass")  # pass / watch / fail
    result_tone: Mapped[str] = mapped_column(String(16), default="green")
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON


class RiskBudget(BaseModel):
    """Risk budget allocation and usage."""

    __tablename__ = "risk_budgets"

    portfolio_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    limit_value: Mapped[float] = mapped_column(Float, nullable=False)
    used_value: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(32), default="pct")
    tone: Mapped[str] = mapped_column(String(16), default="green")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class VaRSnapshot(BaseModel):
    """Value at Risk snapshot."""

    __tablename__ = "var_snapshots"

    portfolio_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ts: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    daily_var: Mapped[float] = mapped_column(Float, nullable=False)
    weekly_var: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.95)


class CircuitBreaker(BaseModel):
    """Circuit breaker configuration and state."""

    __tablename__ = "circuit_breakers"

    level: Mapped[str] = mapped_column(String(8), nullable=False, index=True)  # L1 / L2 / L3 / L4
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    trigger: Mapped[str] = mapped_column(String(256), nullable=False)
    action: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="armed")  # armed / triggered / cooldown / disabled
    status_tone: Mapped[str] = mapped_column(String(16), default="green")
    triggers24h: Mapped[int] = mapped_column(Integer, default=0)
    last_trigger: Mapped[str | None] = mapped_column(String(64), nullable=True)


class RiskBreach(BaseModel):
    """Risk breach / violation event."""

    __tablename__ = "risk_breaches"

    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # critical / high / medium / low
    severity_tone: Mapped[str] = mapped_column(String(16), default="red")
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ongoing", index=True)  # resolved / ongoing / review
    status_tone: Mapped[str] = mapped_column(String(16), default="yellow")


class PolicyDecision(BaseModel):
    """Policy engine decision log."""

    __tablename__ = "policy_decisions"

    actor: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    request: Mapped[str] = mapped_column(String(512), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # allowed / denied / approval_required / modified
    decision_tone: Mapped[str] = mapped_column(String(16), default="green")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
