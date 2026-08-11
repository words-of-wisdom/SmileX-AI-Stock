"""add stock hot rank module + restructure info menu

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-10

1. 创建股票热榜快照表 + 采集日志表
2. 菜单重组：新增「资讯」一级目录(CATALOG)，将现有「资讯聚合」降为其子菜单，
   新增「股票热榜」子菜单(MENU) + 按钮权限。
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 菜单 ID ----
# 资讯一级目录
_INFO_DIR_ID = 2942406616006001
# 现有资讯聚合菜单（来自 0005 种子）
_NEWS_MENU_ID = 2942406616005001
# 股票热榜菜单 + 按钮权限
_STOCK_HOT_MENU_ID = 2942406616006002
_STOCK_HOT_BTN_LIST_ID = 2942406616006003
_STOCK_HOT_BTN_VIEW_ID = 2942406616006004
_STOCK_HOT_BTN_SYNC_ID = 2942406616006005

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


def upgrade() -> None:
    # ================================================================
    # 1. 创建股票热榜表
    # ================================================================
    op.create_table(
        'business_stock_hot_rank',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('record_date', sa.Date(), nullable=False, comment='排名快照日（本地时区）'),
        sa.Column('source', sa.String(length=50), nullable=False, comment='榜单源 key'),
        sa.Column('rank', sa.Integer(), nullable=False, comment='当日排名'),
        sa.Column('stock_code', sa.String(length=20), nullable=False, comment='股票代码'),
        sa.Column('stock_name', sa.String(length=50), nullable=False, comment='股票名称'),
        sa.Column('latest_price', sa.Numeric(precision=12, scale=4), nullable=True, comment='最新价'),
        sa.Column('change_pct', sa.Numeric(precision=8, scale=4), nullable=True, comment='涨跌幅(%)'),
        sa.Column('hot_value', sa.Numeric(precision=16, scale=4), nullable=True, comment='热度/关注数'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_date', 'source', 'stock_code', name='uk_stock_hot_rank_date_source_code'),
        comment='股票热榜快照表',
    )
    op.create_index(op.f('ix_business_stock_hot_rank_id'), 'business_stock_hot_rank', ['id'], unique=True)
    op.create_index('ix_business_stock_hot_rank_record_date', 'business_stock_hot_rank', ['record_date'], unique=False)
    op.create_index('ix_business_stock_hot_rank_source', 'business_stock_hot_rank', ['source'], unique=False)
    op.create_index('ix_business_stock_hot_rank_stock_code', 'business_stock_hot_rank', ['stock_code'], unique=False)

    op.create_table(
        'business_stock_hot_sync_log',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('source', sa.String(length=50), nullable=False, comment='榜单源 key'),
        sa.Column('status', sa.Boolean(), nullable=False, comment='采集状态'),
        sa.Column('fetched_count', sa.Integer(), nullable=False, comment='抓取条数'),
        sa.Column('saved_count', sa.Integer(), nullable=False, comment='入库条数'),
        sa.Column('error_msg', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='开始时间'),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True, comment='结束时间'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        comment='股票热榜采集日志表',
    )
    op.create_index(op.f('ix_business_stock_hot_sync_log_id'), 'business_stock_hot_sync_log', ['id'], unique=True)
    op.create_index('ix_business_stock_hot_sync_log_source', 'business_stock_hot_sync_log', ['source'], unique=False)

    # ================================================================
    # 2. 菜单重组：资讯一级目录 + 降级资讯聚合 + 新增股票热榜
    # ================================================================
    # 2a. 新增「资讯」一级目录
    op.bulk_insert(_MENU_TABLE, [
        {
            'id': _INFO_DIR_ID,
            'parent_id': None,
            'name': 'info',
            'path': '/info',
            'component': 'layout.base',
            'redirect': None,
            'permission': None,
            'meta_icon': 'mdi:newspaper-variant-multiple-outline',
            'meta_hidden': False,
            'meta_affix': False,
            'meta_breadcrumb': True,
            'status': True,
            'type': 'CATALOG',
            'sort': 6,
            'is_system': True,
            'meta_href': None,
            'meta_keep_alive': False,
            'deleted_at': None,
            'created_at': _DT,
            'updated_at': None,
        },
    ])

    # 2b. 降级资讯聚合菜单：挂在资讯目录下
    op.execute(
        f"UPDATE sys_menu SET "
        f"parent_id = {_INFO_DIR_ID}, "
        f"path = '/info/news', "
        f"name = 'info_news', "
        f"component = 'view.info_news', "
        f"sort = 1, "
        f"updated_at = '{_DT.isoformat(sep=' ')}' "
        f"WHERE id = {_NEWS_MENU_ID}"
    )

    # 2c. 新增「股票热榜」菜单 + 按钮权限
    op.bulk_insert(_MENU_TABLE, [
        # 股票热榜菜单（MENU）
        {
            'id': _STOCK_HOT_MENU_ID,
            'parent_id': _INFO_DIR_ID,
            'name': 'info_stock-hot',
            'path': '/info/stock-hot',
            'component': 'view.info_stock-hot',
            'redirect': None,
            'permission': 'sys:stock_hot:list',
            'meta_icon': 'mdi:trending-up',
            'meta_hidden': False,
            'meta_affix': False,
            'meta_breadcrumb': True,
            'status': True,
            'type': 'MENU',
            'sort': 2,
            'is_system': True,
            'meta_href': None,
            'meta_keep_alive': False,
            'deleted_at': None,
            'created_at': _DT,
            'updated_at': None,
        },
        # 查看列表权限（BUTTON）
        {
            'id': _STOCK_HOT_BTN_LIST_ID,
            'parent_id': _STOCK_HOT_MENU_ID,
            'name': 'stock-hot_list',
            'path': None,
            'component': None,
            'redirect': None,
            'permission': 'sys:stock_hot:list',
            'meta_icon': None,
            'meta_hidden': True,
            'meta_affix': False,
            'meta_breadcrumb': True,
            'status': True,
            'type': 'BUTTON',
            'sort': 1,
            'is_system': True,
            'meta_href': None,
            'meta_keep_alive': False,
            'deleted_at': None,
            'created_at': _DT,
            'updated_at': None,
        },
        # 查看详情权限（BUTTON）
        {
            'id': _STOCK_HOT_BTN_VIEW_ID,
            'parent_id': _STOCK_HOT_MENU_ID,
            'name': 'stock-hot_view',
            'path': None,
            'component': None,
            'redirect': None,
            'permission': 'sys:stock_hot:view',
            'meta_icon': None,
            'meta_hidden': True,
            'meta_affix': False,
            'meta_breadcrumb': True,
            'status': True,
            'type': 'BUTTON',
            'sort': 2,
            'is_system': True,
            'meta_href': None,
            'meta_keep_alive': False,
            'deleted_at': None,
            'created_at': _DT,
            'updated_at': None,
        },
        # 手动同步权限（BUTTON）
        {
            'id': _STOCK_HOT_BTN_SYNC_ID,
            'parent_id': _STOCK_HOT_MENU_ID,
            'name': 'stock-hot_sync',
            'path': None,
            'component': None,
            'redirect': None,
            'permission': 'sys:stock_hot:sync',
            'meta_icon': None,
            'meta_hidden': True,
            'meta_affix': False,
            'meta_breadcrumb': True,
            'status': True,
            'type': 'BUTTON',
            'sort': 3,
            'is_system': True,
            'meta_href': None,
            'meta_keep_alive': False,
            'deleted_at': None,
            'created_at': _DT,
            'updated_at': None,
        },
    ])


def downgrade() -> None:
    # 删除股票热榜菜单 + 按钮权限
    op.execute(
        f"DELETE FROM sys_menu WHERE id IN ("
        f"{_STOCK_HOT_BTN_LIST_ID}, {_STOCK_HOT_BTN_VIEW_ID}, "
        f"{_STOCK_HOT_BTN_SYNC_ID}, {_STOCK_HOT_MENU_ID})"
    )

    # 恢复资讯聚合为顶级菜单
    op.execute(
        f"UPDATE sys_menu SET "
        f"parent_id = NULL, "
        f"path = '/news', "
        f"name = 'news', "
        f"component = 'layout.base$view.news', "
        f"sort = 6, "
        f"updated_at = '{_DT.isoformat(sep=' ')}' "
        f"WHERE id = {_NEWS_MENU_ID}"
    )

    # 删除资讯一级目录
    op.execute(f"DELETE FROM sys_menu WHERE id = {_INFO_DIR_ID}")

    # 删除股票热榜表
    op.drop_index('ix_business_stock_hot_sync_log_source', table_name='business_stock_hot_sync_log')
    op.drop_index(op.f('ix_business_stock_hot_sync_log_id'), table_name='business_stock_hot_sync_log')
    op.drop_table('business_stock_hot_sync_log')

    op.drop_index('ix_business_stock_hot_rank_stock_code', table_name='business_stock_hot_rank')
    op.drop_index('ix_business_stock_hot_rank_source', table_name='business_stock_hot_rank')
    op.drop_index('ix_business_stock_hot_rank_record_date', table_name='business_stock_hot_rank')
    op.drop_index(op.f('ix_business_stock_hot_rank_id'), table_name='business_stock_hot_rank')
    op.drop_table('business_stock_hot_rank')
