"""add trailing stop (drawdown take-profit) support

Revision ID: 0025
Revises: 0024
Create Date: 2026-08-29

动态止盈（回撤止盈）：
1. business_ai_strategy 新增 trailing_drawdown_pct（策略级回撤止盈比例%，默认 5）
2. business_strategy_position 新增 trailing_drawdown_pct（建仓时快照）与 peak_price（持仓期间最高价）
3. 存量持仓回填：快照取策略当前值；peak_price 用 GREATEST(buy_price, latest_price) 初始化
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0025'
down_revision: Union[str, Sequence[str], None] = '0024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'business_ai_strategy',
        sa.Column('trailing_drawdown_pct', sa.Numeric(8, 4), nullable=True,
                  server_default='5.0',
                  comment='回撤止盈比例(%)：现价自持仓期间最高价回撤超该值且仍浮盈时止盈离场'),
    )
    op.add_column(
        'business_strategy_position',
        sa.Column('trailing_drawdown_pct', sa.Numeric(8, 4), nullable=True,
                  comment='建仓时快照的策略回撤止盈比例(%)，空则不启用'),
    )
    op.add_column(
        'business_strategy_position',
        sa.Column('peak_price', sa.Numeric(16, 4), nullable=True,
                  comment='持仓期间最高价（回撤止盈基准）'),
    )
    # 存量持仓回填：快照继承策略当前配置，峰值用已有价格最大值初始化
    op.execute(
        "UPDATE business_strategy_position p SET trailing_drawdown_pct = "
        "(SELECT s.trailing_drawdown_pct FROM business_ai_strategy s "
        " WHERE s.id = p.strategy_id) "
        "WHERE p.deleted_at IS NULL AND p.status = 'holding'"
    )
    op.execute(
        "UPDATE business_strategy_position SET peak_price = "
        "GREATEST(buy_price, COALESCE(latest_price, buy_price)) "
        "WHERE deleted_at IS NULL AND status = 'holding'"
    )


def downgrade() -> None:
    op.drop_column('business_strategy_position', 'peak_price')
    op.drop_column('business_strategy_position', 'trailing_drawdown_pct')
    op.drop_column('business_ai_strategy', 'trailing_drawdown_pct')
