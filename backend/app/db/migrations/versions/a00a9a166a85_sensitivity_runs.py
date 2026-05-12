"""sensitivity_runs table

Revision ID: a00a9a166a85
Revises: 65eb0814322d
Create Date: 2026-05-13 01:30:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a00a9a166a85"
down_revision = "65eb0814322d"
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
        "sensitivity_runs",
        *_base_columns(),
        sa.Column("parent_run_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("variant_json", sa.Text(), nullable=True),
        sa.Column("is_baseline", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cumulative_return", sa.Float(), nullable=True),
        sa.Column("annual_return", sa.Float(), nullable=True),
        sa.Column("max_drawdown", sa.Float(), nullable=True),
        sa.Column("sharpe_ratio", sa.Float(), nullable=True),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("turnover", sa.Float(), nullable=True),
    )
    op.create_index(op.f("ix_sensitivity_runs_parent_run_id"), "sensitivity_runs", ["parent_run_id"])
    op.create_index(op.f("ix_sensitivity_runs_kind"), "sensitivity_runs", ["kind"])


def downgrade() -> None:
    op.drop_index(op.f("ix_sensitivity_runs_kind"), table_name="sensitivity_runs")
    op.drop_index(op.f("ix_sensitivity_runs_parent_run_id"), table_name="sensitivity_runs")
    op.drop_table("sensitivity_runs")
