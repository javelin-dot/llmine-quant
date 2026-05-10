"""init identity and audit

Revision ID: 20260510_000001
Revises:
Create Date: 2026-05-10 00:00:01.000000+00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260510_000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── organizations ──
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True),
        sa.Column('metadata_json', sa.String(2048), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('status', sa.String(32), default='active'),
        sa.Column('plan', sa.String(32), default='free'),
    )

    # ── users ──
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True),
        sa.Column('metadata_json', sa.String(2048), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email', sa.String(256), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('hashed_password', sa.String(256), nullable=True),
        sa.Column('status', sa.String(32), default='active'),
        sa.Column('mfa_enabled', sa.Boolean, default=False),
    )

    # ── roles ──
    op.create_table(
        'roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True),
        sa.Column('metadata_json', sa.String(2048), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('scope', sa.String(32), default='global'),
        sa.Column('description', sa.String(512), nullable=True),
    )

    # ── user_roles ──
    op.create_table(
        'user_roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True),
        sa.Column('metadata_json', sa.String(2048), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('role_id', sa.String(36), nullable=False, index=True),
    )

    # ── sessions ──
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True),
        sa.Column('metadata_json', sa.String(2048), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('token_hash', sa.String(256), nullable=False),
        sa.Column('expires_at', sa.String(64), nullable=True),
        sa.Column('ip_address', sa.String(64), nullable=True),
    )

    # ── audit_logs ──
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True, index=True),
        sa.Column('metadata_json', sa.String(2048), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actor', sa.String(128), nullable=False, index=True),
        sa.Column('actor_type', sa.String(32), default='system'),
        sa.Column('action', sa.String(128), nullable=False, index=True),
        sa.Column('resource_type', sa.String(64), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=True, index=True),
        sa.Column('result', sa.String(32), default='success'),
        sa.Column('result_tone', sa.String(16), default='green'),
        sa.Column('confidence', sa.Float, nullable=True),
        sa.Column('detail', sa.Text, nullable=True),
        sa.Column('ip_address', sa.String(64), nullable=True),
        sa.Column('prev_hash', sa.String(128), nullable=True),
        sa.Column('curr_hash', sa.String(128), nullable=True),
    )

    # ── idempotency_keys ──
    op.create_table(
        'idempotency_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True),
        sa.Column('metadata_json', sa.String(2048), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('key', sa.String(256), nullable=False, unique=True, index=True),
        sa.Column('scope', sa.String(128), nullable=False),
        sa.Column('request_hash', sa.String(256), nullable=True),
        sa.Column('response_body', sa.Text, nullable=True),
        sa.Column('status_code', sa.Integer, nullable=True),
    )

    # ── event_outbox ──
    op.create_table(
        'event_outbox',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True),
        sa.Column('metadata_json', sa.String(2048), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('event_type', sa.String(128), nullable=False, index=True),
        sa.Column('payload', sa.Text, nullable=False),
        sa.Column('status', sa.String(32), default='pending', index=True),
        sa.Column('published_at', sa.String(64), nullable=True),
        sa.Column('error', sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('event_outbox')
    op.drop_table('idempotency_keys')
    op.drop_table('audit_logs')
    op.drop_table('sessions')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('organizations')
