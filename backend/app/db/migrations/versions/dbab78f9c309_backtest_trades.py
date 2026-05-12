"""backtest_trades table

Revision ID: dbab78f9c309
Revises: 61868637158e
Create Date: 2026-05-13 02:30:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "dbab78f9c309"
down_revision = "61868637158e"
branch_labels = None
depends_on = None


def _base_columns() -> list:
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
        "backtest_trades",
        *_base_columns(),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("trade_date", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("target_weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("commission", sa.Float(), nullable=False, server_default="0"),
        sa.Column("stamp_tax", sa.Float(), nullable=False, server_default="0"),
        sa.Column("slippage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("net_cash_flow", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_backtest_trades_run_id"), "backtest_trades", ["run_id"])
    op.create_index(op.f("ix_backtest_trades_trade_date"), "backtest_trades", ["trade_date"])
    op.create_index(op.f("ix_backtest_trades_symbol"), "backtest_trades", ["symbol"])


def downgrade() -> None:
    op.drop_index(op.f("ix_backtest_trades_symbol"), table_name="backtest_trades")
    op.drop_index(op.f("ix_backtest_trades_trade_date"), table_name="backtest_trades")
    op.drop_index(op.f("ix_backtest_trades_run_id"), table_name="backtest_trades")
    op.drop_table("backtest_trades")
