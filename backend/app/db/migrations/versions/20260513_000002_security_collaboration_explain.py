"""security, collaboration, and explain tables

Revision ID: 20260513_000002
Revises: 20260513_000001
Create Date: 2026-05-13 10:30:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

revision = "20260513_000002"
down_revision = "20260513_000001"
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
    # ── Security ───────────────────────────────────────────────────
    op.create_table(
        "vault_keys",
        *_base_columns(),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("key_type", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("rotated_at", sa.String(32), nullable=True),
        sa.Column("expires_at", sa.String(32), nullable=True),
        sa.Column("days_to_expiry", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("status", sa.String(16), nullable=False, server_default="'active'"),
        sa.Column("scope", sa.String(256), nullable=True),
        sa.Column("encrypted_value", sa.Text(), nullable=True),
    )

    op.create_table(
        "ai_permissions",
        *_base_columns(),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("api_name", sa.String(128), nullable=False),
        sa.Column("desc", sa.Text(), nullable=True),
        sa.Column("allowed", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("reason", sa.Text(), nullable=True),
    )

    op.create_table(
        "withdrawal_rules",
        *_base_columns(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("desc", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="'enabled'"),
    )

    op.create_table(
        "security_events",
        *_base_columns(),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="'info'"),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("actor", sa.String(128), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="'resolved'"),
    )

    # ── Collaboration ──────────────────────────────────────────────
    op.create_table(
        "strategy_reviews",
        *_base_columns(),
        sa.Column("strategy_id", sa.String(36), nullable=False),
        sa.Column("from_version", sa.String(32), nullable=False),
        sa.Column("to_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="'pending'"),
        sa.Column("priority", sa.String(16), nullable=False, server_default="'medium'"),
    )
    op.create_index("ix_strategy_reviews_strategy_id", "strategy_reviews", ["strategy_id"])

    op.create_table(
        "reviewer_decisions",
        *_base_columns(),
        sa.Column("review_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False, server_default="'pending'"),
    )
    op.create_index("ix_reviewer_decisions_review_id", "reviewer_decisions", ["review_id"])

    op.create_table(
        "ab_tests",
        *_base_columns(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("control_strategy", sa.String(36), nullable=False),
        sa.Column("variant_strategy", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="'pending'"),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("samples", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("improvement", sa.Float(), nullable=False, server_default="0"),
    )

    # ── Explain ────────────────────────────────────────────────────
    op.create_table(
        "signal_explanations",
        *_base_columns(),
        sa.Column("strategy_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("target", sa.String(32), nullable=False),
        sa.Column("size", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("risk_grade", sa.String(16), nullable=True),
        sa.Column("timestamp", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="'pending'"),
    )
    op.create_index("ix_signal_explanations_strategy_id", "signal_explanations", ["strategy_id"])

    op.create_table(
        "attribution_items",
        *_base_columns(),
        sa.Column("explanation_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("desc", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_attribution_items_explanation_id", "attribution_items", ["explanation_id"])

    op.create_table(
        "decision_steps",
        *_base_columns(),
        sa.Column("explanation_id", sa.String(36), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("desc", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("tag", sa.String(64), nullable=True),
        sa.Column("tone", sa.String(16), nullable=False, server_default="'blue'"),
    )
    op.create_index("ix_decision_steps_explanation_id", "decision_steps", ["explanation_id"])

    op.create_table(
        "lineage_records",
        *_base_columns(),
        sa.Column("explanation_id", sa.String(36), nullable=False),
        sa.Column("step", sa.String(128), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("permission", sa.String(32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_lineage_records_explanation_id", "lineage_records", ["explanation_id"])

    op.create_table(
        "bias_gate_checks",
        *_base_columns(),
        sa.Column("explanation_id", sa.String(36), nullable=False),
        sa.Column("check", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="'pass'"),
        sa.Column("desc", sa.Text(), nullable=True),
    )
    op.create_index("ix_bias_gate_checks_explanation_id", "bias_gate_checks", ["explanation_id"])

    op.create_table(
        "similar_cases",
        *_base_columns(),
        sa.Column("explanation_id", sa.String(36), nullable=False),
        sa.Column("date", sa.String(32), nullable=True),
        sa.Column("action", sa.String(16), nullable=True),
        sa.Column("target", sa.String(32), nullable=True),
        sa.Column("outcome", sa.String(256), nullable=True),
        sa.Column("return_pct", sa.Float(), nullable=True),
    )
    op.create_index("ix_similar_cases_explanation_id", "similar_cases", ["explanation_id"])


def downgrade() -> None:
    # Explain
    op.drop_table("similar_cases")
    op.drop_table("bias_gate_checks")
    op.drop_table("lineage_records")
    op.drop_table("decision_steps")
    op.drop_table("attribution_items")
    op.drop_table("signal_explanations")
    # Collaboration
    op.drop_table("ab_tests")
    op.drop_table("reviewer_decisions")
    op.drop_table("strategy_reviews")
    # Security
    op.drop_table("security_events")
    op.drop_table("withdrawal_rules")
    op.drop_table("ai_permissions")
    op.drop_table("vault_keys")
