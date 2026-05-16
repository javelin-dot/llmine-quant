"""workflow versions

Revision ID: 20260516_000001
Revises: 20260513_000002
Create Date: 2026-05-16 00:00:01.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260516_000001"
down_revision = "20260513_000002"
branch_labels = None
depends_on = None


def _base_columns() -> list:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("metadata_json", sa.String(2048), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "agent_definitions" not in tables:
        op.create_table(
            "agent_definitions",
            *_base_columns(),
            sa.Column("name", sa.String(128), nullable=False, unique=True),
            sa.Column("role", sa.String(64), nullable=False, index=True),
            sa.Column("avatar", sa.String(16), default="A"),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("objective", sa.Text, nullable=True),
            sa.Column("downstream_hint", sa.Text, nullable=True),
            sa.Column("autonomy", sa.String(32), default="supervised"),
            sa.Column("status", sa.String(16), default="active"),
            sa.Column("model_config_json", sa.Text, default="{}"),
            sa.Column("system_prompt", sa.Text, default=""),
            sa.Column("user_prompt_template", sa.Text, default=""),
            sa.Column("input_schema_json", sa.Text, default="{}"),
            sa.Column("output_schema_json", sa.Text, default="{}"),
            sa.Column("normalized_input_schema_json", sa.Text, default="{}"),
            sa.Column("normalized_output_schema_json", sa.Text, default="{}"),
            sa.Column("input_mapping_json", sa.Text, default="[]"),
            sa.Column("output_mapping_json", sa.Text, default="[]"),
            sa.Column("tool_policy_json", sa.Text, default="[]"),
            sa.Column("constraints_json", sa.Text, default="[]"),
            sa.Column("runtime_policy_json", sa.Text, default="{}"),
        )

    if "workflow_definitions" not in tables:
        op.create_table(
            "workflow_definitions",
            *_base_columns(),
            sa.Column("name", sa.String(128), nullable=False, unique=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("version", sa.String(32), default="1.0.0"),
            sa.Column("status", sa.String(16), default="draft"),
            sa.Column("is_default", sa.Boolean, default=False),
            sa.Column("published_version_id", sa.String(36), nullable=True, index=True),
        )
    else:
        columns = {column["name"] for column in inspector.get_columns("workflow_definitions")}
        if "published_version_id" not in columns:
            op.add_column("workflow_definitions", sa.Column("published_version_id", sa.String(36), nullable=True))
            op.create_index("ix_workflow_definitions_published_version_id", "workflow_definitions", ["published_version_id"])
            op.execute(
                sa.text(
                    "UPDATE workflow_definitions "
                    "SET status = 'draft' "
                    "WHERE status = 'published' AND published_version_id IS NULL"
                )
            )

    if "workflow_nodes" not in tables:
        op.create_table(
            "workflow_nodes",
            *_base_columns(),
            sa.Column("workflow_id", sa.String(36), nullable=False, index=True),
            sa.Column("agent_definition_id", sa.String(36), nullable=False, index=True),
            sa.Column("label", sa.String(128), nullable=True),
            sa.Column("position_x", sa.Float, default=0.0),
            sa.Column("position_y", sa.Float, default=0.0),
            sa.Column("config_override_json", sa.Text, default="{}"),
        )

    if "workflow_edges" not in tables:
        op.create_table(
            "workflow_edges",
            *_base_columns(),
            sa.Column("workflow_id", sa.String(36), nullable=False, index=True),
            sa.Column("source_node_id", sa.String(36), nullable=False, index=True),
            sa.Column("target_node_id", sa.String(36), nullable=False, index=True),
            sa.Column("mapping_json", sa.Text, default="[]"),
            sa.Column("condition_json", sa.Text, default="{}"),
        )

    if "workflow_versions" not in tables:
        op.create_table(
            "workflow_versions",
            *_base_columns(),
            sa.Column("workflow_id", sa.String(36), nullable=False, index=True),
            sa.Column("version", sa.String(32), nullable=False),
            sa.Column("status", sa.String(16), default="published"),
            sa.Column("snapshot_json", sa.Text, nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "workflow_versions" in tables:
        op.drop_table("workflow_versions")
    if "workflow_definitions" in tables:
        columns = {column["name"] for column in inspector.get_columns("workflow_definitions")}
        if "published_version_id" in columns:
            op.drop_index("ix_workflow_definitions_published_version_id", table_name="workflow_definitions")
            op.drop_column("workflow_definitions", "published_version_id")
