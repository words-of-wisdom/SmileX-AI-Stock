"""strategy async run and pending signals

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-18

1. business_strategy_run.status 由 Boolean 改为 String(20) 三态：
   running-执行中 / success-成功 / failed-失败。
   原 bool 无"执行中"语义，策略执行异步化后需要 running 态做并发守卫与前端轮询。
   存量数据：true -> 'success'，false -> 'failed'。
2. 新增 business_strategy_signal 待执行信号表：LLM 分析不再立即买卖，
   信号落表后由每分钟交易引擎（strategy.trade_engine）按实时价执行模拟买卖。
3. 下线旧任务 strategy.position_track（*/5 持仓跟踪）：
   职责已并入每分钟交易引擎，软删 sys_scheduled_task 行，
   重启后 sync_jobs_from_db 只加载未软删任务，不再调度。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0020'
down_revision: Union[str, Sequence[str], None] = '0019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 执行记录状态 Boolean -> String(20) 三态
    op.alter_column(
        'business_strategy_run', 'status',
        existing_type=sa.Boolean(), type_=sa.String(length=20),
        existing_nullable=False,
        postgresql_using="CASE WHEN status THEN 'success' ELSE 'failed' END",
        comment='执行状态：running-执行中，success-成功，failed-失败',
    )

    # 2. 待执行买卖信号表
    op.create_table(
        'business_strategy_signal',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.Column('strategy_id', sa.BigInteger(), nullable=False, comment='策略 ID'),
        sa.Column('strategy_name', sa.String(length=100), nullable=False, comment='策略名称（信号产生时快照）'),
        sa.Column('run_id', sa.BigInteger(), nullable=False, comment='来源执行记录 ID'),
        sa.Column('run_period', sa.String(length=20), nullable=False, comment='执行时段：pre_market/morning/noon/tail/post_close/manual'),
        sa.Column('run_date', sa.String(length=10), nullable=False, comment='信号产生日期 YYYY-MM-DD（过期判断用）'),
        sa.Column('stock_code', sa.String(length=20), nullable=False, comment='证券代码'),
        sa.Column('stock_name', sa.String(length=50), nullable=False, comment='证券简称'),
        sa.Column('action', sa.String(length=10), nullable=False, comment='信号动作：buy-买入，sell-卖出平仓，adjust-调整卖点/止损'),
        sa.Column('ref_buy_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='AI 参考买价'),
        sa.Column('target_sell_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='预估卖点（目标价）'),
        sa.Column('stop_loss_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='止损价'),
        sa.Column('reason', sa.String(length=500), nullable=True, comment='AI 给出的信号理由'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='信号状态：pending-待执行，executed-已执行，skipped-已跳过，failed-执行失败，expired-已过期'),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True, comment='执行时间'),
        sa.Column('executed_price', sa.Numeric(precision=16, scale=4), nullable=True, comment='实际成交价'),
        sa.Column('result_msg', sa.String(length=500), nullable=True, comment='执行结果说明（跳过/失败原因）'),
        sa.PrimaryKeyConstraint('id'),
        comment='策略待执行买卖信号表',
    )
    op.create_index(op.f('ix_business_strategy_signal_id'), 'business_strategy_signal', ['id'], unique=True)
    op.create_index('ix_strategy_signal_strategy_status', 'business_strategy_signal', ['strategy_id', 'status'], unique=False)
    op.create_index('ix_strategy_signal_run', 'business_strategy_signal', ['run_id'], unique=False)
    op.create_index('ix_strategy_signal_stock', 'business_strategy_signal', ['stock_code'], unique=False)
    op.create_index('ix_business_strategy_signal_status', 'business_strategy_signal', ['status'], unique=False)

    # 3. 下线旧持仓跟踪任务（职责并入每分钟交易引擎）
    op.execute(
        "UPDATE sys_scheduled_task SET deleted_at = now() "
        "WHERE task_key = 'strategy.position_track' AND deleted_at IS NULL"
    )


def downgrade() -> None:
    # 注意：生产运行中禁止 downgrade（见 aiDoc 约定），以下仅保证链路完整
    op.execute(
        "UPDATE sys_scheduled_task SET deleted_at = NULL "
        "WHERE task_key = 'strategy.position_track'"
    )
    op.drop_index('ix_business_strategy_signal_status', table_name='business_strategy_signal')
    op.drop_index('ix_strategy_signal_stock', table_name='business_strategy_signal')
    op.drop_index('ix_strategy_signal_run', table_name='business_strategy_signal')
    op.drop_index('ix_strategy_signal_strategy_status', table_name='business_strategy_signal')
    op.drop_index(op.f('ix_business_strategy_signal_id'), table_name='business_strategy_signal')
    op.drop_table('business_strategy_signal')
    op.alter_column(
        'business_strategy_run', 'status',
        existing_type=sa.String(length=20), type_=sa.Boolean(),
        existing_nullable=False,
        postgresql_using="status = 'success'",
        comment='执行状态：True-成功，False-失败',
    )
