"""market data daily bars

Revision ID: 20260512_000003
Revises: 20260510_000002
Create Date: 2026-05-12 00:00:03.000000+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260512_000003"
down_revision = "20260510_000002"
branch_labels = None
depends_on = None


def _base_columns() -> list:
    """Return the standard BaseModel columns shared by every table."""
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("metadata_json", sa.String(2048), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "market_bars_daily",
        *_base_columns(),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.String(32), nullable=False),
        sa.Column("prev_close", sa.Float(), nullable=True),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("adjusted_close", sa.Float(), nullable=True),
        sa.Column("forward_factor", sa.Float(), nullable=True),
        sa.Column("limit_up_price", sa.Float(), nullable=True),
        sa.Column("limit_down_price", sa.Float(), nullable=True),
        sa.Column("is_st", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_limit_up", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_limit_down", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_suspended", sa.Boolean(), nullable=False, default=False),
        sa.Column("can_buy", sa.Boolean(), nullable=False, default=True),
        sa.Column("can_sell", sa.Boolean(), nullable=False, default=True),
        sa.UniqueConstraint("symbol", "trade_date", name="uq_market_bars_daily_symbol_trade_date"),
    )
    op.create_index("ix_market_bars_daily_org_id", "market_bars_daily", ["org_id"])
    op.create_index("ix_market_bars_daily_symbol", "market_bars_daily", ["symbol"])
    op.create_index("ix_market_bars_daily_trade_date", "market_bars_daily", ["trade_date"])


def downgrade() -> None:
    op.drop_index("ix_market_bars_daily_trade_date", table_name="market_bars_daily")
    op.drop_index("ix_market_bars_daily_symbol", table_name="market_bars_daily")
    op.drop_index("ix_market_bars_daily_org_id", table_name="market_bars_daily")
    op.drop_table("market_bars_daily")
