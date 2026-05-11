"""strategy and agent tables

Revision ID: 20260510_000002
Revises: 20260510_000001
Create Date: 2026-05-10 00:00:02.000000+00:00

"""
import json
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260510_000002'
down_revision = '20260510_000001'
branch_labels = None
depends_on = None


# ── helpers ──────────────────────────────────────────────────────────────────
def _base_columns() -> list:
    """Return the standard BaseModel columns shared by every table."""
    return [
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True),
        sa.Column('metadata_json', sa.String(2048), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    # ── strategies ──
    op.create_table(
        'strategies',
        *_base_columns(),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('family', sa.String(64), nullable=False, index=True),
        sa.Column('type', sa.String(32), nullable=False, index=True),
        sa.Column('status', sa.String(32), default='draft', index=True),
        sa.Column('owner_id', sa.String(36), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('risk_profile', sa.String(32), default='balanced'),
        sa.Column('market', sa.String(32), default='A'),
        sa.Column('universe', sa.String(512), nullable=True),
        sa.Column('frequency', sa.String(16), default='1d'),
        sa.Column('sharpe', sa.Float, nullable=True),
        sa.Column('max_dd', sa.Float, nullable=True),
        sa.Column('annual_return', sa.Float, nullable=True),
        sa.Column('oos_score', sa.Float, nullable=True),
    )

    # ── strategy_versions ──
    op.create_table(
        'strategy_versions',
        *_base_columns(),
        sa.Column('strategy_id', sa.String(36), nullable=False, index=True),
        sa.Column('version', sa.String(32), nullable=False),
        sa.Column('code_uri', sa.String(512), nullable=True),
        sa.Column('code_text', sa.Text, nullable=True),
        sa.Column('params_schema', sa.Text, nullable=True),
        sa.Column('risk_rules', sa.Text, nullable=True),
        sa.Column('status', sa.String(32), default='draft'),
    )

    # ── strategy_tasks ──
    op.create_table(
        'strategy_tasks',
        *_base_columns(),
        sa.Column('prompt', sa.Text, nullable=False),
        sa.Column('market', sa.String(32), default='A'),
        sa.Column('risk_profile', sa.String(32), default='balanced'),
        sa.Column('status', sa.String(32), default='queued', index=True),
        sa.Column('agent_task_id', sa.String(36), nullable=True),
        sa.Column('strategy_id', sa.String(36), nullable=True, index=True),
        sa.Column('result', sa.Text, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
    )

    # ── strategy_pipeline_events ──
    op.create_table(
        'strategy_pipeline_events',
        *_base_columns(),
        sa.Column('strategy_id', sa.String(36), nullable=False, index=True),
        sa.Column('stage', sa.String(32), nullable=False, index=True),
        sa.Column('event', sa.String(64), nullable=False),
        sa.Column('progress', sa.Integer, default=0),
        sa.Column('detail', sa.Text, nullable=True),
    )

    # ── strategy_templates ──
    op.create_table(
        'strategy_templates',
        *_base_columns(),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('risk_level', sa.String(32), default='balanced'),
        sa.Column('market', sa.String(32), default='A'),
        sa.Column('family', sa.String(64), nullable=False),
        sa.Column('template_uri', sa.String(512), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
    )

    # ── agent_registry ──
    op.create_table(
        'agent_registry',
        *_base_columns(),
        sa.Column('name', sa.String(64), nullable=False, unique=True),
        sa.Column('role', sa.String(32), nullable=False),
        sa.Column('status', sa.String(16), default='idle'),
        sa.Column('current_task', sa.String(256), nullable=True),
        sa.Column('metric', sa.String(64), nullable=True),
        sa.Column('heartbeat_at', sa.String(64), nullable=True),
        sa.Column('config_json', sa.Text, nullable=True),
    )

    # ── agent_tasks ──
    op.create_table(
        'agent_tasks',
        *_base_columns(),
        sa.Column('agent_id', sa.String(36), nullable=False, index=True),
        sa.Column('task_type', sa.String(64), nullable=False),
        sa.Column('payload_json', sa.Text, nullable=True),
        sa.Column('priority', sa.Integer, default=0),
        sa.Column('status', sa.String(16), default='pending'),
        sa.Column('result_json', sa.Text, nullable=True),
        sa.Column('started_at', sa.String(64), nullable=True),
        sa.Column('completed_at', sa.String(64), nullable=True),
    )

    # ── agent_messages ──
    op.create_table(
        'agent_messages',
        *_base_columns(),
        sa.Column('from_agent', sa.String(36), nullable=False, index=True),
        sa.Column('to_agent', sa.String(36), nullable=True, index=True),
        sa.Column('msg_type', sa.String(32), nullable=False),
        sa.Column('topic', sa.String(128), nullable=False),
        sa.Column('payload_json', sa.Text, nullable=False),
        sa.Column('correlation_id', sa.String(64), nullable=True, index=True),
    )

    # ── tool_registry ──
    op.create_table(
        'tool_registry',
        *_base_columns(),
        sa.Column('name', sa.String(128), nullable=False, unique=True),
        sa.Column('level', sa.String(16), default='low'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('allowed_agents', sa.Text, nullable=True),
        sa.Column('schema_json', sa.Text, nullable=True),
        sa.Column('enabled', sa.Boolean, default=True),
    )

    # ── seed agent_registry (8 agents) ──
    now = datetime.now(timezone.utc)
    agents_seed = [
        ('agent-research', 'Research Agent', 'research', '扫描宏观因子 / 行业轮动', '召回: 87%'),
        ('agent-strategy', 'Strategy Agent', 'strategy', '生成 / 修改策略代码', '通过率: 92%'),
        ('agent-backtest', 'Backtest Agent', 'backtest', 'IS/OOS 回测 + Walk-forward', '完成: 1,243'),
        ('agent-risk', 'Risk Agent', 'risk', '实时风控审批 / 熔断', '阻断: 12'),
        ('agent-execution', 'Execution Agent', 'execution', '订单路由 / TWAP / VWAP', '滑点: 6.4bps'),
        ('agent-portfolio', 'Portfolio Agent', 'portfolio', '组合优化 / 再平衡建议', '夏普: 2.18'),
        ('agent-explain', 'Explain Agent', 'explain', '决策解释 / 信号溯源', 'XAI 覆盖: 100%'),
        ('agent-data', 'Data Agent', 'data', '数据质量 / 偏差检测', 'P95: 64ms'),
    ]

    op.bulk_insert(
        sa.table(
            'agent_registry',
            sa.Column('id', sa.String(36)),
            sa.Column('org_id', sa.String(36)),
            sa.Column('created_at', sa.DateTime(timezone=True)),
            sa.Column('updated_at', sa.DateTime(timezone=True)),
            sa.Column('created_by', sa.String(36)),
            sa.Column('updated_by', sa.String(36)),
            sa.Column('trace_id', sa.String(64)),
            sa.Column('metadata_json', sa.String(2048)),
            sa.Column('deleted_at', sa.DateTime(timezone=True)),
            sa.Column('name', sa.String(64)),
            sa.Column('role', sa.String(32)),
            sa.Column('status', sa.String(16)),
            sa.Column('current_task', sa.String(256)),
            sa.Column('metric', sa.String(64)),
            sa.Column('heartbeat_at', sa.String(64)),
            sa.Column('config_json', sa.Text),
        ),
        [
            {
                'id': agent_id,
                'org_id': None,
                'created_at': now,
                'updated_at': now,
                'created_by': 'system',
                'updated_by': 'system',
                'trace_id': None,
                'metadata_json': None,
                'deleted_at': None,
                'name': name,
                'role': role,
                'status': 'idle',
                'current_task': current,
                'metric': metric,
                'heartbeat_at': now.isoformat(),
                'config_json': None,
            }
            for agent_id, name, role, current, metric in agents_seed
        ],
    )

    # ── seed tool_registry (5 tools, L1-L5 levels) ──
    tools_seed = [
        (
            'tool-data-read',
            'data.read',
            'low',
            '读取行情 / 因子库（只读）',
            ['research', 'strategy', 'backtest', 'risk', 'portfolio', 'explain', 'data'],
        ),
        (
            'tool-backtest-run',
            'backtest.run',
            'low',
            '提交回测任务（沙盒环境，无资金动作）',
            ['strategy', 'backtest'],
        ),
        (
            'tool-paper-order',
            'paper.order',
            'medium',
            '提交模拟盘订单（无真实资金影响）',
            ['strategy', 'execution', 'portfolio'],
        ),
        (
            'tool-live-order',
            'live.order',
            'high',
            '提交实盘订单（必须人工二审）',
            ['execution'],
        ),
        (
            'tool-withdrawal',
            'fund.withdrawal',
            'high',
            '资金出金 / 转账（默认禁用，需 Vault 解锁）',
            [],
        ),
    ]

    op.bulk_insert(
        sa.table(
            'tool_registry',
            sa.Column('id', sa.String(36)),
            sa.Column('org_id', sa.String(36)),
            sa.Column('created_at', sa.DateTime(timezone=True)),
            sa.Column('updated_at', sa.DateTime(timezone=True)),
            sa.Column('created_by', sa.String(36)),
            sa.Column('updated_by', sa.String(36)),
            sa.Column('trace_id', sa.String(64)),
            sa.Column('metadata_json', sa.String(2048)),
            sa.Column('deleted_at', sa.DateTime(timezone=True)),
            sa.Column('name', sa.String(128)),
            sa.Column('level', sa.String(16)),
            sa.Column('description', sa.Text),
            sa.Column('allowed_agents', sa.Text),
            sa.Column('schema_json', sa.Text),
            sa.Column('enabled', sa.Boolean),
        ),
        [
            {
                'id': tool_id,
                'org_id': None,
                'created_at': now,
                'updated_at': now,
                'created_by': 'system',
                'updated_by': 'system',
                'trace_id': None,
                'metadata_json': None,
                'deleted_at': None,
                'name': name,
                'level': level,
                'description': desc,
                'allowed_agents': json.dumps(allowed),
                'schema_json': None,
                'enabled': name != 'fund.withdrawal',
            }
            for tool_id, name, level, desc, allowed in tools_seed
        ],
    )

    # ── seed strategy_templates (3 starter templates) ──
    templates_seed = [
        (
            'tmpl-value',
            'A 股价值精选',
            'balanced',
            'A',
            'value',
            '基于 ROE>15% / PE 分位 < 30% 的多因子价值策略',
        ),
        (
            'tmpl-momentum',
            '动量轮动 (60/20)',
            'aggressive',
            'A',
            'momentum',
            '60 日动量 + 20 日回看的板块轮动策略',
        ),
        (
            'tmpl-mean-reversion',
            '均值回归 (5/20)',
            'conservative',
            'A',
            'mean_reversion',
            '基于布林带 + RSI 的均值回归',
        ),
    ]

    op.bulk_insert(
        sa.table(
            'strategy_templates',
            sa.Column('id', sa.String(36)),
            sa.Column('org_id', sa.String(36)),
            sa.Column('created_at', sa.DateTime(timezone=True)),
            sa.Column('updated_at', sa.DateTime(timezone=True)),
            sa.Column('created_by', sa.String(36)),
            sa.Column('updated_by', sa.String(36)),
            sa.Column('trace_id', sa.String(64)),
            sa.Column('metadata_json', sa.String(2048)),
            sa.Column('deleted_at', sa.DateTime(timezone=True)),
            sa.Column('name', sa.String(128)),
            sa.Column('risk_level', sa.String(32)),
            sa.Column('market', sa.String(32)),
            sa.Column('family', sa.String(64)),
            sa.Column('template_uri', sa.String(512)),
            sa.Column('description', sa.Text),
        ),
        [
            {
                'id': tmpl_id,
                'org_id': None,
                'created_at': now,
                'updated_at': now,
                'created_by': 'system',
                'updated_by': 'system',
                'trace_id': None,
                'metadata_json': None,
                'deleted_at': None,
                'name': name,
                'risk_level': risk,
                'market': market,
                'family': family,
                'template_uri': None,
                'description': desc,
            }
            for tmpl_id, name, risk, market, family, desc in templates_seed
        ],
    )


def downgrade() -> None:
    op.drop_table('tool_registry')
    op.drop_table('agent_messages')
    op.drop_table('agent_tasks')
    op.drop_table('agent_registry')
    op.drop_table('strategy_templates')
    op.drop_table('strategy_pipeline_events')
    op.drop_table('strategy_tasks')
    op.drop_table('strategy_versions')
    op.drop_table('strategies')
