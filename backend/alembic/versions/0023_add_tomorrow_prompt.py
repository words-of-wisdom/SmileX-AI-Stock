"""add tomorrow prompt template to analysis config

Revision ID: 0023
Revises: 0022
Create Date: 2026-08-19

明日研判增加可配置提示词：business_analysis_config 新增 tomorrow_prompt_template 列
（include_tomorrow 开启时注入 user prompt，空则使用内置专业研判框架）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0023'
down_revision: Union[str, Sequence[str], None] = '0022'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'business_analysis_config',
        sa.Column('tomorrow_prompt_template', sa.Text(), nullable=True,
                  comment='明日研判定制提示词（方法论与侧重点，空则使用内置专业研判框架）'),
    )


def downgrade() -> None:
    op.drop_column('business_analysis_config', 'tomorrow_prompt_template')
