"""stock info (symbol -> name) table

Revision ID: 20260516_000002
Revises: 20260516_000001
Create Date: 2026-05-16 00:00:02.000000+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260516_000002"
down_revision = "20260516_000001"
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
        "stock_info",
        *_base_columns(),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("name", sa.String(64), nullable=False, server_default=""),
        sa.Column("board", sa.String(16), nullable=True),
        sa.Column("is_st", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_synced_at", sa.String(64), nullable=True),
        sa.UniqueConstraint("symbol", name="uq_stock_info_symbol"),
    )
    op.create_index("ix_stock_info_org_id", "stock_info", ["org_id"])
    op.create_index("ix_stock_info_symbol", "stock_info", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_stock_info_symbol", table_name="stock_info")
    op.drop_index("ix_stock_info_org_id", table_name="stock_info")
    op.drop_table("stock_info")
