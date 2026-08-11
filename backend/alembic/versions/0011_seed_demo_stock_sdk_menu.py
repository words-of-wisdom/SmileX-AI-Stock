"""
seed demo stock sdk menu

为「示例」目录新增「股票 SDK 演示」菜单（demo_stock-sdk），
对应后端 /admin/demo/akshare/* 与 /admin/demo/baostock/* 示例接口。
仅含 DML，可通过 downgrade 回滚。
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None

_DEMO_CATALOG_ID = 2907499345027072
_MENU_ID = 2942406616010001
_DT = datetime(2026, 8, 10, 18, 0, 0)

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

_ROWS = [
    {
        'id': _MENU_ID,
        'parent_id': _DEMO_CATALOG_ID,
        'name': 'demo_stock-sdk',
        'path': '/demo/stock-sdk',
        'component': 'view.demo_stock-sdk',
        'redirect': None,
        'permission': None,
        'meta_icon': 'mdi:finance',
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
]

_ROW_IDS = [row['id'] for row in _ROWS]


def upgrade() -> None:
    op.bulk_insert(_MENU_TABLE, _ROWS)


def downgrade() -> None:
    op.execute(
        f"DELETE FROM sys_menu WHERE id IN ({', '.join(str(i) for i in _ROW_IDS)})"
    )
