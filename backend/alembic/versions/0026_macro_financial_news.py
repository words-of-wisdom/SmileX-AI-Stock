"""add macro indicator / financial report / news analysis modules

Revision ID: 0026
Revises: 0025
Create Date: 2026-08-29

1. 新增 business_macro_indicator 宏观经济指标表（中美 CPI/PPI/M1/M2 等历史序列）
2. 新增 business_financial_report 企业财报关键指标表 + business_financial_interpretation AI 财报解读执行记录表
3. 在「AI助手」一级目录下新增「每日资讯分析」「财报分析」「宏观指数」子菜单(MENU) + 按钮权限
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = '0026'
down_revision: Union[str, Sequence[str], None] = '0025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 菜单 ID（0021 用到 8017，从 8018 起）----
_AI_DIR_ID = 2942406616008001
_NEWS_MENU_ID = 2942406616008020
_FIN_MENU_ID = 2942406616008021
_MACRO_MENU_ID = 2942406616008022
_NEWS_BTN_LIST_ID = 2942406616008023
_NEWS_BTN_RUN_ID = 2942406616008024
_FIN_BTN_LIST_ID = 2942406616008025
_FIN_BTN_RUN_ID = 2942406616008026
_MACRO_BTN_LIST_ID = 2942406616008027
_MACRO_BTN_SYNC_ID = 2942406616008028

_DT = datetime(2026, 8, 29, 12, 0, 0)

_MENU_COLUMNS = (
    'id', 'parent_id', 'name', 'path', 'component', 'redirect', 'permission',
    'meta_icon', 'meta_hidden', 'meta_affix', 'meta_breadcrumb', 'status',
    'type', 'sort', 'is_system', 'meta_href', 'meta_keep_alive',
    'deleted_at', 'created_at', 'updated_at',
)


def _menu_row(menu_id, parent_id, name, path, component, permission, icon, sort):
    return (
        menu_id, parent_id, name, path, component, None, permission,
        icon, False, False, True, True, 'MENU', sort, True, None, False,
        None, _DT, None,
    )


def _btn_row(btn_id, parent_id, name, permission, sort):
    return (
        btn_id, parent_id, name, None, None, None, permission,
        None, True, False, True, True, 'BUTTON', sort, True, None, False,
        None, _DT, None,
    )


def _insert_menus(rows):
    # 注意：bulk_insert 在首行存在键编译列丢值问题，这里逐行 insert
    bind = op.get_bind()
    for row in rows:
        bind.execute(
            sa.text(
                "INSERT INTO sys_menu ({cols}) VALUES ({vals})".format(
                    cols=', '.join(_MENU_COLUMNS),
                    vals=', '.join(f':{c}' for c in _MENU_COLUMNS),
                )
            ),
            dict(zip(_MENU_COLUMNS, row)),
        )


def upgrade() -> None:
    # ================================================================
    # 1. 宏观经济指标表
    # ================================================================
    op.create_table(
        'business_macro_indicator',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.Column('country', sa.String(length=10), nullable=False, comment='国家/地区：CN-中国，US-美国'),
        sa.Column('indicator_code', sa.String(length=20), nullable=False, comment='指标代码：cpi/ppi/m1/m2/core_cpi 等'),
        sa.Column('indicator_name', sa.String(length=50), nullable=False, comment='指标中文名'),
        sa.Column('period', sa.String(length=20), nullable=False, comment='数据期次 YYYY-MM（月度指标）'),
        sa.Column('value', sa.Numeric(20, 4), nullable=True, comment='指标值（单位见 unit 字段）'),
        sa.Column('yoy', sa.Numeric(10, 4), nullable=True, comment='同比增速(%)'),
        sa.Column('mom', sa.Numeric(10, 4), nullable=True, comment='环比增速(%)'),
        sa.Column('unit', sa.String(length=20), nullable=False, server_default='%', comment='单位'),
        sa.Column('source', sa.String(length=50), nullable=True, comment='数据来源（akshare 接口名）'),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True, comment='数据发布时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('country', 'indicator_code', 'period', name='uk_macro_country_code_period'),
        comment='宏观经济指标表',
    )
    op.create_index(op.f('ix_business_macro_indicator_id'), 'business_macro_indicator', ['id'], unique=True)
    op.create_index('ix_macro_country_code_period', 'business_macro_indicator', ['country', 'indicator_code', 'period'])

    # ================================================================
    # 2. 企业财报表 + AI 财报解读执行记录表
    # ================================================================
    op.create_table(
        'business_financial_report',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.Column('stock_code', sa.String(length=10), nullable=False, comment='股票代码（6 位）'),
        sa.Column('stock_name', sa.String(length=50), nullable=True, comment='股票名称'),
        sa.Column('report_period', sa.String(length=10), nullable=False, comment='报告期 YYYY-MM-DD'),
        sa.Column('metrics', sa.JSON(), nullable=True, comment='财报关键指标（列名→值）'),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False, comment='抓取时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stock_code', 'report_period', name='uk_fin_report_code_period'),
        comment='企业财报关键指标表',
    )
    op.create_index(op.f('ix_business_financial_report_id'), 'business_financial_report', ['id'], unique=True)
    op.create_index('ix_fin_report_code', 'business_financial_report', ['stock_code'])

    op.create_table(
        'business_financial_interpretation',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.Column('stock_code', sa.String(length=10), nullable=False, comment='股票代码（6 位）'),
        sa.Column('stock_name', sa.String(length=50), nullable=True, comment='股票名称'),
        sa.Column('report_period', sa.String(length=10), nullable=True, comment='解读所基于的报告期 YYYY-MM-DD'),
        sa.Column('run_date', sa.String(length=10), nullable=False, comment='执行日期 YYYY-MM-DD'),
        sa.Column('trigger_type', sa.String(length=20), nullable=False, comment='触发方式：schedule-定时，manual-手动'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='执行状态：running/success/failed'),
        sa.Column('ai_raw_response', sa.Text(), nullable=True, comment='AI 财报解读报告原文（markdown）'),
        sa.Column('parsed_result', sa.JSON(), nullable=True, comment='结构化摘要：{quality_rating, highlights, risks, forecast}'),
        sa.Column('error_msg', sa.Text(), nullable=True, comment='错误信息'),
        sa.PrimaryKeyConstraint('id'),
        comment='AI 财报解读执行记录表',
    )
    op.create_index(op.f('ix_business_financial_interpretation_id'), 'business_financial_interpretation', ['id'], unique=True)
    op.create_index('ix_fin_interp_code_created', 'business_financial_interpretation', ['stock_code', 'created_at'])

    # ================================================================
    # 3. 新增「每日资讯分析」「财报分析」「宏观指数」菜单 + 按钮权限
    #    注意：name 必须与前端 elegant-router 生成的路由 name 完全一致
    # ================================================================
    _insert_menus([
        _menu_row(
            _NEWS_MENU_ID, _AI_DIR_ID,
            'ai_news-analysis', '/ai/news-analysis',
            'view.ai_news-analysis',
            'analysis:list',
            'mdi:newspaper-variant-multiple-outline', 6,
        ),
        _menu_row(
            _FIN_MENU_ID, _AI_DIR_ID,
            'ai_financial-analysis', '/ai/financial-analysis',
            'view.ai_financial-analysis',
            'financial:list',
            'mdi:file-document-edit-outline', 7,
        ),
        _menu_row(
            _MACRO_MENU_ID, _AI_DIR_ID,
            'ai_macro', '/ai/macro',
            'view.ai_macro',
            'macro:list',
            'mdi:finance', 8,
        ),
        _btn_row(_NEWS_BTN_LIST_ID, _NEWS_MENU_ID, 'news-analysis_list', 'analysis:list', 1),
        _btn_row(_NEWS_BTN_RUN_ID, _NEWS_MENU_ID, 'news-analysis_run', 'analysis:run', 2),
        _btn_row(_FIN_BTN_LIST_ID, _FIN_MENU_ID, 'financial-analysis_list', 'financial:list', 1),
        _btn_row(_FIN_BTN_RUN_ID, _FIN_MENU_ID, 'financial-analysis_run', 'financial:run', 2),
        _btn_row(_MACRO_BTN_LIST_ID, _MACRO_MENU_ID, 'macro_list', 'macro:list', 1),
        _btn_row(_MACRO_BTN_SYNC_ID, _MACRO_MENU_ID, 'macro_sync', 'macro:sync', 2),
    ])


def downgrade() -> None:
    _menu_ids = [
        _NEWS_BTN_LIST_ID, _NEWS_BTN_RUN_ID,
        _FIN_BTN_LIST_ID, _FIN_BTN_RUN_ID,
        _MACRO_BTN_LIST_ID, _MACRO_BTN_SYNC_ID, _NEWS_MENU_ID, _FIN_MENU_ID, _MACRO_MENU_ID,
    ]
    op.execute(
        f"DELETE FROM sys_menu WHERE id IN ({', '.join(str(i) for i in _menu_ids)})"
    )

    op.drop_index('ix_fin_interp_code_created', table_name='business_financial_interpretation')
    op.drop_index(op.f('ix_business_financial_interpretation_id'), table_name='business_financial_interpretation')
    op.drop_table('business_financial_interpretation')
    op.drop_index('ix_fin_report_code', table_name='business_financial_report')
    op.drop_index(op.f('ix_business_financial_report_id'), table_name='business_financial_report')
    op.drop_table('business_financial_report')
    op.drop_index('ix_macro_country_code_period', table_name='business_macro_indicator')
    op.drop_index(op.f('ix_business_macro_indicator_id'), table_name='business_macro_indicator')
    op.drop_table('business_macro_indicator')
