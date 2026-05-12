"""backtest result tables

Revision ID: 20260512_000004
Revises: 20260512_000003
Create Date: 2026-05-12 00:00:04.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260512_000004"
down_revision = "20260512_000003"
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
        "backtest_tasks",
        *_base_columns(),
        sa.Column("strategy_version_id", sa.String(36), nullable=False),
        sa.Column("config", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, default="queued"),
        sa.Column("priority", sa.Integer(), nullable=False, default=3),
    )
    op.create_index("ix_backtest_tasks_org_id", "backtest_tasks", ["org_id"])
    op.create_index("ix_backtest_tasks_strategy_version_id", "backtest_tasks", ["strategy_version_id"])
    op.create_index("ix_backtest_tasks_status", "backtest_tasks", ["status"])

    op.create_table(
        "backtest_runs",
        *_base_columns(),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("params", sa.Text(), nullable=True),
        sa.Column("started_at", sa.String(64), nullable=True),
        sa.Column("ended_at", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, default="running"),
        sa.Column("report_uri", sa.String(512), nullable=True),
    )
    op.create_index("ix_backtest_runs_org_id", "backtest_runs", ["org_id"])
    op.create_index("ix_backtest_runs_task_id", "backtest_runs", ["task_id"])
    op.create_index("ix_backtest_runs_status", "backtest_runs", ["status"])

    op.create_table(
        "backtest_metrics",
        *_base_columns(),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("cumulative_return", sa.Float(), nullable=True),
        sa.Column("annual_return", sa.Float(), nullable=True),
        sa.Column("max_drawdown", sa.Float(), nullable=True),
        sa.Column("sharpe_ratio", sa.Float(), nullable=True),
        sa.Column("sortino_ratio", sa.Float(), nullable=True),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("profit_loss_ratio", sa.Float(), nullable=True),
        sa.Column("turnover", sa.Float(), nullable=True),
        sa.Column("oos_score", sa.Float(), nullable=True),
        sa.Column("overfit_level", sa.String(16), nullable=True),
    )
    op.create_index("ix_backtest_metrics_org_id", "backtest_metrics", ["org_id"])
    op.create_index("ix_backtest_metrics_run_id", "backtest_metrics", ["run_id"])

    op.create_table(
        "equity_points",
        *_base_columns(),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("trade_date", sa.String(32), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("benchmark", sa.Float(), nullable=True),
        sa.Column("drawdown", sa.Float(), nullable=True),
        sa.Column("phase", sa.String(16), nullable=False, default="is"),
    )
    op.create_index("ix_equity_points_org_id", "equity_points", ["org_id"])
    op.create_index("ix_equity_points_run_id", "equity_points", ["run_id"])
    op.create_index("ix_equity_points_trade_date", "equity_points", ["trade_date"])

    op.create_table(
        "stress_results",
        *_base_columns(),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("scenario", sa.String(64), nullable=False),
        sa.Column("loss", sa.String(64), nullable=True),
        sa.Column("max_drawdown", sa.String(64), nullable=True),
        sa.Column("fuse", sa.String(64), nullable=True),
        sa.Column("fuse_tone", sa.String(16), nullable=False, default="green"),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("human", sa.Text(), nullable=True),
    )
    op.create_index("ix_stress_results_org_id", "stress_results", ["org_id"])
    op.create_index("ix_stress_results_run_id", "stress_results", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_stress_results_run_id", table_name="stress_results")
    op.drop_index("ix_stress_results_org_id", table_name="stress_results")
    op.drop_table("stress_results")

    op.drop_index("ix_equity_points_trade_date", table_name="equity_points")
    op.drop_index("ix_equity_points_run_id", table_name="equity_points")
    op.drop_index("ix_equity_points_org_id", table_name="equity_points")
    op.drop_table("equity_points")

    op.drop_index("ix_backtest_metrics_run_id", table_name="backtest_metrics")
    op.drop_index("ix_backtest_metrics_org_id", table_name="backtest_metrics")
    op.drop_table("backtest_metrics")

    op.drop_index("ix_backtest_runs_status", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_task_id", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_org_id", table_name="backtest_runs")
    op.drop_table("backtest_runs")

    op.drop_index("ix_backtest_tasks_status", table_name="backtest_tasks")
    op.drop_index("ix_backtest_tasks_strategy_version_id", table_name="backtest_tasks")
    op.drop_index("ix_backtest_tasks_org_id", table_name="backtest_tasks")
    op.drop_table("backtest_tasks")
