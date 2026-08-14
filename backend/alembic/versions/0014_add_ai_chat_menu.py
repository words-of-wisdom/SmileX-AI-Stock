"""add AI Agent chat menu

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-13

在「AI助手」一级目录下新增「AI 对话」子菜单(MENU)
"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None

_AI_DIR_ID = 2942406616008001
_AI_CHAT_MENU_ID = 2942406616008007
_DT = datetime(2026, 8, 13, 10, 0, 0)

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
        'id': _AI_CHAT_MENU_ID,
        'parent_id': _AI_DIR_ID,
        'name': 'ai_chat',
        'path': '/ai/chat',
        'component': 'view.ai_chat',
        'redirect': None,
        'permission': None,
        'meta_icon': 'mdi:robot',
        'meta_hidden': False,
        'meta_affix': False,
        'meta_breadcrumb': True,
        'status': True,
        'type': 'MENU',
        'sort': 2,
        'is_system': True,
        'meta_href': None,
        'meta_keep_alive': True,
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
