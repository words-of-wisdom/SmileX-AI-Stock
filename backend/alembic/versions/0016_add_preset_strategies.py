"""add preset strategies and index constituent table

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-17

1. business_ai_strategy 新增 category（策略分类）/ is_preset（预置标记）字段
2. 幂等插入 10 条系统预置策略（默认停用，覆盖早盘竞价/午盘/尾盘/蓝筹白马/综合）
3. 新建指数成分股快照表 business_index_constituent（BaoStock 沪深300/中证500）
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = '0016'
down_revision: Union[str, Sequence[str], None] = '0015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DT = datetime(2026, 8, 17, 12, 0, 0)

# 预置策略固定 ID 段（便于识别与幂等）
_PRESET_ID_BASE = 2942406616009100

# 蓝筹白马 —— 沪深300 核心资产池（30 只）
_CORE_ASSET_POOL = [
    "600519", "000858", "000568", "600809", "000333", "000651", "600690",
    "601318", "600036", "601166", "600030", "300059", "601899", "601088",
    "600900", "600309", "600276", "300750", "002594", "600887", "601888",
    "002415", "600028", "601857", "601390", "601668", "000002", "600000",
    "601669", "600585",
]

# 蓝筹白马 —— 高股息红利池（20 只）
_DIVIDEND_POOL = [
    "601398", "601939", "601288", "601988", "600036", "601318", "601088",
    "601898", "600900", "600886", "600023", "600011", "600941", "601728",
    "601006", "600019", "601111", "600028", "601857", "000895",
]

# ----------------------------------------------------------------------
# 10 条预置策略定义
# ----------------------------------------------------------------------
_PRESET_STRATEGIES = [
    {
        "seq": 1,
        "name": "竞价高开抢筹",
        "description": "集合竞价阶段捕捉高开 2%~5%、竞价量明显放大的强势股，博弈开盘后惯性冲高",
        "category": "pre_market_auction",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 通过热榜与涨停池工具了解昨日市场主线题材，判断题材是否仍有发酵空间\n"
            "2. 聚焦今日集合竞价高开 2%~5% 的强势股（高开过低动能不足，高开超过 7% 接近一字板买入风险大，均回避）\n"
            "3. 优选：所属板块昨日涨幅榜前列 + 今日板块内多股同步高开（板块效应）；个股昨日放量上涨或涨停但未一字、今日竞价继续高开（加速确认）\n"
            "4. 回避：昨日一字涨停今日大幅高开（获利盘抛压）、ST/*ST、停牌复牌无题材股、纯消息高开无板块配合的独苗股\n"
            "\n"
            "买卖纪律：\n"
            "- 买入参考竞价价格，单日最多新建 2~3 只\n"
            "- 高开超过 6% 一律不追（隔夜跳空止损滑点大，历史亏损多来自高位接力）\n"
            "- 竞价须放量（量比>2）但非巨量高开出逃形态，量价背离直接放弃\n"
            "- 目标：开盘后惯性冲高获利，当日或次日冲高即卖（target_sell_price 按 +3%~+4% 设置，冲高果断兑现）\n"
            "- 止损：开盘后走势不及预期、跌破竞价低点或分时均价线即离场（stop_loss_price 按 -3% 设置）"
        ),
        "stock_pool": None,
        "execute_periods": ["pre_market"],
        "max_positions": 3,
        "stop_loss_pct": 3.0,
        "take_profit_pct": 4.0,
    },
    {
        "seq": 2,
        "name": "竞价超跌低吸",
        "description": "上升趋势个股因恐慌情绪竞价大幅低开（-3%~-6%）时低吸，博弈当日超跌反弹",
        "category": "pre_market_auction",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 前提：大盘指数趋势未走坏（用指数行情与资金流工具确认），系统性风险时不出手\n"
            "2. 寻找中期上升趋势中（近期热榜出现过、人气未散）因短期利空或恐慌情绪今日集合竞价低开 -3%~-6% 的个股\n"
            "3. 优选：低开但竞价量能温和（非恐慌性放量出逃）、利空不伤及主营业务逻辑、昨日收盘仍处于上升趋势\n"
            "4. 回避：连续跌停后继续低开（下跌中继）、重大违规/退市风险个股、低开超过 -7%（趋势可能破位）\n"
            "\n"
            "买卖纪律：\n"
            "- 低开买入博当日修复反弹，买点参考竞价价格\n"
            "- 目标：反弹至昨日收盘价附近或上方（target_sell_price 按 +5%~+8% 设置）\n"
            "- 止损：盘面确认破位（继续下探不回头）坚决止损（stop_loss_price 按 -4% 设置），不与趋势作对"
        ),
        "stock_pool": None,
        "execute_periods": ["pre_market"],
        "max_positions": 3,
        "stop_loss_pct": 4.0,
        "take_profit_pct": 8.0,
    },
    {
        "seq": 3,
        "name": "午盘强势回踩低吸",
        "description": "午后强势板块内个股缩量回踩分时均价线企稳时低吸，跟随强势资金博尾盘再度走强",
        "category": "noon",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 通过板块排行工具确认上午涨幅居前的强势板块（行业/概念），锁定当日主线\n"
            "2. 在强势板块内找上午保持红盘上涨、午后缩量回踩的个股：回踩不破分时均价线、量能萎缩（抛压轻）为佳\n"
            "3. 优选：上午板块涨幅榜前列 + 板块资金净流入为正 + 个股为板块内人气或权重标的\n"
            "4. 回避：上午已涨停午后开板的弱势回封股、放量下跌破均价线的真跌个股、ST 股\n"
            "\n"
            "买卖纪律：\n"
            "- 必须等回踩至分时均价线附近且企稳信号明确（止跌翻红/缩量止跌）后才给 buy，禁止在均价线上方高位直接追多\n"
            "- 当日涨幅已超 6% 的个股不买（尾盘冲高回落风险大）\n"
            "- 目标：尾盘板块再度走强带动冲高（target_sell_price 按 +3%~+5% 设置，达到即兑现不贪）\n"
            "- 止损：午后跌破均价线且板块整体转弱（stop_loss_price 按 -3% 设置）\n"
            "- 信号宁缺毋滥：无明确企稳形态时输出空数组"
        ),
        "stock_pool": None,
        "execute_periods": ["noon"],
        "max_positions": 5,
        "stop_loss_pct": 3.0,
        "take_profit_pct": 5.0,
    },
    {
        "seq": 4,
        "name": "午盘补涨轮动",
        "description": "上午主线板块高位时，捕捉同产业链低位补涨方向的轮动卡位机会",
        "category": "noon",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 判断上午主线板块位置：涨幅已高（前排集体大涨或涨停潮）时，寻找同产业链或关联度高的低位补涨方向\n"
            "2. 补涨方向特征：板块涨幅榜中位但资金净流入开始转正、板块内出现首只放量首板股、消息面有扩散催化（用新闻工具核实）\n"
            "3. 个股层面：低位（近期未大涨）、午后放量启动、突破近期整理平台\n"
            "4. 回避：纯蹭热点无基本面/消息支撑的方向、已连续补涨两天以上的滞涨板块\n"
            "\n"
            "买卖纪律：\n"
            "- 午后启动初期介入，不追已快速拉升超过 5% 的标的\n"
            "- 目标：补涨行情通常 1~3 天，吃到主升段即走（target_sell_price 按 +5%~+7% 设置）\n"
            "- 止损：轮动逻辑证伪（主线熄火+补涨方向无人跟进）即离场（stop_loss_price 按 -4% 设置）"
        ),
        "stock_pool": None,
        "execute_periods": ["noon"],
        "max_positions": 5,
        "stop_loss_pct": 4.0,
        "take_profit_pct": 7.0,
    },
    {
        "seq": 5,
        "name": "尾盘资金抢筹",
        "description": "14:30 后捕捉主力资金尾盘放量抢筹的个股，博弈次日惯性高开",
        "category": "tail",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 14:30 后扫描：板块资金净流入排行靠前的方向 + 涨幅榜中走势稳健的个股\n"
            "2. 尾盘抢筹特征：全天震荡上行、尾盘 30 分钟放量走强创日内新高（或逼近新高）、板块多股尾盘同步拉升\n"
            "3. 优选：当日有明确题材催化（新闻可查）、板块净流入持续到尾盘、个股非炸板回封的弱势股\n"
            "4. 回避：尾盘偷袭直线拉涨停（次日大概率低开兑现）、全天弱势仅尾盘异动的无量个股、连板高位的尾盘分歧股\n"
            "\n"
            "买卖纪律：\n"
            "- 尾盘 14:30~14:55 间确认强势后买入，博次日惯性高开\n"
            "- 只选全天涨幅 2%~5%、尾盘温和放量走强的标的；当日涨幅已超 6% 或尾盘直线拉升的一律不买（隔夜跳空止损滑点大，历史亏损集中于此）\n"
            "- 目标：次日高开冲高即兑现，不恋战（target_sell_price 按 +4%~+6% 设置）\n"
            "- 止损：次日低开低走不及预期立即离场（stop_loss_price 按 -3% 设置，开盘观察 10 分钟内确认走弱再执行）\n"
            "- 信号宁缺毋滥：尾盘无符合条件标的时输出空数组"
        ),
        "stock_pool": None,
        "execute_periods": ["tail"],
        "max_positions": 2,
        "stop_loss_pct": 3.0,
        "take_profit_pct": 6.0,
    },
    {
        "seq": 6,
        "name": "尾盘趋势确认",
        "description": "全天强势且尾盘仍站稳高位的多头趋势股，尾盘买入隔夜持有",
        "category": "tail",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 大盘环境：指数当日收阳概率大（尾盘指数走稳、大盘资金净流出收窄或转正），否则宁可空仓\n"
            "2. 个股全天强势确认：所属板块涨幅榜前列 + 个股全天红盘震荡上行 + 尾盘仍站稳日内高位区（回撤小于涨幅一半）\n"
            "3. 优选：板块与个股共振（板块净流入+个股放量）、处于上升趋势初中期、非高位放量滞涨\n"
            "4. 回避：尾盘跳水股、高位巨量换手股（分歧过大）、大盘尾盘明显走弱时的所有买入\n"
            "\n"
            "买卖纪律：\n"
            "- 尾盘买入隔夜持有，博次日趋势延续\n"
            "- 回避当日涨幅超 7%、已连续拉升 3 日以上的加速股（隔夜跳空风险大，历史止损全部来自此类高位接力）；优先当日涨幅 2%~6%、趋势初中期的温和强势股\n"
            "- 目标：趋势延续可持有 2~5 天，移动止盈（target_sell_price 初步按 +5%~+7% 设置，后续可 adjust 上移）\n"
            "- 止损：隔夜逻辑证伪（次日低开破位）坚决止损（stop_loss_price 按 -4% 设置）\n"
            "- 信号宁缺毋滥：大盘或个股形态不理想时输出空数组"
        ),
        "stock_pool": None,
        "execute_periods": ["tail"],
        "max_positions": 3,
        "stop_loss_pct": 4.0,
        "take_profit_pct": 7.0,
    },
    {
        "seq": 7,
        "name": "核心资产价值投资",
        "description": "沪深300核心资产池内低吸分批建仓，中线持有估值修复行情",
        "category": "blue_chip",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 只允许在给定股票池内选择（沪深300核心资产），严禁池外选股\n"
            "2. 优先选择：所属板块资金净流入转正或连续改善、大盘资金面回暖阶段的核心资产\n"
            "3. 结合热榜与新闻判断市场风格是否切向大盘蓝筹（热点缺失、防御情绪升温时核心资产相对受益）\n"
            "4. 估值意识：无法获取精确估值数据时，优先选择近期滞涨（相对板块涨幅落后）、回调充分（距离近期高点回撤较大）的池内标的，回避短期已大涨的\n"
            "\n"
            "买卖纪律：\n"
            "- 分批建仓思路：每次执行最多新建 2~3 只，持有周期以周计\n"
            "- 目标：中线估值修复行情（target_sell_price 按 +10%~+20% 设置）\n"
            "- 止损：宏观逻辑或个股基本面证伪时止损（stop_loss_price 按 -8% 设置，容忍正常波动）\n"
            "- 已持仓个股重点评估：趋势完好则 hold，逻辑变化则 sell，涨幅过大可 adjust 上移卖点"
        ),
        "stock_pool": {"codes": _CORE_ASSET_POOL},
        "execute_periods": ["tail", "post_close"],
        "max_positions": 8,
        "stop_loss_pct": 8.0,
        "take_profit_pct": 20.0,
    },
    {
        "seq": 8,
        "name": "高股息红利防御",
        "description": "银行/公用事业/能源/运营商高股息池防御配置，市场风险偏好下降时长持吃息",
        "category": "blue_chip",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 只允许在给定股票池内选择（高股息红利股），严禁池外选股\n"
            "2. 市场环境判断：风险偏好下降（题材退潮、涨停池缩量、大盘资金净流出）时红利资产配置价值上升；市场亢奋时可降低配置或 hold 现有持仓\n"
            "3. 个股选择：池内近期相对抗跌（回调小）、板块资金稳中有升的标的；银行/公用事业/能源/运营商分散配置\n"
            "4. 回避：池内近期异动大涨的（追高风险），红利策略以稳为主\n"
            "\n"
            "买卖纪律：\n"
            "- 防御型长持：买入后以吃息+慢牛为目标，不追求短期爆发\n"
            "- 目标：+8%~+15%（target_sell_price），达到后可 adjust 上移或卖出再平衡\n"
            "- 止损：-6%（stop_loss_price），红利股破位说明防御逻辑失效\n"
            "- 每次执行最多新建 2~3 只，逐步构建组合"
        ),
        "stock_pool": {"codes": _DIVIDEND_POOL},
        "execute_periods": ["post_close"],
        "max_positions": 8,
        "stop_loss_pct": 6.0,
        "take_profit_pct": 15.0,
    },
    {
        "seq": 9,
        "name": "涨停题材龙头打板",
        "description": "基于涨停池连板梯队与题材集中度，在情绪上升期参与 2~3 板主线龙头",
        "category": "general",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 用涨停股池工具分析当日连板梯队：最高板、2板/3板梯队完整性、题材集中度（同题材涨停家数）\n"
            "2. 只在情绪上升期参与：涨停家数多、连板梯队完整、炸板率低；情绪冰点（涨停稀少+炸板率高）时空仓等待\n"
            "3. 标的：主线题材中辨识度高的龙头（最先涨停/封单最大/连板最高），优选 2~3 板位置的主升龙头\n"
            "4. 回避：独苗股（题材内仅一只涨停无跟随）、高位断板反核（风险极大）、尾盘偷袭板、ST 股\n"
            "\n"
            "买卖纪律：\n"
            "- 严格止损是本策略生命线：买入后不涨停或破分时均价线即考虑离场\n"
            "- 目标：连板晋级或龙头溢价（target_sell_price 按 +10% 设置）\n"
            "- 止损：-5%（stop_loss_price），绝不补仓不摊薄\n"
            "- 最多同时持有 3 只，情绪退潮期主动 sell 降仓"
        ),
        "stock_pool": None,
        "execute_periods": ["morning", "noon", "tail"],
        "max_positions": 3,
        "stop_loss_pct": 5.0,
        "take_profit_pct": 10.0,
    },
    {
        "seq": 10,
        "name": "大盘共振波段",
        "description": "先判大盘多空（指数趋势+资金流），多头时选与指数共振的板块龙头顺势波段",
        "category": "general",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 第一步必须先判断大盘多空：用指数行情 + 指数历史K线（get_index_history 看上证/沪深300趋势）+ 大盘资金流（连续净流入/流出）综合判断\n"
            "2. 大盘多头（趋势向上+资金净流入）：选与指数共振的板块龙头——板块涨幅榜与净流入榜双前列板块中的强势股\n"
            "3. 大盘空头（趋势走弱+资金持续净流出）：不出新仓，重点评估持仓 sell/减仓；震荡市轻仓试错\n"
            "4. 个股优选：板块龙头（涨幅与资金双强）、趋势向上、量价配合；回避逆势独立走强的无板块支撑个股\n"
            "\n"
            "买卖纪律：\n"
            "- 顺势而为：大盘决定仓位，板块决定方向，个股决定买卖点\n"
            "- 目标：波段持股 3~10 天（target_sell_price 按 +8%~+12% 设置）\n"
            "- 止损：个股 -5% 或大盘趋势反转时无条件降仓（stop_loss_price 按 -5% 设置）\n"
            "- 每日 morning 与 tail 时段评估持仓：趋势延续 hold / 上移卖点 adjust / 趋势破坏 sell"
        ),
        "stock_pool": None,
        "execute_periods": ["morning", "tail"],
        "max_positions": 8,
        "stop_loss_pct": 5.0,
        "take_profit_pct": 12.0,
    },
    {
        "seq": 11,
        "name": "资金潜伏低吸",
        "description": "捕捉板块资金连续多日净流入、但板块内个股尚未出现明显拉升（无 10%+ 大涨）的蓄势方向，提前潜伏等待资金发酵",
        "category": "general",
        "prompt_template": (
            "选股逻辑：\n"
            "1. 用板块排行工具（get_board_ranking）对比资金净流入排行：寻找连续多日（至少 3 个交易日）净流入为正且金额逐步放大、但阶段涨幅平庸（近期累计涨幅明显落后于流入前排）的板块——资金在暗中吸筹而股价尚未兑现\n"
            "2. 板块内选个股：近 10 个交易日内无单日涨幅超 7%、无涨停、未出现 10%+ 阶段大涨的温和放量标的（量能缓慢抬升但价格横盘或小阳推进=吸筹特征）\n"
            "3. 优选：板块净流入持续天数最长 + 个股量比温和放大（1.5~3）+ 距离近期平台突破位不远（蓄势待突破）\n"
            "4. 回避：资金流入但个股已提前大涨兑现的板块、单日脉冲式净流入（一日游资金）、大盘资金持续净流出阶段的个股\n"
            "\n"
            "买卖纪律：\n"
            "- 买点必须接近平台/支撑位，严禁追已脱离底部的标的；当日涨幅已超 5% 的不买\n"
            "- 潜伏要有耐心验证：若买入 3~5 日资金转为净流出且股价滞涨，主动 sell 离场换股\n"
            "- 目标：资金发酵带动主升（target_sell_price 按 +8%~+10% 设置），突破放量后可 adjust 上移\n"
            "- 止损：潜伏逻辑证伪（板块净流入中断+跌破买入平台）即离场（stop_loss_price 按 -4% 设置）\n"
            "- 信号宁缺毋滥：无同时满足「多日流入+未大涨」的板块时输出空数组"
        ),
        "stock_pool": None,
        "execute_periods": ["noon", "tail"],
        "max_positions": 4,
        "stop_loss_pct": 4.0,
        "take_profit_pct": 10.0,
    },
]


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


def upgrade() -> None:
    # ================================================================
    # 1. 策略表新增分类/预置标记字段
    # ================================================================
    op.add_column(
        'business_ai_strategy',
        sa.Column('category', sa.String(length=30), nullable=False,
                  server_default='general',
                  comment='策略分类：pre_market_auction/noon/tail/blue_chip/general'),
    )
    op.add_column(
        'business_ai_strategy',
        sa.Column('is_preset', sa.Boolean(), nullable=False,
                  server_default=sa.text('false'),
                  comment='是否系统预置策略'),
    )
    op.create_index('ix_ai_strategy_category', 'business_ai_strategy', ['category'], unique=False)

    # ================================================================
    # 2. 幂等插入 10 条预置策略（按名称查重，默认停用）
    # ================================================================
    conn = op.get_bind()
    existing_names = {
        row[0] for row in conn.execute(
            sa.text("SELECT name FROM business_ai_strategy WHERE deleted_at IS NULL")
        )
    }
    rows = []
    for item in _PRESET_STRATEGIES:
        if item['name'] in existing_names:
            continue
        # 注意：所有行必须带相同键集合（多行 INSERT 按首行键编译列清单），
        # 无池时置 None，插入后再统一清理为 SQL NULL
        rows.append({
            'id': _PRESET_ID_BASE + item['seq'],
            'deleted_at': None,
            'created_at': _DT,
            'updated_at': None,
            'name': item['name'],
            'description': item['description'],
            'category': item['category'],
            'is_preset': True,
            'prompt_template': item['prompt_template'],
            'stock_pool': item['stock_pool'],
            'execute_periods': item['execute_periods'],
            'max_positions': item['max_positions'],
            'stop_loss_pct': item['stop_loss_pct'],
            'take_profit_pct': item['take_profit_pct'],
            'status': False,  # 预置策略默认停用，由用户在管理页自行启用
            'last_executed_at': None,
        })
    if rows:
        op.bulk_insert(_STRATEGY_TABLE, rows)
        # JSON 列的 None 会落成 JSON null，统一清理为 SQL NULL（无池=AI 全市场自选）
        op.execute(
            "UPDATE business_ai_strategy SET stock_pool = NULL "
            "WHERE stock_pool IS NOT NULL AND stock_pool::text = 'null'"
        )

    # ================================================================
    # 3. 指数成分股快照表（BaoStock 沪深300/中证500）
    # ================================================================
    op.create_table(
        'business_index_constituent',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.Column('record_date', sa.Date(), nullable=False, comment='快照日期（本地时区）'),
        sa.Column('index_code', sa.String(length=20), nullable=False, comment='指数代码，如 000300-沪深300'),
        sa.Column('index_name', sa.String(length=50), nullable=False, comment='指数名称'),
        sa.Column('stock_code', sa.String(length=20), nullable=False, comment='成分股代码（6位）'),
        sa.Column('stock_name', sa.String(length=50), nullable=False, comment='成分股名称'),
        sa.Column('weight', sa.Numeric(precision=10, scale=4), nullable=True, comment='权重(%)'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_date', 'index_code', 'stock_code',
                            name='uk_index_constituent_date_code'),
        comment='指数成分股快照表',
    )
    op.create_index(op.f('ix_business_index_constituent_id'), 'business_index_constituent', ['id'], unique=True)
    op.create_index('ix_business_index_constituent_record_date', 'business_index_constituent', ['record_date'], unique=False)
    op.create_index('ix_business_index_constituent_index_code', 'business_index_constituent', ['index_code'], unique=False)
    op.create_index('ix_business_index_constituent_stock_code', 'business_index_constituent', ['stock_code'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_business_index_constituent_stock_code', table_name='business_index_constituent')
    op.drop_index('ix_business_index_constituent_index_code', table_name='business_index_constituent')
    op.drop_index('ix_business_index_constituent_record_date', table_name='business_index_constituent')
    op.drop_index(op.f('ix_business_index_constituent_id'), table_name='business_index_constituent')
    op.drop_table('business_index_constituent')

    # 删除预置策略种子
    ids = ', '.join(str(_PRESET_ID_BASE + item['seq']) for item in _PRESET_STRATEGIES)
    op.execute(f"DELETE FROM business_ai_strategy WHERE id IN ({ids})")

    op.drop_index('ix_ai_strategy_category', table_name='business_ai_strategy')
    op.drop_column('business_ai_strategy', 'is_preset')
    op.drop_column('business_ai_strategy', 'category')
