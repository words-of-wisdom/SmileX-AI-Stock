"""seed news menu

Revision ID: 0005
Revises: e7ac2bb48021
Create Date: 2026-08-09

新增"资讯聚合"顶级菜单(MENU)，挂 base 布局，含 list/view/sync 三个按钮权限。
仅插菜单记录，不向 sys_role_menu_association 分配角色 ——
上线后由运维在角色管理页为目标角色勾选。

注意：菜单 name 与前端 elegant-router 路由名保持一致(news)，
否则前端按菜单 name 找不到组件与 i18n。
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = 'e7ac2bb48021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 资讯聚合顶级菜单 id
_NEWS_MENU_ID = 2942406616005001

_DT = datetime(2026, 8, 9, 16, 0, 0)

_NEWS_MENU_ROWS = [
    # 资讯聚合（MENU，顶级菜单）
    {
        'id': _NEWS_MENU_ID,
        'parent_id': None,
        'name': 'news',
        'path': '/news',
        'component': 'layout.base$view.news',
        'redirect': None,
        'permission': 'sys:news:list',
        'meta_icon': 'mdi:newspaper-variant',
        'meta_hidden': False,
        'meta_affix': False,
        'meta_breadcrumb': True,
        'status': True,
        'type': 'MENU',
        'sort': 6,
        'is_system': True,
        'meta_href': None,
        'meta_keep_alive': False,
        'deleted_at': None,
        'created_at': _DT,
        'updated_at': None,
    },
    # 查看列表权限（BUTTON）
    {
        'id': 2942406616005002,
        'parent_id': _NEWS_MENU_ID,
        'name': 'news_list',
        'path': None,
        'component': None,
        'redirect': None,
        'permission': 'sys:news:list',
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
        'id': 2942406616005003,
        'parent_id': _NEWS_MENU_ID,
        'name': 'news_view',
        'path': None,
        'component': None,
        'redirect': None,
        'permission': 'sys:news:view',
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
        'id': 2942406616005004,
        'parent_id': _NEWS_MENU_ID,
        'name': 'news_sync',
        'path': None,
        'component': None,
        'redirect': None,
        'permission': 'sys:news:sync',
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
]

_NEWS_MENU_IDS = [row['id'] for row in _NEWS_MENU_ROWS]


def upgrade() -> None:
    op.bulk_insert(
        sa.table(
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
        ),
        _NEWS_MENU_ROWS,
    )


def downgrade() -> None:
    op.execute(
        f"DELETE FROM sys_menu WHERE id IN ({', '.join(str(i) for i in _NEWS_MENU_IDS)})"
    )
