"""Portfolio domain models — portfolios, positions, NAV snapshots, rebalancing."""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class Portfolio(BaseModel):
    """Portfolio master record."""

    __tablename__ = "portfolios"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(8), default="CNY")
    status: Mapped[str] = mapped_column(String(32), default="active")
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class Account(BaseModel):
    """Trading account."""

    __tablename__ = "accounts"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # custody / live-main / live-small / paper / sandbox
    broker: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_live: Mapped[bool] = mapped_column(default=False)
    cap_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    portfolio_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class Position(BaseModel):
    """Current position."""

    __tablename__ = "positions"

    account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_cost: Mapped[float] = mapped_column(Float, nullable=False)
    market_value: Mapped[float] = mapped_column(Float, nullable=False)


class CashBalance(BaseModel):
    """Cash balance per currency."""

    __tablename__ = "cash_balances"

    account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    available: Mapped[float] = mapped_column(Float, default=0.0)
    frozen: Mapped[float] = mapped_column(Float, default=0.0)


class NAVSnapshot(BaseModel):
    """Portfolio NAV snapshot."""

    __tablename__ = "nav_snapshots"

    portfolio_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ts: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    nav: Mapped[float] = mapped_column(Float, nullable=False)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    leverage: Mapped[float] = mapped_column(Float, default=1.0)


class RebalanceProposal(BaseModel):
    """Rebalancing proposal."""

    __tablename__ = "rebalance_proposals"

    portfolio_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # reduce / add / rotate / hedge
    from_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delta: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgency: Mapped[str] = mapped_column(String(16), default="medium")  # high / medium / low
    urgency_tone: Mapped[str] = mapped_column(String(16), default="yellow")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending / approved / rejected / executed
