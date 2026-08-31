"""add board leading stocks top3

Revision ID: 0028
Revises: 0027
Create Date: 2026-08-31

行业/概念板块领涨股前三名：
business_board_daily 新增 leading_stocks（JSON），
存储 [{code, name, change_pct}] 按板块内涨幅降序，东财源抓取层补齐股票代码。
旧三字段（leading_stock_code/name/change_pct）保留并由 top1 回填，供历史数据与旧消费方使用。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0028'
down_revision: Union[str, Sequence[str], None] = '0027'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'business_board_daily',
        sa.Column('leading_stocks', sa.JSON(), nullable=True,
                  comment='领涨股前三名 [{code, name, change_pct}]，抓取层按板块内涨幅排序'),
    )


def downgrade() -> None:
    op.drop_column('business_board_daily', 'leading_stocks')
