"""add market fund flow daily snapshot table

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-11

创建大盘资金流日快照表（主力/超大单/大单/中单/小单净流入），
数据源为东财大盘资金流（akshare stock_market_fund_flow）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0012'
down_revision: Union[str, Sequence[str], None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'business_market_fund_flow',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('record_date', sa.Date(), nullable=False, comment='快照日期（本地时区）'),
        sa.Column('main_net_inflow', sa.Numeric(precision=20, scale=2), nullable=True, comment='主力净流入(元)'),
        sa.Column('super_large_net_inflow', sa.Numeric(precision=20, scale=2), nullable=True, comment='超大单净流入(元)'),
        sa.Column('large_net_inflow', sa.Numeric(precision=20, scale=2), nullable=True, comment='大单净流入(元)'),
        sa.Column('medium_net_inflow', sa.Numeric(precision=20, scale=2), nullable=True, comment='中单净流入(元)'),
        sa.Column('small_net_inflow', sa.Numeric(precision=20, scale=2), nullable=True, comment='小单净流入(元)'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_date', name='uk_market_fund_flow_date'),
        comment='大盘资金流日快照表',
    )
    op.create_index(op.f('ix_business_market_fund_flow_id'), 'business_market_fund_flow', ['id'], unique=True)
    op.create_index('ix_business_market_fund_flow_record_date', 'business_market_fund_flow', ['record_date'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_business_market_fund_flow_record_date', table_name='business_market_fund_flow')
    op.drop_index(op.f('ix_business_market_fund_flow_id'), table_name='business_market_fund_flow')
    op.drop_table('business_market_fund_flow')
