"""walk_forward_folds table

Revision ID: 65eb0814322d
Revises: c45d1fe90688
Create Date: 2026-05-13 01:00:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "65eb0814322d"
down_revision = "c45d1fe90688"
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
        "walk_forward_folds",
        *_base_columns(),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("fold_index", sa.Integer(), nullable=False),
        sa.Column("train_start", sa.String(32), nullable=False),
        sa.Column("train_end", sa.String(32), nullable=False),
        sa.Column("test_start", sa.String(32), nullable=False),
        sa.Column("test_end", sa.String(32), nullable=False),
        sa.Column("train_return", sa.Float(), nullable=True),
        sa.Column("test_return", sa.Float(), nullable=True),
        sa.Column("train_sharpe", sa.Float(), nullable=True),
        sa.Column("test_sharpe", sa.Float(), nullable=True),
        sa.Column("train_max_dd", sa.Float(), nullable=True),
        sa.Column("test_max_dd", sa.Float(), nullable=True),
        sa.Column("train_params_json", sa.Text(), nullable=True),
    )
    op.create_index(
        op.f("ix_walk_forward_folds_run_id"), "walk_forward_folds", ["run_id"]
    )
    op.create_index(
        op.f("ix_walk_forward_folds_fold_index"), "walk_forward_folds", ["fold_index"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_walk_forward_folds_fold_index"), table_name="walk_forward_folds")
    op.drop_index(op.f("ix_walk_forward_folds_run_id"), table_name="walk_forward_folds")
    op.drop_table("walk_forward_folds")
