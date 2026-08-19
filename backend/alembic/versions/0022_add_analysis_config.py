"""add analysis strategy config & tomorrow outlook

Revision ID: 0022
Revises: 0021
Create Date: 2026-08-19

1. 新增 business_analysis_run 配置表（大盘/板块分析策略，每类型一条）：
   prompt_template 策略定制提示词 + include_tomorrow 明日研判开关
2. 大盘/板块分析菜单下各新增「分析策略」按钮权限（analysis:strategy）
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = '0022'
down_revision: Union[str, Sequence[str], None] = '0021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 菜单 ID（0021 用到 8017，取 8018~8019）----
_MARKET_MENU_ID = 2942406616008012
_SECTOR_MENU_ID = 2942406616008013
_MARKET_BTN_STRATEGY_ID = 2942406616008018
_SECTOR_BTN_STRATEGY_ID = 2942406616008019

_DT = datetime(2026, 8, 19, 18, 0, 0)

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


def _btn_row(btn_id, parent_id, name, permission, sort):
    return {
        'id': btn_id,
        'parent_id': parent_id,
        'name': name,
        'path': None,
        'component': None,
        'redirect': None,
        'permission': permission,
        'meta_icon': None,
        'meta_hidden': True,
        'meta_affix': False,
        'meta_breadcrumb': True,
        'status': True,
        'type': 'BUTTON',
        'sort': sort,
        'is_system': True,
        'meta_href': None,
        'meta_keep_alive': False,
        'deleted_at': None,
        'created_at': _DT,
        'updated_at': None,
    }


def upgrade() -> None:
    # ================================================================
    # 1. AI 分析策略配置表（大盘/板块每类型一条）
    # ================================================================
    op.create_table(
        'business_analysis_config',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.Column('analysis_type', sa.String(length=20), nullable=False,
                  comment='分析类型：market-大盘分析，sector-板块分析（唯一）'),
        sa.Column('prompt_template', sa.Text(), nullable=True,
                  comment='分析策略定制提示词（关注面/风格/风控偏好等，空则使用默认策略）'),
        sa.Column('include_tomorrow', sa.Boolean(), nullable=False,
                  comment='是否包含明日研判章节'),
        sa.PrimaryKeyConstraint('id'),
        comment='AI 分析策略配置表',
    )
    op.create_index(op.f('ix_business_analysis_config_id'), 'business_analysis_config', ['id'], unique=True)
    op.create_index('ix_analysis_config_type', 'business_analysis_config', ['analysis_type'], unique=True)

    # ================================================================
    # 2. 「分析策略」按钮权限（挂在两个分析菜单下）
    # ================================================================
    op.bulk_insert(_MENU_TABLE, [
        _btn_row(_MARKET_BTN_STRATEGY_ID, _MARKET_MENU_ID,
                 'market-analysis_strategy', 'analysis:strategy', 3),
        _btn_row(_SECTOR_BTN_STRATEGY_ID, _SECTOR_MENU_ID,
                 'sector-analysis_strategy', 'analysis:strategy', 3),
    ])


def downgrade() -> None:
    op.execute(
        f"DELETE FROM sys_menu WHERE id IN ({_MARKET_BTN_STRATEGY_ID}, {_SECTOR_BTN_STRATEGY_ID})"
    )

    op.drop_index('ix_analysis_config_type', table_name='business_analysis_config')
    op.drop_index(op.f('ix_business_analysis_config_id'), table_name='business_analysis_config')
    op.drop_table('business_analysis_config')
