"""add market & sector AI analysis module

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-19

1. 新增 business_analysis_run AI 分析执行记录表
   （大盘/板块分析共用，submit_run 落库即返、后台 LLM 生成，三态 status）
2. 在「AI助手」一级目录下新增「大盘分析」「板块分析」子菜单(MENU) + 生成按钮权限
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = '0021'
down_revision: Union[str, Sequence[str], None] = '0020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 菜单 ID（AI 助手目录 8001，0015 用到 8011，取 8012~8017）----
_AI_DIR_ID = 2942406616008001
_MARKET_MENU_ID = 2942406616008012
_SECTOR_MENU_ID = 2942406616008013
_MARKET_BTN_LIST_ID = 2942406616008014
_MARKET_BTN_RUN_ID = 2942406616008015
_SECTOR_BTN_LIST_ID = 2942406616008016
_SECTOR_BTN_RUN_ID = 2942406616008017

_DT = datetime(2026, 8, 19, 12, 0, 0)

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


def _menu_row(menu_id, parent_id, name, path, component, permission, icon, menu_type, sort):
    return {
        'id': menu_id,
        'parent_id': parent_id,
        'name': name,
        'path': path,
        'component': component,
        'redirect': None,
        'permission': permission,
        'meta_icon': icon,
        'meta_hidden': False,
        'meta_affix': False,
        'meta_breadcrumb': True,
        'status': True,
        'type': menu_type,
        'sort': sort,
        'is_system': True,
        'meta_href': None,
        'meta_keep_alive': False,
        'deleted_at': None,
        'created_at': _DT,
        'updated_at': None,
    }


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


_BASE_COLUMNS = [
    sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
]


def _base_pk():
    return sa.PrimaryKeyConstraint('id')


def upgrade() -> None:
    # ================================================================
    # 1. AI 分析执行记录表
    # ================================================================
    op.create_table(
        'business_analysis_run',
        *_BASE_COLUMNS,
        sa.Column('analysis_type', sa.String(length=20), nullable=False,
                  comment='分析类型：market-大盘分析，sector-板块分析'),
        sa.Column('run_date', sa.String(length=10), nullable=False,
                  comment='执行日期 YYYY-MM-DD（定时任务同日去重用）'),
        sa.Column('trigger_type', sa.String(length=20), nullable=False,
                  comment='触发方式：schedule-定时，manual-手动'),
        sa.Column('status', sa.String(length=20), nullable=False,
                  comment='执行状态：running-执行中，success-成功，failed-失败'),
        sa.Column('ai_raw_response', sa.Text(), nullable=True, comment='AI 分析报告原文（markdown）'),
        sa.Column('parsed_result', sa.JSON(), nullable=True,
                  comment='结构化摘要：大盘{sentiment,score,summary,key_points}；板块{hot_boards,rotation_summary,key_points}'),
        sa.Column('error_msg', sa.Text(), nullable=True, comment='错误信息'),
        _base_pk(),
        comment='AI 分析执行记录表',
    )
    op.create_index(op.f('ix_business_analysis_run_id'), 'business_analysis_run', ['id'], unique=True)
    op.create_index('ix_analysis_run_type_created', 'business_analysis_run', ['analysis_type', 'created_at'], unique=False)
    op.create_index('ix_analysis_run_type_date', 'business_analysis_run', ['analysis_type', 'run_date'], unique=False)

    # ================================================================
    # 2. 新增「大盘分析」「板块分析」菜单 + 生成按钮权限（挂在 AI 助手目录下）
    #    注意：name 必须与前端 elegant-router 生成的路由 name 完全一致
    # ================================================================
    op.bulk_insert(_MENU_TABLE, [
        _menu_row(
            _MARKET_MENU_ID, _AI_DIR_ID,
            'ai_market-analysis', '/ai/market-analysis',
            'view.ai_market-analysis',
            'analysis:market:list',
            'mdi:chart-areaspline', 'MENU', 4,
        ),
        _menu_row(
            _SECTOR_MENU_ID, _AI_DIR_ID,
            'ai_sector-analysis', '/ai/sector-analysis',
            'view.ai_sector-analysis',
            'analysis:sector:list',
            'mdi:view-grid-outline', 'MENU', 5,
        ),
        _btn_row(_MARKET_BTN_LIST_ID, _MARKET_MENU_ID,
                 'market-analysis_list', 'analysis:list', 1),
        _btn_row(_MARKET_BTN_RUN_ID, _MARKET_MENU_ID,
                 'market-analysis_run', 'analysis:run', 2),
        _btn_row(_SECTOR_BTN_LIST_ID, _SECTOR_MENU_ID,
                 'sector-analysis_list', 'analysis:list', 1),
        _btn_row(_SECTOR_BTN_RUN_ID, _SECTOR_MENU_ID,
                 'sector-analysis_run', 'analysis:run', 2),
    ])


def downgrade() -> None:
    # 删除菜单 + 权限
    _menu_ids = [
        _MARKET_BTN_LIST_ID, _MARKET_BTN_RUN_ID,
        _SECTOR_BTN_LIST_ID, _SECTOR_BTN_RUN_ID,
        _MARKET_MENU_ID, _SECTOR_MENU_ID,
    ]
    op.execute(
        f"DELETE FROM sys_menu WHERE id IN ({', '.join(str(i) for i in _menu_ids)})"
    )

    op.drop_index('ix_analysis_run_type_date', table_name='business_analysis_run')
    op.drop_index('ix_analysis_run_type_created', table_name='business_analysis_run')
    op.drop_index(op.f('ix_business_analysis_run_id'), table_name='business_analysis_run')
    op.drop_table('business_analysis_run')
