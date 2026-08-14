"""add block trade (暗盘跟踪) module

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-12

1. 创建大宗交易每日统计快照表、活跃A股统计表、采集日志表
2. 在「A股」一级目录下新增「暗盘跟踪」子菜单(MENU) + 按钮权限
数据源：东方财富 data.eastmoney.com/dzjy/（akshare stock_dzjy_*）
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = '0013'
down_revision: Union[str, Sequence[str], None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 菜单 ID（紧接 limit-up 的 9010，取 9011~9013）----
_A_STOCK_DIR_ID = 2942406616009001
_BLOCK_TRADE_MENU_ID = 2942406616009011
_BLOCK_TRADE_BTN_LIST_ID = 2942406616009012
_BLOCK_TRADE_BTN_SYNC_ID = 2942406616009013

_DT = datetime(2026, 8, 12, 12, 0, 0)

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


def upgrade() -> None:
    # ================================================================
    # 1. 大宗交易每日统计快照表
    # ================================================================
    op.create_table(
        'business_block_trade_daily',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('record_date', sa.Date(), nullable=False, comment='交易日期（本地时区）'),
        sa.Column('stock_code', sa.String(length=20), nullable=False, comment='证券代码'),
        sa.Column('stock_name', sa.String(length=50), nullable=False, comment='证券简称'),
        sa.Column('change_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='涨跌幅(%)'),
        sa.Column('close_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='收盘价'),
        sa.Column('trade_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='成交价'),
        sa.Column('premium_rate', sa.Numeric(precision=10, scale=4), nullable=True, comment='折溢率(%)，正=溢价，负=折价'),
        sa.Column('trade_count', sa.Integer(), nullable=True, comment='成交笔数'),
        sa.Column('trade_volume', sa.Numeric(precision=20, scale=2), nullable=True, comment='成交总量(股)'),
        sa.Column('trade_amount', sa.Numeric(precision=20, scale=4), nullable=True, comment='成交总额(万元)'),
        sa.Column('amount_ratio', sa.Numeric(precision=10, scale=4), nullable=True, comment='成交总额/流通市值(%)'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_date', 'stock_code', name='uk_block_trade_daily_date_code'),
        comment='大宗交易每日统计快照表',
    )
    op.create_index(op.f('ix_business_block_trade_daily_id'), 'business_block_trade_daily', ['id'], unique=True)
    op.create_index('ix_business_block_trade_daily_record_date', 'business_block_trade_daily', ['record_date'], unique=False)
    op.create_index('ix_business_block_trade_daily_stock_code', 'business_block_trade_daily', ['stock_code'], unique=False)

    # ================================================================
    # 2. 大宗交易活跃A股统计表
    # ================================================================
    op.create_table(
        'business_block_trade_active',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('stat_window', sa.String(length=20), nullable=False, comment='统计窗口：近一月/近三月/近六月/近一年'),
        sa.Column('stock_code', sa.String(length=20), nullable=False, comment='证券代码'),
        sa.Column('stock_name', sa.String(length=50), nullable=False, comment='证券简称'),
        sa.Column('latest_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='最新价'),
        sa.Column('change_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='涨跌幅(%)'),
        sa.Column('last_list_date', sa.Date(), nullable=True, comment='最近上榜日'),
        sa.Column('list_count_total', sa.Integer(), nullable=True, comment='上榜次数-总计'),
        sa.Column('list_count_premium', sa.Integer(), nullable=True, comment='上榜次数-溢价'),
        sa.Column('list_count_discount', sa.Integer(), nullable=True, comment='上榜次数-折价'),
        sa.Column('total_amount', sa.Numeric(precision=20, scale=4), nullable=True, comment='总成交额(万元)'),
        sa.Column('premium_rate', sa.Numeric(precision=10, scale=4), nullable=True, comment='折溢率(%)'),
        sa.Column('amount_ratio', sa.Numeric(precision=10, scale=4), nullable=True, comment='成交总额/流通市值(%)'),
        sa.Column('avg_change_1d', sa.Numeric(precision=8, scale=4), nullable=True, comment='上榜后1日平均涨跌幅(%)'),
        sa.Column('avg_change_5d', sa.Numeric(precision=8, scale=4), nullable=True, comment='上榜后5日平均涨跌幅(%)'),
        sa.Column('avg_change_10d', sa.Numeric(precision=8, scale=4), nullable=True, comment='上榜后10日平均涨跌幅(%)'),
        sa.Column('avg_change_20d', sa.Numeric(precision=8, scale=4), nullable=True, comment='上榜后20日平均涨跌幅(%)'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stat_window', 'stock_code', name='uk_block_trade_active_window_code'),
        comment='大宗交易活跃A股统计表',
    )
    op.create_index(op.f('ix_business_block_trade_active_id'), 'business_block_trade_active', ['id'], unique=True)
    op.create_index('ix_business_block_trade_active_stat_window', 'business_block_trade_active', ['stat_window'], unique=False)
    op.create_index('ix_business_block_trade_active_stock_code', 'business_block_trade_active', ['stock_code'], unique=False)

    # ================================================================
    # 3. 大宗交易采集日志表
    # ================================================================
    op.create_table(
        'business_block_trade_sync_log',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('sub_board', sa.String(length=20), nullable=False, comment='子榜：daily-每日统计 / active-活跃A股'),
        sa.Column('stat_window', sa.String(length=20), nullable=True, comment='统计窗口（仅 active 子榜有值）'),
        sa.Column('status', sa.Boolean(), nullable=False, comment='采集状态：True-成功，False-失败'),
        sa.Column('fetched_count', sa.Integer(), nullable=False, comment='抓取条数'),
        sa.Column('saved_count', sa.Integer(), nullable=False, comment='入库条数'),
        sa.Column('error_msg', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='开始时间'),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True, comment='结束时间'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        comment='大宗交易采集日志表',
    )
    op.create_index(op.f('ix_business_block_trade_sync_log_id'), 'business_block_trade_sync_log', ['id'], unique=True)
    op.create_index('ix_business_block_trade_sync_log_sub_board', 'business_block_trade_sync_log', ['sub_board'], unique=False)

    # ================================================================
    # 4. 新增「暗盘跟踪」菜单 + 按钮权限（挂在 A 股目录下，sort=5）
    # ================================================================
    op.bulk_insert(_MENU_TABLE, [
        _menu_row(
            _BLOCK_TRADE_MENU_ID, _A_STOCK_DIR_ID,
            'a-stock_block-trade', '/a-stock/block-trade',
            'view.a-stock_block-trade',
            'stock:block_trade:list',
            'mdi:swap-horizontal', 'MENU', 5,
        ),
        _btn_row(_BLOCK_TRADE_BTN_LIST_ID, _BLOCK_TRADE_MENU_ID,
                 'block-trade_list', 'stock:block_trade:list', 1),
        _btn_row(_BLOCK_TRADE_BTN_SYNC_ID, _BLOCK_TRADE_MENU_ID,
                 'block-trade_sync', 'stock:block_trade:sync', 2),
    ])


def downgrade() -> None:
    # 删除菜单 + 权限
    _menu_ids = [
        _BLOCK_TRADE_BTN_LIST_ID, _BLOCK_TRADE_BTN_SYNC_ID,
        _BLOCK_TRADE_MENU_ID,
    ]
    op.execute(
        f"DELETE FROM sys_menu WHERE id IN ({', '.join(str(i) for i in _menu_ids)})"
    )

    # 删除采集日志表
    op.drop_index('ix_business_block_trade_sync_log_sub_board', table_name='business_block_trade_sync_log')
    op.drop_index(op.f('ix_business_block_trade_sync_log_id'), table_name='business_block_trade_sync_log')
    op.drop_table('business_block_trade_sync_log')

    # 删除活跃A股统计表
    op.drop_index('ix_business_block_trade_active_stock_code', table_name='business_block_trade_active')
    op.drop_index('ix_business_block_trade_active_stat_window', table_name='business_block_trade_active')
    op.drop_index(op.f('ix_business_block_trade_active_id'), table_name='business_block_trade_active')
    op.drop_table('business_block_trade_active')

    # 删除每日统计快照表
    op.drop_index('ix_business_block_trade_daily_stock_code', table_name='business_block_trade_daily')
    op.drop_index('ix_business_block_trade_daily_record_date', table_name='business_block_trade_daily')
    op.drop_index(op.f('ix_business_block_trade_daily_id'), table_name='business_block_trade_daily')
    op.drop_table('business_block_trade_daily')
