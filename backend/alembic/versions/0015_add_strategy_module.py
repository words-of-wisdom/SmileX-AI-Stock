"""add AI strategy analysis module

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-16

1. 创建 AI 分析策略表、策略执行记录表、策略模拟持仓表、持仓跟踪日志表
2. 在「AI助手」一级目录下新增「AI 分析」子菜单(MENU) + 按钮权限
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = '0015'
down_revision: Union[str, Sequence[str], None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 菜单 ID（AI 助手目录 8001，0014 用到 8007，取 8008~8012）----
_AI_DIR_ID = 2942406616008001
_STRATEGY_MENU_ID = 2942406616008008
_STRATEGY_BTN_MANAGE_ID = 2942406616008009
_STRATEGY_BTN_RUN_ID = 2942406616008010
_STRATEGY_BTN_CLOSE_ID = 2942406616008011

_DT = datetime(2026, 8, 16, 12, 0, 0)

_MENU_TABLE = sa.table(
    'sys_menu',
    sa.column('id', sa.BigInteger),
    sa.column('parent_id', sa.BigInteger),
    sa.column('name', sa.String),
    sa.column('path', sa.String),
    sa.column('component', sa.String),
    sa.column('redirect', sa.String),
    sa.column('permission', sa.String),
    sa.column('meta_icon', sa.String),
    sa.column('meta_hidden', sa.Boolean),
    sa.column('meta_affix', sa.Boolean),
    sa.column('meta_breadcrumb', sa.Boolean),
    sa.column('status', sa.Boolean),
    sa.column('type', sa.String),
    sa.column('sort', sa.Integer),
    sa.column('is_system', sa.Boolean),
    sa.column('meta_href', sa.String),
    sa.column('meta_keep_alive', sa.Boolean),
    sa.column('deleted_at', sa.DateTime),
    sa.column('created_at', sa.DateTime),
    sa.column('updated_at', sa.DateTime),
)


def _menu_row(menu_id, parent_id, name, path, component, permission, icon, menu_type, sort):
    return {
        'id': menu_id,
        'parent_id': parent_id,
        'name': name,
        'path': path,
        'component': component,
        'redirect': None,
        'permission': permission,
        'meta_icon': icon,
        'meta_hidden': False,
        'meta_affix': False,
        'meta_breadcrumb': True,
        'status': True,
        'type': menu_type,
        'sort': sort,
        'is_system': True,
        'meta_href': None,
        'meta_keep_alive': False,
        'deleted_at': None,
        'created_at': _DT,
        'updated_at': None,
    }


def _btn_row(btn_id, parent_id, name, permission, sort):
    return {
        'id': btn_id,
        'parent_id': parent_id,
        'name': name,
        'path': None,
        'component': None,
        'redirect': None,
        'permission': permission,
        'meta_icon': None,
        'meta_hidden': True,
        'meta_affix': False,
        'meta_breadcrumb': True,
        'status': True,
        'type': 'BUTTON',
        'sort': sort,
        'is_system': True,
        'meta_href': None,
        'meta_keep_alive': False,
        'deleted_at': None,
        'created_at': _DT,
        'updated_at': None,
    }


_BASE_COLUMNS = [
    sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
]


def _base_pk():
    return sa.PrimaryKeyConstraint('id')


def upgrade() -> None:
    # ================================================================
    # 1. AI 分析策略配置表
    # ================================================================
    op.create_table(
        'business_ai_strategy',
        *_BASE_COLUMNS,
        sa.Column('name', sa.String(length=100), nullable=False, comment='策略名称'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='策略描述'),
        sa.Column('prompt_template', sa.Text(), nullable=True, comment='策略定制提示词（选股逻辑、风控要求等）'),
        sa.Column('stock_pool', sa.JSON(), nullable=True, comment='股票池：{"codes": [...]}，为空则由 AI 在全市场内自主选择'),
        sa.Column('execute_periods', sa.JSON(), nullable=True, comment='执行时段列表：pre_market/morning/noon/tail/post_close'),
        sa.Column('max_positions', sa.Integer(), nullable=False, comment='最大同时持仓数'),
        sa.Column('stop_loss_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='默认止损比例(%)，相对买价'),
        sa.Column('take_profit_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='默认止盈比例(%)，相对买价'),
        sa.Column('status', sa.Boolean(), nullable=False, comment='状态：True-启用，False-停用'),
        sa.Column('last_executed_at', sa.DateTime(timezone=True), nullable=True, comment='最近执行时间'),
        _base_pk(),
        comment='AI 分析策略配置表',
    )
    op.create_index(op.f('ix_business_ai_strategy_id'), 'business_ai_strategy', ['id'], unique=True)
    op.create_index('ix_ai_strategy_status', 'business_ai_strategy', ['status'], unique=False)

    # ================================================================
    # 2. 策略执行记录表
    # ================================================================
    op.create_table(
        'business_strategy_run',
        *_BASE_COLUMNS,
        sa.Column('strategy_id', sa.Integer(), nullable=False, comment='策略 ID'),
        sa.Column('strategy_name', sa.String(length=100), nullable=False, comment='策略名称（执行时快照）'),
        sa.Column('run_period', sa.String(length=20), nullable=False, comment='执行时段：pre_market/morning/noon/tail/post_close/manual'),
        sa.Column('run_date', sa.String(length=10), nullable=False, comment='执行日期 YYYY-MM-DD（同日同时段去重用）'),
        sa.Column('trigger_type', sa.String(length=20), nullable=False, comment='触发方式：schedule-定时，manual-手动'),
        sa.Column('status', sa.Boolean(), nullable=False, comment='执行状态：True-成功，False-失败'),
        sa.Column('ai_raw_response', sa.Text(), nullable=True, comment='AI 原始回复文本'),
        sa.Column('parsed_signals', sa.JSON(), nullable=True, comment='解析后的结构化信号列表'),
        sa.Column('opened_count', sa.Integer(), nullable=False, comment='本次新建仓数量'),
        sa.Column('closed_count', sa.Integer(), nullable=False, comment='本次平仓数量'),
        sa.Column('error_msg', sa.Text(), nullable=True, comment='错误信息'),
        _base_pk(),
        comment='策略执行记录表',
    )
    op.create_index(op.f('ix_business_strategy_run_id'), 'business_strategy_run', ['id'], unique=True)
    op.create_index('ix_strategy_run_strategy', 'business_strategy_run', ['strategy_id', 'created_at'], unique=False)

    # ================================================================
    # 3. 策略个股模拟持仓表
    # ================================================================
    op.create_table(
        'business_strategy_position',
        *_BASE_COLUMNS,
        sa.Column('strategy_id', sa.Integer(), nullable=False, comment='策略 ID'),
        sa.Column('strategy_name', sa.String(length=100), nullable=False, comment='策略名称（建仓时快照）'),
        sa.Column('stock_code', sa.String(length=20), nullable=False, comment='证券代码'),
        sa.Column('stock_name', sa.String(length=50), nullable=False, comment='证券简称'),
        sa.Column('buy_price', sa.Numeric(precision=16, scale=4), nullable=False, comment='买入价（信号触发时最新价）'),
        sa.Column('buy_time', sa.DateTime(timezone=True), nullable=False, comment='买入时间'),
        sa.Column('buy_reason', sa.Text(), nullable=True, comment='AI 给出的买入理由'),
        sa.Column('quantity', sa.Integer(), nullable=False, comment='持仓数量（股，默认一手）'),
        sa.Column('target_sell_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='预估卖点（目标价）'),
        sa.Column('stop_loss_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='止损价'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='持仓状态：holding/closed/cancelled'),
        sa.Column('latest_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='最新价（跟踪任务刷新）'),
        sa.Column('floating_pnl_pct', sa.Numeric(precision=10, scale=4), nullable=True, comment='浮动盈亏比例(%)'),
        sa.Column('tracked_at', sa.DateTime(timezone=True), nullable=True, comment='最近跟踪时间'),
        sa.Column('sell_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='卖出价'),
        sa.Column('sell_time', sa.DateTime(timezone=True), nullable=True, comment='卖出时间'),
        sa.Column('sell_reason', sa.String(length=500), nullable=True, comment='卖出原因：stop_loss/take_profit/target_reached/ai_signal/manual'),
        sa.Column('return_rate', sa.Numeric(precision=10, scale=4), nullable=True, comment='最终收益率(%)，平仓时计算'),
        _base_pk(),
        comment='策略个股模拟持仓表',
    )
    op.create_index(op.f('ix_business_strategy_position_id'), 'business_strategy_position', ['id'], unique=True)
    op.create_index('ix_strategy_position_strategy_status', 'business_strategy_position', ['strategy_id', 'status'], unique=False)
    op.create_index('ix_strategy_position_stock', 'business_strategy_position', ['stock_code'], unique=False)

    # ================================================================
    # 4. 持仓跟踪日志表
    # ================================================================
    op.create_table(
        'business_position_track_log',
        *_BASE_COLUMNS,
        sa.Column('position_id', sa.Integer(), nullable=False, comment='持仓 ID'),
        sa.Column('track_time', sa.DateTime(timezone=True), nullable=False, comment='跟踪时间'),
        sa.Column('latest_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='当时最新价'),
        sa.Column('pnl_pct', sa.Numeric(precision=10, scale=4), nullable=True, comment='当时浮动盈亏(%)'),
        sa.Column('ai_adjusted_target', sa.Numeric(precision=16, scale=4), nullable=True, comment='AI 本次调整后的预估卖点'),
        sa.Column('adjust_reason', sa.String(length=500), nullable=True, comment='调整理由（未调整为空）'),
        _base_pk(),
        comment='持仓跟踪日志表',
    )
    op.create_index(op.f('ix_business_position_track_log_id'), 'business_position_track_log', ['id'], unique=True)
    op.create_index('ix_position_track_position', 'business_position_track_log', ['position_id', 'track_time'], unique=False)

    # ================================================================
    # 5. 新增「AI 分析」菜单 + 按钮权限（挂在 AI 助手目录下，sort=3）
    # ================================================================
    op.bulk_insert(_MENU_TABLE, [
        _menu_row(
            _STRATEGY_MENU_ID, _AI_DIR_ID,
            'ai_analysis', '/ai/analysis',
            'view.ai_analysis',
            'strategy:position:list',
            'mdi:chart-line', 'MENU', 3,
        ),
        _btn_row(_STRATEGY_BTN_MANAGE_ID, _STRATEGY_MENU_ID,
                 'strategy_manage', 'strategy:manage', 1),
        _btn_row(_STRATEGY_BTN_RUN_ID, _STRATEGY_MENU_ID,
                 'strategy_run', 'strategy:run', 2),
        _btn_row(_STRATEGY_BTN_CLOSE_ID, _STRATEGY_MENU_ID,
                 'position_close', 'strategy:position:close', 3),
    ])


def downgrade() -> None:
    # 删除菜单 + 权限
    _menu_ids = [
        _STRATEGY_BTN_MANAGE_ID, _STRATEGY_BTN_RUN_ID, _STRATEGY_BTN_CLOSE_ID,
        _STRATEGY_MENU_ID,
    ]
    op.execute(
        f"DELETE FROM sys_menu WHERE id IN ({', '.join(str(i) for i in _menu_ids)})"
    )

    op.drop_index('ix_position_track_position', table_name='business_position_track_log')
    op.drop_index(op.f('ix_business_position_track_log_id'), table_name='business_position_track_log')
    op.drop_table('business_position_track_log')

    op.drop_index('ix_strategy_position_stock', table_name='business_strategy_position')
    op.drop_index('ix_strategy_position_strategy_status', table_name='business_strategy_position')
    op.drop_index(op.f('ix_business_strategy_position_id'), table_name='business_strategy_position')
    op.drop_table('business_strategy_position')

    op.drop_index('ix_strategy_run_strategy', table_name='business_strategy_run')
    op.drop_index(op.f('ix_business_strategy_run_id'), table_name='business_strategy_run')
    op.drop_table('business_strategy_run')

    op.drop_index('ix_ai_strategy_status', table_name='business_ai_strategy')
    op.drop_index(op.f('ix_business_ai_strategy_id'), table_name='business_ai_strategy')
    op.drop_table('business_ai_strategy')
