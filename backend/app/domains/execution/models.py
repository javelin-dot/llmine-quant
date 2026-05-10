"""Execution domain models — approvals, orders, fills, execution metrics."""

from sqlalchemy import Float, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class Approval(BaseModel):
    """Trade approval request (HITL gate)."""

    __tablename__ = "approvals"

    portfolio_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    strategy_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # live / paper / reduce / add / rotate / hedge / pause
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)  # BUY / SELL / PAUSE
    qty: Mapped[str] = mapped_column(String(32), nullable=False)
    notional: Mapped[str] = mapped_column(String(32), nullable=False)
    notional_pct: Mapped[float] = mapped_column(Float, default=0.0)
    limit_price: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stop_loss: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    risk_grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    expire_sec: Mapped[int] = mapped_column(Integer, default=300)
    urgency: Mapped[str] = mapped_column(String(16), default="medium")  # high / medium / low
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending / approved / rejected / expired


class Order(BaseModel):
    """Order book entry."""

    __tablename__ = "orders"

    account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(16), nullable=False)  # BUY / SELL
    qty: Mapped[str] = mapped_column(String(32), nullable=False)
    limit_price: Mapped[str] = mapped_column(String(32), nullable=False)
    filled_qty: Mapped[str] = mapped_column(String(32), default="0")
    status: Mapped[str] = mapped_column(String(32), default="working")  # filled / partial / rejected / canceled / working
    slippage_bps: Mapped[float] = mapped_column(Float, default=0.0)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    strategy_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class Fill(BaseModel):
    """Individual fill record."""

    __tablename__ = "fills"

    order_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    fill_price: Mapped[float] = mapped_column(Float, nullable=False)
    fill_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    commission: Mapped[float] = mapped_column(Float, default=0.0)


class ExecutionMetric(BaseModel):
    """Execution quality metric snapshot."""

    __tablename__ = "execution_metrics"

    account_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    avg_slippage_bps: Mapped[float] = mapped_column(Float, default=0.0)
    p50_slippage_bps: Mapped[float] = mapped_column(Float, default=0.0)
    p95_slippage_bps: Mapped[float] = mapped_column(Float, default=0.0)
    fill_rate_total: Mapped[int] = mapped_column(Integer, default=0)
    fill_rate_filled: Mapped[int] = mapped_column(Integer, default=0)
    fill_rate_partial: Mapped[int] = mapped_column(Integer, default=0)
    fill_rate_rejected: Mapped[int] = mapped_column(Integer, default=0)
    fill_rate_canceled: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_sec: Mapped[float] = mapped_column(Float, default=0.0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)


class PreTradeCheck(BaseModel):
    """Pre-trade risk check result."""

    __tablename__ = "pre_trade_checks"

    account_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    limit_value: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="pass")  # pass / watch / fail
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentTrace(BaseModel):
    """Agent execution trace log."""

    __tablename__ = "agent_traces"

    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str] = mapped_column(String(16), default="blue")
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
