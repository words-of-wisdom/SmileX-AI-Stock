"""add A-stock market module (tables + menu restructure)

Revision ID: 0010
Revises: 0009, e7ac2bb48021
Create Date: 2026-08-10

1. 创建大盘指数日快照表、行业/概念板块日快照表、涨停股池日快照表
2. 新增「A股」一级目录(CATALOG)，将「股票热榜」从「资讯」迁移到 A 股下，
   新增大盘概览 / 行业板块 / 热门个股 子菜单(MENU) + 按钮权限
3. 旧 stock_hot 路由 key 从 info_stock-hot → a-stock_stock-hot，
   API 路径从 /admin/sys/stock-hot/ → /admin/stock/stock-hot/
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = '0010'
down_revision: Union[str, Sequence[str], None] = ('0009', 'e7ac2bb48021')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 菜单 ID ----
_A_STOCK_DIR_ID = 2942406616009001
# 迁移：原 info_stock-hot 菜单 (0006 迁移创建)
_STOCK_HOT_MENU_ID = 2942406616006002
_STOCK_HOT_BTN_LIST_ID = 2942406616006003
_STOCK_HOT_BTN_VIEW_ID = 2942406616006004
_STOCK_HOT_BTN_SYNC_ID = 2942406616006005
# 新增子菜单 + 按钮权限
_MARKET_OVERVIEW_MENU_ID = 2942406616009002
_MARKET_OVERVIEW_BTN_LIST_ID = 2942406616009003
_MARKET_OVERVIEW_BTN_SYNC_ID = 2942406616009004
_INDUSTRY_BOARD_MENU_ID = 2942406616009005
_INDUSTRY_BOARD_BTN_LIST_ID = 2942406616009006
_INDUSTRY_BOARD_BTN_SYNC_ID = 2942406616009007
_LIMIT_UP_MENU_ID = 2942406616009008
_LIMIT_UP_BTN_LIST_ID = 2942406616009009
_LIMIT_UP_BTN_SYNC_ID = 2942406616009010

_DT = datetime(2026, 8, 10, 12, 0, 0)

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
    # 1. 创建行情快照表
    # ================================================================
    op.create_table(
        'business_market_index_daily',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('record_date', sa.Date(), nullable=False, comment='快照日期'),
        sa.Column('index_code', sa.String(length=20), nullable=False, comment='指数代码'),
        sa.Column('index_name', sa.String(length=50), nullable=False, comment='指数名称'),
        sa.Column('latest_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='最新价'),
        sa.Column('change_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='涨跌幅(%)'),
        sa.Column('change_amount', sa.Numeric(precision=16, scale=4), nullable=True, comment='涨跌额'),
        sa.Column('volume', sa.Numeric(precision=20, scale=2), nullable=True, comment='成交量(手)'),
        sa.Column('turnover', sa.Numeric(precision=20, scale=2), nullable=True, comment='成交额(元)'),
        sa.Column('amplitude', sa.Numeric(precision=8, scale=4), nullable=True, comment='振幅(%)'),
        sa.Column('high', sa.Numeric(precision=16, scale=4), nullable=True, comment='最高'),
        sa.Column('low', sa.Numeric(precision=16, scale=4), nullable=True, comment='最低'),
        sa.Column('open', sa.Numeric(precision=16, scale=4), nullable=True, comment='今开'),
        sa.Column('prev_close', sa.Numeric(precision=16, scale=4), nullable=True, comment='昨收'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_date', 'index_code', name='uk_market_index_daily_date_code'),
        comment='大盘指数日快照表',
    )
    op.create_index(op.f('ix_business_market_index_daily_id'), 'business_market_index_daily', ['id'], unique=True)
    op.create_index('ix_business_market_index_daily_record_date', 'business_market_index_daily', ['record_date'], unique=False)
    op.create_index('ix_business_market_index_daily_index_code', 'business_market_index_daily', ['index_code'], unique=False)

    op.create_table(
        'business_board_daily',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('record_date', sa.Date(), nullable=False, comment='快照日期'),
        sa.Column('board_type', sa.String(length=20), nullable=False, comment='板块类型: industry/concept'),
        sa.Column('board_code', sa.String(length=20), nullable=False, comment='板块代码'),
        sa.Column('board_name', sa.String(length=100), nullable=False, comment='板块名称'),
        sa.Column('change_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='涨跌幅(%)'),
        sa.Column('turnover', sa.Numeric(precision=20, scale=2), nullable=True, comment='成交额(元)'),
        sa.Column('turnover_rate', sa.Numeric(precision=8, scale=4), nullable=True, comment='换手率(%)'),
        sa.Column('volume', sa.Numeric(precision=20, scale=2), nullable=True, comment='成交量(手)'),
        sa.Column('net_inflow', sa.Numeric(precision=20, scale=2), nullable=True, comment='主力净流入(元)'),
        sa.Column('rising_count', sa.Integer(), nullable=True, comment='上涨家数'),
        sa.Column('falling_count', sa.Integer(), nullable=True, comment='下跌家数'),
        sa.Column('leading_stock_code', sa.String(length=20), nullable=True, comment='领涨股代码'),
        sa.Column('leading_stock_name', sa.String(length=50), nullable=True, comment='领涨股名称'),
        sa.Column('leading_stock_change_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='领涨股涨跌幅(%)'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_date', 'board_type', 'board_code', name='uk_board_daily_date_type_code'),
        comment='行业/概念板块日快照表',
    )
    op.create_index(op.f('ix_business_board_daily_id'), 'business_board_daily', ['id'], unique=True)
    op.create_index('ix_business_board_daily_record_date', 'business_board_daily', ['record_date'], unique=False)
    op.create_index('ix_business_board_daily_board_type', 'business_board_daily', ['board_type'], unique=False)
    op.create_index('ix_business_board_daily_board_code', 'business_board_daily', ['board_code'], unique=False)

    op.create_table(
        'business_limit_up_stock',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('record_date', sa.Date(), nullable=False, comment='快照日期'),
        sa.Column('stock_code', sa.String(length=20), nullable=False, comment='股票代码'),
        sa.Column('stock_name', sa.String(length=50), nullable=False, comment='股票名称'),
        sa.Column('market_board', sa.String(length=20), nullable=False, comment='市场板块: main/chinext/star/bse'),
        sa.Column('latest_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='最新价'),
        sa.Column('change_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='涨跌幅(%)'),
        sa.Column('turnover_rate', sa.Numeric(precision=8, scale=4), nullable=True, comment='换手率(%)'),
        sa.Column('turnover', sa.Numeric(precision=20, scale=2), nullable=True, comment='成交额(元)'),
        sa.Column('amplitude', sa.Numeric(precision=8, scale=4), nullable=True, comment='振幅(%)'),
        sa.Column('seal_amount', sa.Numeric(precision=20, scale=2), nullable=True, comment='封板资金(元)'),
        sa.Column('first_limit_up_time', sa.String(length=20), nullable=True, comment='首次封板时间'),
        sa.Column('last_limit_up_time', sa.String(length=20), nullable=True, comment='最后封板时间'),
        sa.Column('break_count', sa.Integer(), nullable=True, comment='炸板次数'),
        sa.Column('consecutive_limit_up', sa.Integer(), nullable=True, comment='连板数'),
        sa.Column('industry', sa.String(length=100), nullable=True, comment='所属行业'),
        sa.Column('limit_up_reason', sa.String(length=500), nullable=True, comment='涨停原因'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_date', 'stock_code', name='uk_limit_up_daily_date_code'),
        comment='涨停股池日快照表',
    )
    op.create_index(op.f('ix_business_limit_up_stock_id'), 'business_limit_up_stock', ['id'], unique=True)
    op.create_index('ix_business_limit_up_stock_record_date', 'business_limit_up_stock', ['record_date'], unique=False)
    op.create_index('ix_business_limit_up_stock_stock_code', 'business_limit_up_stock', ['stock_code'], unique=False)
    op.create_index('ix_business_limit_up_stock_market_board', 'business_limit_up_stock', ['market_board'], unique=False)

    # ================================================================
    # 2. 新增「A股」一级目录
    # ================================================================
    op.bulk_insert(_MENU_TABLE, [
        _menu_row(
            _A_STOCK_DIR_ID, None, 'a-stock', '/a-stock',
            'layout.base', None,
            'mdi:chart-line', 'CATALOG', 8,
        ),
    ])

    # ================================================================
    # 3. 迁移「股票热榜」到 A 股目录下
    # ================================================================
    op.execute(
        f"UPDATE sys_menu SET "
        f"parent_id = {_A_STOCK_DIR_ID}, "
        f"path = '/a-stock/stock-hot', "
        f"name = 'a-stock_stock-hot', "
        f"component = 'view.a-stock_stock-hot', "
        f"sort = 4, "
        f"updated_at = '{_DT.isoformat(sep=' ')}' "
        f"WHERE id = {_STOCK_HOT_MENU_ID}"
    )

    # ================================================================
    # 4. 新增 大盘概览 / 行业板块 / 热门个股 菜单 + 权限
    # ================================================================
    op.bulk_insert(_MENU_TABLE, [
        # 大盘概览
        _menu_row(
            _MARKET_OVERVIEW_MENU_ID, _A_STOCK_DIR_ID,
            'a-stock_market-overview', '/a-stock/market-overview',
            'view.a-stock_market-overview',
            'stock:market:list',
            'mdi:chart-multiple', 'MENU', 1,
        ),
        _btn_row(_MARKET_OVERVIEW_BTN_LIST_ID, _MARKET_OVERVIEW_MENU_ID,
                 'market-overview_list', 'stock:market:list', 1),
        _btn_row(_MARKET_OVERVIEW_BTN_SYNC_ID, _MARKET_OVERVIEW_MENU_ID,
                 'market-overview_sync', 'stock:market:sync', 2),

        # 行业板块
        _menu_row(
            _INDUSTRY_BOARD_MENU_ID, _A_STOCK_DIR_ID,
            'a-stock_industry-board', '/a-stock/industry-board',
            'view.a-stock_industry-board',
            'stock:board:list',
            'mdi:view-dashboard', 'MENU', 2,
        ),
        _btn_row(_INDUSTRY_BOARD_BTN_LIST_ID, _INDUSTRY_BOARD_MENU_ID,
                 'industry-board_list', 'stock:board:list', 1),
        _btn_row(_INDUSTRY_BOARD_BTN_SYNC_ID, _INDUSTRY_BOARD_MENU_ID,
                 'industry-board_sync', 'stock:board:sync', 2),

        # 热门个股（涨停）
        _menu_row(
            _LIMIT_UP_MENU_ID, _A_STOCK_DIR_ID,
            'a-stock_limit-up', '/a-stock/limit-up',
            'view.a-stock_limit-up',
            'stock:limit_up:list',
            'mdi:trending-up', 'MENU', 3,
        ),
        _btn_row(_LIMIT_UP_BTN_LIST_ID, _LIMIT_UP_MENU_ID,
                 'limit-up_list', 'stock:limit_up:list', 1),
        _btn_row(_LIMIT_UP_BTN_SYNC_ID, _LIMIT_UP_MENU_ID,
                 'limit-up_sync', 'stock:limit_up:sync', 2),
    ])


def downgrade() -> None:
    # 删除新增菜单 + 权限
    _new_ids = [
        _MARKET_OVERVIEW_BTN_LIST_ID, _MARKET_OVERVIEW_BTN_SYNC_ID,
        _MARKET_OVERVIEW_MENU_ID,
        _INDUSTRY_BOARD_BTN_LIST_ID, _INDUSTRY_BOARD_BTN_SYNC_ID,
        _INDUSTRY_BOARD_MENU_ID,
        _LIMIT_UP_BTN_LIST_ID, _LIMIT_UP_BTN_SYNC_ID,
        _LIMIT_UP_MENU_ID,
    ]
    op.execute(
        f"DELETE FROM sys_menu WHERE id IN ({', '.join(str(i) for i in _new_ids)})"
    )

    # 恢复股票热榜到资讯目录
    _INFO_DIR_ID = 2942406616006001
    op.execute(
        f"UPDATE sys_menu SET "
        f"parent_id = {_INFO_DIR_ID}, "
        f"path = '/info/stock-hot', "
        f"name = 'info_stock-hot', "
        f"component = 'view.info_stock-hot', "
        f"sort = 2, "
        f"updated_at = '{_DT.isoformat(sep=' ')}' "
        f"WHERE id = {_STOCK_HOT_MENU_ID}"
    )

    # 删除 A 股一级目录
    op.execute(f"DELETE FROM sys_menu WHERE id = {_A_STOCK_DIR_ID}")

    # 删除行情表
    op.drop_index('ix_business_limit_up_stock_market_board', table_name='business_limit_up_stock')
    op.drop_index('ix_business_limit_up_stock_stock_code', table_name='business_limit_up_stock')
    op.drop_index('ix_business_limit_up_stock_record_date', table_name='business_limit_up_stock')
    op.drop_index(op.f('ix_business_limit_up_stock_id'), table_name='business_limit_up_stock')
    op.drop_table('business_limit_up_stock')

    op.drop_index('ix_business_board_daily_board_code', table_name='business_board_daily')
    op.drop_index('ix_business_board_daily_board_type', table_name='business_board_daily')
    op.drop_index('ix_business_board_daily_record_date', table_name='business_board_daily')
    op.drop_index(op.f('ix_business_board_daily_id'), table_name='business_board_daily')
    op.drop_table('business_board_daily')

    op.drop_index('ix_business_market_index_daily_index_code', table_name='business_market_index_daily')
    op.drop_index('ix_business_market_index_daily_record_date', table_name='business_market_index_daily')
    op.drop_index(op.f('ix_business_market_index_daily_id'), table_name='business_market_index_daily')
    op.drop_table('business_market_index_daily')
