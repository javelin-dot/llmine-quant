"""strategy_task_backtest_link

Revision ID: c029ffadba27
Revises: 20260512_000004
Create Date: 2026-05-12 22:58:34.801325+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c029ffadba27'
down_revision = '20260512_000004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('strategy_tasks', sa.Column('backtest_task_id', sa.String(length=36), nullable=True))
    op.add_column('strategy_tasks', sa.Column('backtest_run_id', sa.String(length=36), nullable=True))
    op.create_index(op.f('ix_strategy_tasks_backtest_task_id'), 'strategy_tasks', ['backtest_task_id'], unique=False)
    op.create_index(op.f('ix_strategy_tasks_backtest_run_id'), 'strategy_tasks', ['backtest_run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_strategy_tasks_backtest_run_id'), table_name='strategy_tasks')
    op.drop_index(op.f('ix_strategy_tasks_backtest_task_id'), table_name='strategy_tasks')
    op.drop_column('strategy_tasks', 'backtest_run_id')
    op.drop_column('strategy_tasks', 'backtest_task_id')
