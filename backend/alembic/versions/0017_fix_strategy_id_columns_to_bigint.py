"""fix strategy id reference columns to bigint

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-17

修复 0015 遗留缺陷：策略相关表的 id 引用列（strategy_id/position_id）
误建为 Integer(int32)，雪花主键 id 为 64 位量级，参数绑定即溢出
（asyncpg: value out of int32 range），导致策略执行必然失败。
统一改为 BigInteger，int4 -> int8 为隐式安全转换。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0017'
down_revision: Union[str, Sequence[str], None] = '0016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'business_strategy_run', 'strategy_id',
        existing_type=sa.Integer(), type_=sa.BigInteger(),
        existing_nullable=False,
        comment='策略 ID',
    )
    op.alter_column(
        'business_strategy_position', 'strategy_id',
        existing_type=sa.Integer(), type_=sa.BigInteger(),
        existing_nullable=False,
        comment='策略 ID',
    )
    op.alter_column(
        'business_position_track_log', 'position_id',
        existing_type=sa.Integer(), type_=sa.BigInteger(),
        existing_nullable=False,
        comment='持仓 ID',
    )


def downgrade() -> None:
    op.alter_column(
        'business_position_track_log', 'position_id',
        existing_type=sa.BigInteger(), type_=sa.Integer(),
        existing_nullable=False,
        comment='持仓 ID',
    )
    op.alter_column(
        'business_strategy_position', 'strategy_id',
        existing_type=sa.BigInteger(), type_=sa.Integer(),
        existing_nullable=False,
        comment='策略 ID',
    )
    op.alter_column(
        'business_strategy_run', 'strategy_id',
        existing_type=sa.BigInteger(), type_=sa.Integer(),
        existing_nullable=False,
        comment='策略 ID',
    )
