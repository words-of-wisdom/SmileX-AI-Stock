"""add research report module

Revision ID: 0027
Revises: 0026
Create Date: 2026-08-29

1. 新增 business_research_report 券商研报表（东财 stock_research_report_em，按 url 去重）
2. 幂等插入预置策略「研报掘金」（seq=12，基于券商研报评级/盈利预测对个股分析）
3. 在「AI助手」一级目录下新增「研报中心」子菜单(MENU) + 查询/同步按钮权限
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = '0027'
down_revision: Union[str, Sequence[str], None] = '0026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---- 菜单 ID（0026 用到 8028，从 8029 起）----
_AI_DIR_ID = 2942406616008001
_REPORT_MENU_ID = 2942406616008029
_REPORT_BTN_LIST_ID = 2942406616008030
_REPORT_BTN_SYNC_ID = 2942406616008031

_DT = datetime(2026, 8, 29, 12, 0, 0)

_PRESET_ID_BASE = 2942406616009100
_PRESET_SEQ = 12

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


_STRATEGY_TABLE = sa.table(
    'business_ai_strategy',
    sa.column('id', sa.BigInteger),
    sa.column('deleted_at', sa.DateTime),
    sa.column('created_at', sa.DateTime),
    sa.column('updated_at', sa.DateTime),
    sa.column('name', sa.String),
    sa.column('description', sa.String),
    sa.column('category', sa.String),
    sa.column('is_preset', sa.Boolean),
    sa.column('prompt_template', sa.Text),
    sa.column('stock_pool', sa.JSON),
    sa.column('execute_periods', sa.JSON),
    sa.column('max_positions', sa.Integer),
    sa.column('stop_loss_pct', sa.Numeric),
    sa.column('take_profit_pct', sa.Numeric),
    sa.column('status', sa.Boolean),
    sa.column('last_executed_at', sa.DateTime),
)

_RESEARCH_STRATEGY_PROMPT = (
    "选股与分析逻辑：\n"
    "1. 本策略基于券商研报观点选股：先用研报共识工具（get_report_consensus）与个股研报工具（get_research_reports）查询候选标的近 90 天研报\n"
    "2. 若指定了股票池：只分析池内个股（适合「对某个公司深入分析」——把股票池设为目标公司即可）；未指定池时，先用热榜/板块排行工具圈出近期热度或资金居前的 5~10 只候选，再逐一查其研报\n"
    "3. 优选标的特征：近 30 天研报数量明显增加（机构关注度升温）、评级以买入/增持为主且无下调、盈利预测（EPS/PE）逐年抬升、多机构观点一致\n"
    "4. 结合实时行情验证：研报看多但股价已短期大涨（涨幅超 15%）的回避追高；研报刚覆盖、股价尚在低位的优先\n"
    "5. 回避：近 90 天无研报覆盖的个股（机构盲区，无法验证逻辑）、评级出现下调或盈利预测下修的、研报数量多但评级分歧大的\n"
    "\n"
    "买卖纪律：\n"
    "- 买入逻辑=机构共识升温+基本面预测改善，属于中线逻辑，持股周期以周计\n"
    "- 目标：估值修复+盈利兑现（target_sell_price 按 +10%~+15% 设置）\n"
    "- 止损：研报逻辑证伪（后续出现评级下调/盈利下修/跌破买入平台）（stop_loss_price 按 -6% 设置）\n"
    "- 持仓评估重点：个股研报是否出现评级变化或预测下修，有则优先 sell\n"
    "- 信号宁缺毋滥：无研报支撑的标的一律不买"
)


def upgrade() -> None:
    # ================================================================
    # 1. 券商研报表
    # ================================================================
    op.create_table(
        'business_research_report',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.Column('stock_code', sa.String(length=10), nullable=False, comment='股票代码（6 位）'),
        sa.Column('published_date', sa.Date(), nullable=True, comment='研报发布日期'),
        sa.Column('title', sa.String(length=500), nullable=False, comment='研报标题'),
        sa.Column('url', sa.String(length=500), nullable=False, comment='研报 PDF 链接（去重键）'),
        sa.Column('stock_name', sa.String(length=50), nullable=True, comment='股票名称'),
        sa.Column('org_name', sa.String(length=100), nullable=True, comment='券商机构名称'),
        sa.Column('rating', sa.String(length=20), nullable=True, comment='评级（买入/增持/中性/减持等）'),
        sa.Column('industry', sa.String(length=50), nullable=True, comment='所属行业'),
        sa.Column('forecast', sa.JSON(), nullable=True, comment='盈利预测：{年份: {eps, pe}}'),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False, comment='抓取时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url', name='uk_research_report_url'),
        comment='券商研报表',
    )
    op.create_index(op.f('ix_business_research_report_id'), 'business_research_report', ['id'], unique=True)
    op.create_index('ix_research_report_code_date', 'business_research_report', ['stock_code', 'published_date'])

    # ================================================================
    # 2. 幂等插入预置策略「研报掘金」（默认停用）
    # ================================================================
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT id FROM business_ai_strategy "
            "WHERE deleted_at IS NULL AND name = '研报掘金' LIMIT 1"
        )
    ).first()
    if exists is None:
        conn.execute(
            _STRATEGY_TABLE.insert().values(
                id=_PRESET_ID_BASE + _PRESET_SEQ,
                deleted_at=None,
                created_at=_DT,
                updated_at=None,
                name='研报掘金',
                description=(
                    '基于券商研报选股：机构关注度升温 + 评级买入/增持占优 + 盈利预测逐年抬升的标的，'
                    '中线持有吃估值修复（股票池设为单只个股即「对某公司分析」）'
                ),
                category='general',
                is_preset=True,
                prompt_template=_RESEARCH_STRATEGY_PROMPT,
                stock_pool=None,
                execute_periods=['pre_market'],
                max_positions=4,
                stop_loss_pct=6.0,
                take_profit_pct=15.0,
                status=False,
                last_executed_at=None,
            )
        )

    # ================================================================
    # 3. 新增「研报中心」菜单 + 按钮权限
    # ================================================================
    _insert_menus([
        _menu_row(
            _REPORT_MENU_ID, _AI_DIR_ID,
            'ai_research-report', '/ai/research-report',
            'view.ai_research-report',
            'research:list',
            'mdi:file-chart-outline', 9,
        ),
        _btn_row(_REPORT_BTN_LIST_ID, _REPORT_MENU_ID, 'research-report_list', 'research:list', 1),
        _btn_row(_REPORT_BTN_SYNC_ID, _REPORT_MENU_ID, 'research-report_sync', 'research:sync', 2),
    ])


def downgrade() -> None:
    # 运行中的环境禁止 downgrade（会丢数据），仅保留结构定义
    _menu_ids = [_REPORT_BTN_LIST_ID, _REPORT_BTN_SYNC_ID, _REPORT_MENU_ID]
    op.execute(
        f"DELETE FROM sys_menu WHERE id IN ({', '.join(str(i) for i in _menu_ids)})"
    )
    op.execute(
        "DELETE FROM business_ai_strategy "
        f"WHERE id = {_PRESET_ID_BASE + _PRESET_SEQ} AND is_preset = TRUE"
    )
    op.drop_index('ix_research_report_code_date', table_name='business_research_report')
    op.drop_index(op.f('ix_business_research_report_id'), table_name='business_research_report')
    op.drop_table('business_research_report')
