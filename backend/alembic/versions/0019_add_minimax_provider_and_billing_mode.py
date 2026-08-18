"""add minimax provider and billing mode

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-17

1. aiproviderenum 枚举新增 'minimax'（PG16 事务内 ADD VALUE 安全，
   仅要求同事务内不随后使用新值做 DDL）
2. sys_ai_model 新增 billing_mode（计费模式）：
   pay_as_you_go-按量计费 / coding_plan-Coding Plan 订阅
   同一供应商不同计费模式对应不同默认端点（如智谱
   /api/paas/v4 vs /api/coding/paas/v4，填错会误扣余额）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0019'
down_revision: Union[str, Sequence[str], None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE aiproviderenum ADD VALUE IF NOT EXISTS 'minimax'")
    op.add_column(
        'sys_ai_model',
        sa.Column('billing_mode', sa.String(length=20), nullable=False,
                  server_default='pay_as_you_go',
                  comment='计费模式：pay_as_you_go-按量计费，coding_plan-Coding Plan 订阅'),
    )


def downgrade() -> None:
    op.drop_column('sys_ai_model', 'billing_mode')
    # PG enum 不支持移除成员，minimax 保留（无害）
