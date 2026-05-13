"""execution, risk, and portfolio tables

Revision ID: 20260513_000001
Revises: 49c0724c647e
Create Date: 2026-05-13 10:00:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

revision = "20260513_000001"
down_revision = "49c0724c647e"
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
    # ── Execution ──────────────────────────────────────────────────
    op.create_table(
        "approvals",
        *_base_columns(),
        sa.Column("portfolio_id", sa.String(36), nullable=False),
        sa.Column("strategy_id", sa.String(36), nullable=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("qty", sa.String(32), nullable=False),
        sa.Column("notional", sa.String(32), nullable=False),
        sa.Column("notional_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("limit_price", sa.String(32), nullable=True),
        sa.Column("stop_loss", sa.String(32), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("risk_grade", sa.String(16), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("expire_sec", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("urgency", sa.String(16), nullable=False, server_default="'medium'"),
        sa.Column("status", sa.String(32), nullable=False, server_default="'pending'"),
    )
    op.create_index("ix_approvals_portfolio_id", "approvals", ["portfolio_id"])
    op.create_index("ix_approvals_strategy_id", "approvals", ["strategy_id"])
    op.create_index("ix_approvals_status", "approvals", ["status"])

    op.create_table(
        "orders",
        *_base_columns(),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("qty", sa.String(32), nullable=False),
        sa.Column("limit_price", sa.String(32), nullable=False),
        sa.Column("filled_qty", sa.String(32), nullable=False, server_default="'0'"),
        sa.Column("status", sa.String(32), nullable=False, server_default="'working'"),
        sa.Column("slippage_bps", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("strategy_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_orders_account_id", "orders", ["account_id"])
    op.create_index("ix_orders_symbol", "orders", ["symbol"])
    op.create_index("ix_orders_strategy_id", "orders", ["strategy_id"])

    op.create_table(
        "fills",
        *_base_columns(),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("fill_price", sa.Float(), nullable=False),
        sa.Column("fill_qty", sa.Integer(), nullable=False),
        sa.Column("commission", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_fills_order_id", "fills", ["order_id"])

    op.create_table(
        "execution_metrics",
        *_base_columns(),
        sa.Column("account_id", sa.String(36), nullable=True),
        sa.Column("avg_slippage_bps", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p50_slippage_bps", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p95_slippage_bps", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fill_rate_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fill_rate_filled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fill_rate_partial", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fill_rate_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fill_rate_canceled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_latency_sec", sa.Float(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_execution_metrics_account_id", "execution_metrics", ["account_id"])

    op.create_table(
        "pre_trade_checks",
        *_base_columns(),
        sa.Column("account_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("limit_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="'pass'"),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_pre_trade_checks_account_id", "pre_trade_checks", ["account_id"])

    op.create_table(
        "agent_traces",
        *_base_columns(),
        sa.Column("agent", sa.String(64), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("tone", sa.String(16), nullable=False, server_default="'blue'"),
        sa.Column("icon", sa.String(32), nullable=True),
    )

    # ── Risk ───────────────────────────────────────────────────────
    op.create_table(
        "risk_rules",
        *_base_columns(),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False, server_default="'alert'"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_risk_rules_scope", "risk_rules", ["scope"])
    op.create_index("ix_risk_rules_metric", "risk_rules", ["metric"])

    op.create_table(
        "risk_checks",
        *_base_columns(),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("result", sa.String(16), nullable=False, server_default="'pass'"),
        sa.Column("result_tone", sa.String(16), nullable=False, server_default="'green'"),
        sa.Column("snapshot", sa.Text(), nullable=True),
    )
    op.create_index("ix_risk_checks_resource_type", "risk_checks", ["resource_type"])
    op.create_index("ix_risk_checks_resource_id", "risk_checks", ["resource_id"])

    op.create_table(
        "risk_budgets",
        *_base_columns(),
        sa.Column("portfolio_id", sa.String(36), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("limit_value", sa.Float(), nullable=False),
        sa.Column("used_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(32), nullable=False, server_default="'pct'"),
        sa.Column("tone", sa.String(16), nullable=False, server_default="'green'"),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_risk_budgets_portfolio_id", "risk_budgets", ["portfolio_id"])

    op.create_table(
        "var_snapshots",
        *_base_columns(),
        sa.Column("portfolio_id", sa.String(36), nullable=False),
        sa.Column("ts", sa.String(64), nullable=False),
        sa.Column("daily_var", sa.Float(), nullable=False),
        sa.Column("weekly_var", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.95"),
    )
    op.create_index("ix_var_snapshots_portfolio_id", "var_snapshots", ["portfolio_id"])

    op.create_table(
        "circuit_breakers",
        *_base_columns(),
        sa.Column("level", sa.String(8), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("trigger", sa.String(256), nullable=False),
        sa.Column("action", sa.String(256), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="'armed'"),
        sa.Column("status_tone", sa.String(16), nullable=False, server_default="'green'"),
        sa.Column("triggers24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_trigger", sa.String(64), nullable=True),
    )
    op.create_index("ix_circuit_breakers_level", "circuit_breakers", ["level"])

    op.create_table(
        "risk_breaches",
        *_base_columns(),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("severity_tone", sa.String(16), nullable=False, server_default="'red'"),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="'ongoing'"),
        sa.Column("status_tone", sa.String(16), nullable=False, server_default="'yellow'"),
    )
    op.create_index("ix_risk_breaches_severity", "risk_breaches", ["severity"])
    op.create_index("ix_risk_breaches_status", "risk_breaches", ["status"])

    op.create_table(
        "policy_decisions",
        *_base_columns(),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("request", sa.String(512), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("decision_tone", sa.String(16), nullable=False, server_default="'green'"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=True),
    )
    op.create_index("ix_policy_decisions_actor", "policy_decisions", ["actor"])
    op.create_index("ix_policy_decisions_decision", "policy_decisions", ["decision"])

    # ── Portfolio ──────────────────────────────────────────────────
    op.create_table(
        "portfolios",
        *_base_columns(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("base_currency", sa.String(8), nullable=False, server_default="'CNY'"),
        sa.Column("status", sa.String(32), nullable=False, server_default="'active'"),
        sa.Column("owner_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_portfolios_owner_id", "portfolios", ["owner_id"])

    op.create_table(
        "accounts",
        *_base_columns(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("broker", sa.String(64), nullable=True),
        sa.Column("is_live", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("cap_amount", sa.Float(), nullable=True),
        sa.Column("portfolio_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_accounts_role", "accounts", ["role"])
    op.create_index("ix_accounts_portfolio_id", "accounts", ["portfolio_id"])

    op.create_table(
        "positions",
        *_base_columns(),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("avg_cost", sa.Float(), nullable=False),
        sa.Column("market_value", sa.Float(), nullable=False),
    )
    op.create_index("ix_positions_account_id", "positions", ["account_id"])
    op.create_index("ix_positions_symbol", "positions", ["symbol"])

    op.create_table(
        "cash_balances",
        *_base_columns(),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="'CNY'"),
        sa.Column("available", sa.Float(), nullable=False, server_default="0"),
        sa.Column("frozen", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_cash_balances_account_id", "cash_balances", ["account_id"])

    op.create_table(
        "nav_snapshots",
        *_base_columns(),
        sa.Column("portfolio_id", sa.String(36), nullable=False),
        sa.Column("ts", sa.String(64), nullable=False),
        sa.Column("nav", sa.Float(), nullable=False),
        sa.Column("pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("leverage", sa.Float(), nullable=False, server_default="1"),
    )
    op.create_index("ix_nav_snapshots_portfolio_id", "nav_snapshots", ["portfolio_id"])

    op.create_table(
        "rebalance_proposals",
        *_base_columns(),
        sa.Column("portfolio_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("from_symbol", sa.String(32), nullable=True),
        sa.Column("to_symbol", sa.String(32), nullable=True),
        sa.Column("delta", sa.String(64), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("urgency", sa.String(16), nullable=False, server_default="'medium'"),
        sa.Column("urgency_tone", sa.String(16), nullable=False, server_default="'yellow'"),
        sa.Column("status", sa.String(32), nullable=False, server_default="'pending'"),
    )
    op.create_index("ix_rebalance_proposals_portfolio_id", "rebalance_proposals", ["portfolio_id"])


def downgrade() -> None:
    # Portfolio
    op.drop_table("rebalance_proposals")
    op.drop_table("nav_snapshots")
    op.drop_table("cash_balances")
    op.drop_table("positions")
    op.drop_table("accounts")
    op.drop_table("portfolios")
    # Risk
    op.drop_table("policy_decisions")
    op.drop_table("risk_breaches")
    op.drop_table("circuit_breakers")
    op.drop_table("var_snapshots")
    op.drop_table("risk_budgets")
    op.drop_table("risk_checks")
    op.drop_table("risk_rules")
    # Execution
    op.drop_table("agent_traces")
    op.drop_table("pre_trade_checks")
    op.drop_table("execution_metrics")
    op.drop_table("fills")
    op.drop_table("orders")
    op.drop_table("approvals")
