"""add session dimension to analysis run/config

Revision ID: 0024
Revises: 0023
Create Date: 2026-08-21

大盘/板块分析增加时段维度（close-收盘分析，morning-早盘分析 9:20）：
1. business_analysis_run / business_analysis_config 新增 session 列（存量数据归为 close）
2. config 唯一索引由 analysis_type 改为 (analysis_type, session)
3. run 索引 ix_analysis_run_type_date 扩展为 (analysis_type, run_date, session)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0024'
down_revision: Union[str, Sequence[str], None] = '0023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'business_analysis_run',
        sa.Column('session', sa.String(length=20), nullable=False,
                  server_default='close',
                  comment='分析时段：close-收盘分析（16:05），morning-早盘分析（9:20）'),
    )
    op.add_column(
        'business_analysis_config',
        sa.Column('session', sa.String(length=20), nullable=False,
                  server_default='close',
                  comment='分析时段：close-收盘分析，morning-早盘分析'),
    )

    # config 唯一索引：analysis_type -> (analysis_type, session)
    op.drop_index('ix_analysis_config_type', table_name='business_analysis_config')
    op.create_index(
        'ix_analysis_config_type_session', 'business_analysis_config',
        ['analysis_type', 'session'], unique=True,
    )

    # run 同日去重索引扩展（定时任务按 类型+日期+时段 去重）
    op.drop_index('ix_analysis_run_type_date', table_name='business_analysis_run')
    op.create_index(
        'ix_analysis_run_type_date', 'business_analysis_run',
        ['analysis_type', 'run_date', 'session'],
    )


def downgrade() -> None:
    # 回滚前需保证每个 analysis_type 只剩一条 session（否则唯一索引创建失败）
    op.drop_index('ix_analysis_run_type_date', table_name='business_analysis_run')
    op.create_index(
        'ix_analysis_run_type_date', 'business_analysis_run',
        ['analysis_type', 'run_date'],
    )
    op.drop_index('ix_analysis_config_type_session', table_name='business_analysis_config')
    op.create_index(
        'ix_analysis_config_type', 'business_analysis_config',
        ['analysis_type'], unique=True,
    )
    op.drop_column('business_analysis_config', 'session')
    op.drop_column('business_analysis_run', 'session')
