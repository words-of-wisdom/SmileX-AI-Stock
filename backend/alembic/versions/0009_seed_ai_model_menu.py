from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None

_AI_DIR_ID = 2942406616008001
_AI_MODEL_MENU_ID = 2942406616008002
_DT = datetime(2026, 8, 10, 14, 0, 0)

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
        'id': _AI_DIR_ID,
        'parent_id': None,
        'name': 'ai',
        'path': '/ai',
        'component': 'layout.base',
        'redirect': None,
        'permission': None,
        'meta_icon': 'mdi:robot-outline',
        'meta_hidden': False,
        'meta_affix': False,
        'meta_breadcrumb': True,
        'status': True,
        'type': 'CATALOG',
        'sort': 7,
        'is_system': True,
        'meta_href': None,
        'meta_keep_alive': False,
        'deleted_at': None,
        'created_at': _DT,
        'updated_at': None,
    },
    {
        'id': _AI_MODEL_MENU_ID,
        'parent_id': _AI_DIR_ID,
        'name': 'ai_model',
        'path': '/ai/model',
        'component': 'view.ai_model',
        'redirect': None,
        'permission': 'sys:ai_model:list',
        'meta_icon': 'mdi:brain',
        'meta_hidden': False,
        'meta_affix': False,
        'meta_breadcrumb': True,
        'status': True,
        'type': 'MENU',
        'sort': 1,
        'is_system': True,
        'meta_href': None,
        'meta_keep_alive': False,
        'deleted_at': None,
        'created_at': _DT,
        'updated_at': None,
    },
    {
        'id': 2942406616008003,
        'parent_id': _AI_MODEL_MENU_ID,
        'name': 'ai_model_list',
        'path': None,
        'component': None,
        'redirect': None,
        'permission': 'sys:ai_model:list',
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
    {
        'id': 2942406616008004,
        'parent_id': _AI_MODEL_MENU_ID,
        'name': 'ai_model_add',
        'path': None,
        'component': None,
        'redirect': None,
        'permission': 'sys:ai_model:add',
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
    {
        'id': 2942406616008005,
        'parent_id': _AI_MODEL_MENU_ID,
        'name': 'ai_model_edit',
        'path': None,
        'component': None,
        'redirect': None,
        'permission': 'sys:ai_model:edit',
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
    {
        'id': 2942406616008006,
        'parent_id': _AI_MODEL_MENU_ID,
        'name': 'ai_model_delete',
        'path': None,
        'component': None,
        'redirect': None,
        'permission': 'sys:ai_model:delete',
        'meta_icon': None,
        'meta_hidden': True,
        'meta_affix': False,
        'meta_breadcrumb': True,
        'status': True,
        'type': 'BUTTON',
        'sort': 4,
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
