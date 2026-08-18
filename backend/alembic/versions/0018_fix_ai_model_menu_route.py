"""fix ai model menu route fields to match frontend router

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-17

修正 0009 菜单种子遗留缺陷：LLM 配置菜单的路由字段
（manage_ai-model / /ai/ai-model / view.manage_ai-model）
与前端 elegant-router 实际生成的路由不匹配
（ai_model / /ai/model / view.ai_model，组件位于 views/ai/model/），
导致菜单不可见/点击 404。幂等 UPDATE 对齐。
"""
from typing import Sequence, Union

from alembic import op


revision: str = '0018'
down_revision: Union[str, Sequence[str], None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MENU_ID = 2942406616007001


def upgrade() -> None:
    op.execute(
        f"UPDATE sys_menu SET name = 'ai_model', path = '/ai/model', "
        f"component = 'view.ai_model', updated_at = now() "
        f"WHERE id = {_MENU_ID} AND deleted_at IS NULL "
        f"AND name = 'manage_ai-model'"
    )


def downgrade() -> None:
    # 无需回退：仅对齐前端路由事实，恢复旧值会使菜单不可用
    pass
