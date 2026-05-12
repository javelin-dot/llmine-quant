"""Data domain models — sources, market data, features, lineage, incidents."""

from sqlalchemy import Boolean, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class DataSource(BaseModel):
    """External data source configuration and metadata."""

    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # akshare / tushare / baostock / wind
    tier: Mapped[str] = mapped_column(String(32), default="research")  # research / paper / live
    license_scope: Mapped[str] = mapped_column(String(64), default="research")
    type: Mapped[str] = mapped_column(String(64), default="kline")  # kline / fundamental / macro
    coverage: Mapped[str] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="healthy", index=True)  # healthy / warning / error / maintenance
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_p95: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    drift_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    license: Mapped[str | None] = mapped_column(String(256), nullable=True)
    last_update: Mapped[str | None] = mapped_column(String(64), nullable=True)


class DataSourceHealth(BaseModel):
    """Periodic health snapshot for a data source."""

    __tablename__ = "data_source_health"

    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    drift_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class MarketBarDaily(BaseModel):
    """Daily OHLCV market data (stored in TimescaleDB in production)."""

    __tablename__ = "market_bars_daily"
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_market_bars_daily_symbol_trade_date"),
    )

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trade_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    prev_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    adjusted_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    forward_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    limit_up_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    limit_down_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_st: Mapped[bool] = mapped_column(Boolean, default=False)
    is_limit_up: Mapped[bool] = mapped_column(Boolean, default=False)
    is_limit_down: Mapped[bool] = mapped_column(Boolean, default=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    can_buy: Mapped[bool] = mapped_column(Boolean, default=True)
    can_sell: Mapped[bool] = mapped_column(Boolean, default=True)


class CorporateAction(BaseModel):
    """Corporate actions for adjustment (splits, dividends)."""

    __tablename__ = "corporate_actions"

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ex_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    factor: Mapped[float] = mapped_column(Float, nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)  # split / dividend / rights
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)


class FeatureSet(BaseModel):
    """Feature set registry with lineage and validation status."""

    __tablename__ = "feature_sets"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    permission_scope: Mapped[str] = mapped_column(String(64), default="research")
    lineage_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    validated: Mapped[bool] = mapped_column(default=False)
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class LineageNode(BaseModel):
    """Data lineage DAG node."""

    __tablename__ = "lineage_nodes"

    node_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # raw / cleaned / feature / model / signal / order
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    permission: Mapped[str] = mapped_column(String(64), default="read")


class LineageEdge(BaseModel):
    """Data lineage DAG edge."""

    __tablename__ = "lineage_edges"

    from_node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    to_node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class DataIncident(BaseModel):
    """Data quality incident or outage."""

    __tablename__ = "data_incidents"

    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # latency / missing / drift / license / outage / schema
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # critical / high / medium / low
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ongoing", index=True)  # resolved / ongoing / review
