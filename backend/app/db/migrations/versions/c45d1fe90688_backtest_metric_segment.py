"""backtest_metric segment column for IS/OOS split

Revision ID: c45d1fe90688
Revises: c029ffadba27
Create Date: 2026-05-13 00:00:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c45d1fe90688"
down_revision = "c029ffadba27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "backtest_metrics",
        sa.Column("segment", sa.String(length=16), nullable=False, server_default="all"),
    )
    op.create_index(
        op.f("ix_backtest_metrics_segment"),
        "backtest_metrics",
        ["segment"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_backtest_metrics_segment"), table_name="backtest_metrics")
    op.drop_column("backtest_metrics", "segment")
