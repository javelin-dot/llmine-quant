"""paper trading tables

Revision ID: 49c0724c647e
Revises: dbab78f9c309
Create Date: 2026-05-13 03:00:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "49c0724c647e"
down_revision = "dbab78f9c309"
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
        "paper_accounts",
        *_base_columns(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("strategy_id", sa.String(36), nullable=True),
        sa.Column("strategy_version_id", sa.String(36), nullable=True),
        sa.Column("market", sa.String(16), nullable=False, server_default="A"),
        sa.Column("base_currency", sa.String(8), nullable=False, server_default="CNY"),
        sa.Column("initial_cash", sa.Float(), nullable=False),
        sa.Column("cash", sa.Float(), nullable=False),
        sa.Column("cost_config_json", sa.Text(), nullable=True),
        sa.Column("inception_date", sa.String(32), nullable=True),
        sa.Column("last_processed_date", sa.String(32), nullable=True),
        sa.Column("peak_nav", sa.Float(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
    )
    op.create_index(op.f("ix_paper_accounts_owner_id"), "paper_accounts", ["owner_id"])
    op.create_index(op.f("ix_paper_accounts_strategy_id"), "paper_accounts", ["strategy_id"])
    op.create_index(
        op.f("ix_paper_accounts_strategy_version_id"), "paper_accounts", ["strategy_version_id"]
    )
    op.create_index(
        op.f("ix_paper_accounts_last_processed_date"), "paper_accounts", ["last_processed_date"]
    )
    op.create_index(op.f("ix_paper_accounts_status"), "paper_accounts", ["status"])

    op.create_table(
        "paper_positions",
        *_base_columns(),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_price", sa.Float(), nullable=True),
        sa.Column("market_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "account_id", "symbol", name="uq_paper_positions_account_symbol"
        ),
    )
    op.create_index(op.f("ix_paper_positions_account_id"), "paper_positions", ["account_id"])
    op.create_index(op.f("ix_paper_positions_symbol"), "paper_positions", ["symbol"])

    op.create_table(
        "paper_orders",
        *_base_columns(),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("strategy_id", sa.String(36), nullable=True),
        sa.Column("trade_date", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("target_weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("target_quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("filled_quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(op.f("ix_paper_orders_account_id"), "paper_orders", ["account_id"])
    op.create_index(op.f("ix_paper_orders_strategy_id"), "paper_orders", ["strategy_id"])
    op.create_index(op.f("ix_paper_orders_trade_date"), "paper_orders", ["trade_date"])
    op.create_index(op.f("ix_paper_orders_symbol"), "paper_orders", ["symbol"])
    op.create_index(op.f("ix_paper_orders_status"), "paper_orders", ["status"])

    op.create_table(
        "paper_fills",
        *_base_columns(),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("trade_date", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("commission", sa.Float(), nullable=False, server_default="0"),
        sa.Column("stamp_tax", sa.Float(), nullable=False, server_default="0"),
        sa.Column("slippage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("net_cash_flow", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index(op.f("ix_paper_fills_order_id"), "paper_fills", ["order_id"])
    op.create_index(op.f("ix_paper_fills_account_id"), "paper_fills", ["account_id"])
    op.create_index(op.f("ix_paper_fills_trade_date"), "paper_fills", ["trade_date"])
    op.create_index(op.f("ix_paper_fills_symbol"), "paper_fills", ["symbol"])

    op.create_table(
        "paper_nav_points",
        *_base_columns(),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("trade_date", sa.String(32), nullable=False),
        sa.Column("nav", sa.Float(), nullable=False),
        sa.Column("cash", sa.Float(), nullable=False),
        sa.Column("market_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("daily_return", sa.Float(), nullable=True),
        sa.Column("drawdown", sa.Float(), nullable=True),
        sa.UniqueConstraint("account_id", "trade_date", name="uq_paper_nav_account_date"),
    )
    op.create_index(op.f("ix_paper_nav_points_account_id"), "paper_nav_points", ["account_id"])
    op.create_index(op.f("ix_paper_nav_points_trade_date"), "paper_nav_points", ["trade_date"])

    op.create_table(
        "paper_pre_trade_checks",
        *_base_columns(),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("rule", sa.String(64), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("limit_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pass"),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index(
        op.f("ix_paper_pre_trade_checks_order_id"), "paper_pre_trade_checks", ["order_id"]
    )
    op.create_index(
        op.f("ix_paper_pre_trade_checks_account_id"), "paper_pre_trade_checks", ["account_id"]
    )

    op.create_table(
        "paper_risk_breaches",
        *_base_columns(),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("trade_date", sa.String(32), nullable=False),
        sa.Column("rule", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ongoing"),
    )
    op.create_index(
        op.f("ix_paper_risk_breaches_account_id"), "paper_risk_breaches", ["account_id"]
    )
    op.create_index(
        op.f("ix_paper_risk_breaches_trade_date"), "paper_risk_breaches", ["trade_date"]
    )
    op.create_index(op.f("ix_paper_risk_breaches_rule"), "paper_risk_breaches", ["rule"])
    op.create_index(op.f("ix_paper_risk_breaches_status"), "paper_risk_breaches", ["status"])


def downgrade() -> None:
    for ix, tbl in [
        ("ix_paper_risk_breaches_status", "paper_risk_breaches"),
        ("ix_paper_risk_breaches_rule", "paper_risk_breaches"),
        ("ix_paper_risk_breaches_trade_date", "paper_risk_breaches"),
        ("ix_paper_risk_breaches_account_id", "paper_risk_breaches"),
    ]:
        op.drop_index(op.f(ix), table_name=tbl)
    op.drop_table("paper_risk_breaches")

    for ix, tbl in [
        ("ix_paper_pre_trade_checks_account_id", "paper_pre_trade_checks"),
        ("ix_paper_pre_trade_checks_order_id", "paper_pre_trade_checks"),
    ]:
        op.drop_index(op.f(ix), table_name=tbl)
    op.drop_table("paper_pre_trade_checks")

    for ix, tbl in [
        ("ix_paper_nav_points_trade_date", "paper_nav_points"),
        ("ix_paper_nav_points_account_id", "paper_nav_points"),
    ]:
        op.drop_index(op.f(ix), table_name=tbl)
    op.drop_table("paper_nav_points")

    for ix, tbl in [
        ("ix_paper_fills_symbol", "paper_fills"),
        ("ix_paper_fills_trade_date", "paper_fills"),
        ("ix_paper_fills_account_id", "paper_fills"),
        ("ix_paper_fills_order_id", "paper_fills"),
    ]:
        op.drop_index(op.f(ix), table_name=tbl)
    op.drop_table("paper_fills")

    for ix, tbl in [
        ("ix_paper_orders_status", "paper_orders"),
        ("ix_paper_orders_symbol", "paper_orders"),
        ("ix_paper_orders_trade_date", "paper_orders"),
        ("ix_paper_orders_strategy_id", "paper_orders"),
        ("ix_paper_orders_account_id", "paper_orders"),
    ]:
        op.drop_index(op.f(ix), table_name=tbl)
    op.drop_table("paper_orders")

    for ix, tbl in [
        ("ix_paper_positions_symbol", "paper_positions"),
        ("ix_paper_positions_account_id", "paper_positions"),
    ]:
        op.drop_index(op.f(ix), table_name=tbl)
    op.drop_table("paper_positions")

    for ix, tbl in [
        ("ix_paper_accounts_status", "paper_accounts"),
        ("ix_paper_accounts_last_processed_date", "paper_accounts"),
        ("ix_paper_accounts_strategy_version_id", "paper_accounts"),
        ("ix_paper_accounts_strategy_id", "paper_accounts"),
        ("ix_paper_accounts_owner_id", "paper_accounts"),
    ]:
        op.drop_index(op.f(ix), table_name=tbl)
    op.drop_table("paper_accounts")
