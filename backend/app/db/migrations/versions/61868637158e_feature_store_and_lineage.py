"""feature store and lineage tables

Revision ID: 61868637158e
Revises: a00a9a166a85
Create Date: 2026-05-13 02:00:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "61868637158e"
down_revision = "a00a9a166a85"
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
        "feature_sets",
        *_base_columns(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("permission_scope", sa.String(64), nullable=False, server_default="research"),
        sa.Column("lineage_hash", sa.String(64), nullable=True),
        sa.Column("validated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("validation_error", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(32), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dependencies_json", sa.Text(), nullable=True),
        sa.Column("computation_window", sa.Integer(), nullable=True),
    )
    op.create_index(op.f("ix_feature_sets_name"), "feature_sets", ["name"])

    op.create_table(
        "feature_usages",
        *_base_columns(),
        sa.Column("feature_id", sa.String(36), nullable=False),
        sa.Column("strategy_version_id", sa.String(36), nullable=False),
        sa.Column("backtest_run_id", sa.String(36), nullable=True),
        sa.Column("role", sa.String(32), nullable=True),
    )
    op.create_index(op.f("ix_feature_usages_feature_id"), "feature_usages", ["feature_id"])
    op.create_index(
        op.f("ix_feature_usages_strategy_version_id"),
        "feature_usages",
        ["strategy_version_id"],
    )
    op.create_index(
        op.f("ix_feature_usages_backtest_run_id"), "feature_usages", ["backtest_run_id"]
    )

    op.create_table(
        "lineage_nodes",
        *_base_columns(),
        sa.Column("node_type", sa.String(32), nullable=False),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("permission", sa.String(64), nullable=False, server_default="read"),
        sa.Column("ref_table", sa.String(64), nullable=True),
        sa.Column("ref_id", sa.String(64), nullable=True),
    )
    op.create_index(op.f("ix_lineage_nodes_node_type"), "lineage_nodes", ["node_type"])
    op.create_index(op.f("ix_lineage_nodes_ref_id"), "lineage_nodes", ["ref_id"])

    op.create_table(
        "lineage_edges",
        *_base_columns(),
        sa.Column("from_node_id", sa.String(36), nullable=False),
        sa.Column("to_node_id", sa.String(36), nullable=False),
        sa.Column("backtest_run_id", sa.String(36), nullable=True),
    )
    op.create_index(op.f("ix_lineage_edges_from_node_id"), "lineage_edges", ["from_node_id"])
    op.create_index(op.f("ix_lineage_edges_to_node_id"), "lineage_edges", ["to_node_id"])
    op.create_index(
        op.f("ix_lineage_edges_backtest_run_id"), "lineage_edges", ["backtest_run_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_lineage_edges_backtest_run_id"), table_name="lineage_edges")
    op.drop_index(op.f("ix_lineage_edges_to_node_id"), table_name="lineage_edges")
    op.drop_index(op.f("ix_lineage_edges_from_node_id"), table_name="lineage_edges")
    op.drop_table("lineage_edges")

    op.drop_index(op.f("ix_lineage_nodes_ref_id"), table_name="lineage_nodes")
    op.drop_index(op.f("ix_lineage_nodes_node_type"), table_name="lineage_nodes")
    op.drop_table("lineage_nodes")

    op.drop_index(op.f("ix_feature_usages_backtest_run_id"), table_name="feature_usages")
    op.drop_index(op.f("ix_feature_usages_strategy_version_id"), table_name="feature_usages")
    op.drop_index(op.f("ix_feature_usages_feature_id"), table_name="feature_usages")
    op.drop_table("feature_usages")

    op.drop_index(op.f("ix_feature_sets_name"), table_name="feature_sets")
    op.drop_table("feature_sets")
