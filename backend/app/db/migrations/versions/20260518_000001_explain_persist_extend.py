"""extend explain tables — persist full Explain screen payload

Revision ID: 20260518_000001
Revises: 20260516_000002
"""

import sqlalchemy as sa
from alembic import op

revision = "20260518_000001"
down_revision = "20260516_000002"
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
    with op.batch_alter_table("signal_explanations") as batch:
        batch.add_column(sa.Column("strategy_name", sa.String(128), nullable=True))
        batch.add_column(
            sa.Column(
                "status_tone",
                sa.String(16),
                nullable=False,
                server_default=sa.text("'yellow'"),
            ),
        )
        batch.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("attribution_base", sa.Float(), nullable=True))
        batch.add_column(sa.Column("attribution_final", sa.Float(), nullable=True))
        batch.add_column(sa.Column("attribution_decision", sa.String(64), nullable=True))
        batch.add_column(sa.Column("attribution_decision_tone", sa.String(16), nullable=True))
        batch.add_column(sa.Column("similar_summary", sa.Text(), nullable=True))
        batch.add_column(sa.Column("similar_win_rate", sa.Float(), nullable=True))
        batch.add_column(sa.Column("similar_avg_return", sa.Float(), nullable=True))
        batch.add_column(sa.Column("radar_avg", sa.Float(), nullable=True))
        batch.alter_column(
            "target",
            type_=sa.String(192),
            existing_type=sa.String(32),
            existing_nullable=False,
        )
        batch.alter_column(
            "size",
            type_=sa.String(192),
            existing_type=sa.String(32),
            existing_nullable=False,
        )

    op.add_column(
        "lineage_records",
        sa.Column(
            "permission_tone",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'green'"),
        ),
    )
    op.add_column("similar_cases", sa.Column("days", sa.Integer(), nullable=True))
    op.add_column("similar_cases", sa.Column("success", sa.Boolean(), nullable=True))
    op.add_column("similar_cases", sa.Column("note", sa.Text(), nullable=True))

    op.create_table(
        "confidence_radar_axes",
        *_base_columns(),
        sa.Column("explanation_id", sa.String(36), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("axis_name", sa.String(128), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("axis_detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_confidence_radar_axes_explanation_id", "confidence_radar_axes", ["explanation_id"])


def downgrade() -> None:
    op.drop_index("ix_confidence_radar_axes_explanation_id", table_name="confidence_radar_axes")
    op.drop_table("confidence_radar_axes")
    op.drop_column("similar_cases", "note")
    op.drop_column("similar_cases", "success")
    op.drop_column("similar_cases", "days")
    op.drop_column("lineage_records", "permission_tone")

    with op.batch_alter_table("signal_explanations") as batch:
        batch.alter_column(
            "size",
            type_=sa.String(32),
            existing_type=sa.String(192),
            existing_nullable=False,
        )
        batch.alter_column(
            "target",
            type_=sa.String(32),
            existing_type=sa.String(192),
            existing_nullable=False,
        )
        batch.drop_column("radar_avg")
        batch.drop_column("similar_avg_return")
        batch.drop_column("similar_win_rate")
        batch.drop_column("similar_summary")
        batch.drop_column("attribution_decision_tone")
        batch.drop_column("attribution_decision")
        batch.drop_column("attribution_final")
        batch.drop_column("attribution_base")
        batch.drop_column("approved_at")
        batch.drop_column("status_tone")
        batch.drop_column("strategy_name")
