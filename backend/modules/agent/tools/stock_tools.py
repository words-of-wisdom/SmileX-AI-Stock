"""
Agent 股票相关工具函数 —— 供 LLM 通过 Function Calling 自主查询系统中的股票数据。

每个工具用 @register_tool 装饰器声明式注册，自动出现在工具列表中。
工具函数第一个参数固定为 db: AsyncSession（由 tool_registry.execute 注入）。
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from modules.agent.services.tool_registry import register_tool
from modules.stock.services.stock_hot_service import StockHotService
from modules.stock.services.market_service import MarketService
from modules.stock.services.board_service import BoardService
from modules.stock.services.limit_up_service import LimitUpService
from modules.stock.services.constituent_service import ConstituentService

logger = logging.getLogger(__name__)


@register_tool(
    name="get_hot_stocks",
    description="获取当前各平台的股票热榜数据（如东方财富、同花顺等热榜），了解市场关注度最高的股票。返回股票代码、名称、排名、最新价、涨跌幅、热度值等信息。",
    parameters={
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "热榜来源，可选值：eastmoney（东方财富）、10jqka（同花顺）、xueqiu（雪球）。留空则返回所有来源的最新数据。",
            },
            "limit": {
                "type": "integer",
                "description": "每个来源返回的最大条目数，默认 10",
                "default": 10,
            },
        },
    },
)
async def get_hot_stocks(
    db: AsyncSession, source: str = "", limit: int = 10
) -> dict[str, Any]:
    """获取股票热榜数据。"""
    # 先获取所有可用来源
    sources = await StockHotService.get_sources(db)
    if not sources:
        return {"items": [], "message": "当前无热榜数据，请先同步热榜"}

    # 过滤指定来源
    target_sources = [s.source for s in sources]
    if source:
        target_sources = [s for s in target_sources if s == source]
        if not target_sources:
            return {
                "error": f"来源 {source} 不存在，可用来源: {[s.source for s in sources]}"
            }

    result: dict[str, Any] = {"sources": {}}
    for src in target_sources:
        rank_list = await StockHotService.get_rank_list(db, src)
        items = []
        for item in rank_list[:limit]:
            items.append(
                {
                    "rank": item.rank,
                    "stock_code": item.stock_code,
                    "stock_name": item.stock_name,
                    "latest_price": float(item.latest_price) if item.latest_price else None,
                    "change_pct": float(item.change_pct) if item.change_pct else None,
                    "hot_value": float(item.hot_value) if item.hot_value else None,
                    "rank_change": item.rank_change,
                }
            )
        src_info = next((s for s in sources if s.source == src), None)
        result["sources"][src] = {
            "source_name": src_info.source_name if src_info else src,
            "record_date": str(src_info.last_record_date) if src_info and src_info.last_record_date else None,
            "items": items,
        }

    return result


@register_tool(
    name="get_market_indices",
    description="获取A股大盘指数最新行情（上证指数、深证成指、创业板指等），包含最新点位、涨跌幅、成交量、成交额等。用于了解整体大盘走势。",
    parameters={
        "type": "object",
        "properties": {
            "record_date": {
                "type": "string",
                "description": "查询日期，格式 YYYY-MM-DD，留空则取最新快照日",
            },
        },
    },
)
async def get_market_indices(
    db: AsyncSession, record_date: str = ""
) -> dict[str, Any]:
    """获取大盘指数行情。"""
    indices = await MarketService.get_indices(db, record_date or None)
    if not indices:
        return {"items": [], "message": "当前无大盘指数数据"}

    return {
        "record_date": str(indices[0].record_date) if indices else None,
        "items": [
            {
                "index_code": idx.index_code,
                "index_name": idx.index_name,
                "latest_price": float(idx.latest_price) if idx.latest_price else None,
                "change_pct": float(idx.change_pct) if idx.change_pct else None,
                "change_amount": float(idx.change_amount) if idx.change_amount else None,
                "volume": float(idx.volume) if idx.volume else None,
                "turnover": float(idx.turnover) if idx.turnover else None,
                "amplitude": float(idx.amplitude) if idx.amplitude else None,
            }
            for idx in indices
        ],
    }


@register_tool(
    name="get_market_fund_flow",
    description="获取A股大盘资金流向数据（主力、超大单、大单、中单、小单的净流入），用于判断市场资金动向。可查看最近 N 天的资金流趋势。",
    parameters={
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "查看最近几天的资金流数据，默认 5 天",
                "default": 5,
            },
        },
    },
)
async def get_market_fund_flow(db: AsyncSession, days: int = 5) -> dict[str, Any]:
    """获取大盘资金流数据。"""
    flows = await MarketService.get_fund_flow(db, days=days)
    if not flows:
        return {"items": [], "message": "当前无资金流数据"}

    return {
        "items": [
            {
                "record_date": str(f.record_date),
                "main_net_inflow": float(f.main_net_inflow) if f.main_net_inflow else None,
                "super_large_net_inflow": float(f.super_large_net_inflow)
                if f.super_large_net_inflow
                else None,
                "large_net_inflow": float(f.large_net_inflow) if f.large_net_inflow else None,
                "medium_net_inflow": float(f.medium_net_inflow) if f.medium_net_inflow else None,
                "small_net_inflow": float(f.small_net_inflow) if f.small_net_inflow else None,
            }
            for f in flows
        ],
    }


@register_tool(
    name="get_board_ranking",
    description="获取行业板块或概念板块的涨跌幅排行（如领涨/领跌的行业或概念），包含板块名称、涨跌幅、成交额、换手率、领涨股等。用于了解板块轮动和热点方向。",
    parameters={
        "type": "object",
        "properties": {
            "board_type": {
                "type": "string",
                "enum": ["industry", "concept"],
                "description": "板块类型：industry-行业板块，concept-概念板块。默认 industry",
                "default": "industry",
            },
            "sort_by": {
                "type": "string",
                "enum": ["change_pct", "net_inflow"],
                "description": "排序字段：change_pct-按涨跌幅，net_inflow-按主力净流入。默认 change_pct",
                "default": "change_pct",
            },
            "sort_order": {
                "type": "string",
                "enum": ["desc", "asc"],
                "description": "排序方向：desc-降序（领涨/净流入最多），asc-升序（领跌/净流出最多）。默认 desc",
                "default": "desc",
            },
            "limit": {
                "type": "integer",
                "description": "返回条目数，默认 10",
                "default": 10,
            },
        },
    },
)
async def get_board_ranking(
    db: AsyncSession,
    board_type: str = "industry",
    sort_by: str = "change_pct",
    sort_order: str = "desc",
    limit: int = 10,
) -> dict[str, Any]:
    """获取板块涨跌幅排行。"""
    boards = await BoardService.get_list(
        db, board_type=board_type, sort_by=sort_by, sort_order=sort_order
    )
    if not boards:
        return {"items": [], "message": f"当前无{board_type}板块数据"}

    return {
        "board_type": board_type,
        "record_date": str(boards[0].record_date) if boards else None,
        "items": [
            {
                "board_code": b.board_code,
                "board_name": b.board_name,
                "change_pct": float(b.change_pct) if b.change_pct else None,
                "turnover": float(b.turnover) if b.turnover else None,
                "turnover_rate": float(b.turnover_rate) if b.turnover_rate else None,
                "net_inflow": float(b.net_inflow) if b.net_inflow else None,
                "rising_count": b.rising_count,
                "falling_count": b.falling_count,
                "leading_stock_name": b.leading_stock_name,
                "leading_stock_change_pct": float(b.leading_stock_change_pct)
                if b.leading_stock_change_pct
                else None,
            }
            for b in boards[:limit]
        ],
    }


@register_tool(
    name="get_index_history",
    description="获取大盘指数的历史日K线数据（最近N天），包含每日收盘点位、涨跌幅、成交量、成交额、最高、最低等。用于判断指数的中期趋势（如上证指数、沪深300是否处于上升通道）。数据不足时会自动从数据源回补。",
    parameters={
        "type": "object",
        "properties": {
            "index_code": {
                "type": "string",
                "description": "指数代码：000001-上证指数、399001-深证成指、399006-创业板指、000688-科创50、000300-沪深300、000905-中证500、000852-中证1000。默认 000001",
                "default": "000001",
            },
            "days": {
                "type": "integer",
                "description": "查看最近几天的日K线，默认 30 天",
                "default": 30,
            },
        },
    },
)
async def get_index_history(
    db: AsyncSession, index_code: str = "000001", days: int = 30
) -> dict[str, Any]:
    """获取指数历史日K线。"""
    days = max(1, min(days, 250))
    bars = await MarketService.get_history(db, index_code, days=days)
    if not bars:
        return {"items": [], "message": f"指数 {index_code} 暂无历史数据"}

    return {
        "index_code": index_code,
        "days": len(bars),
        "items": [
            {
                "record_date": str(b.record_date),
                "latest_price": b.latest_price,
                "change_pct": b.change_pct,
                "volume": b.volume,
                "turnover": b.turnover,
                "high": b.high,
                "low": b.low,
                "open": b.open,
                "prev_close": b.prev_close,
            }
            for b in bars
        ],
    }


@register_tool(
    name="get_index_constituents",
    description="获取指数成分股列表（当前支持沪深300、中证500），包含成分股代码、名称、权重（如有）。用于蓝筹白马/核心资产类选股时获取结构化的成分股候选池。",
    parameters={
        "type": "object",
        "properties": {
            "index_code": {
                "type": "string",
                "enum": ["000300", "000905"],
                "description": "指数代码：000300-沪深300，000905-中证500。默认 000300",
                "default": "000300",
            },
            "limit": {
                "type": "integer",
                "description": "返回条目数，默认 50（沪深300/中证500各约300/500只）",
                "default": 50,
            },
        },
    },
)
async def get_index_constituents(
    db: AsyncSession, index_code: str = "000300", limit: int = 50
) -> dict[str, Any]:
    """获取指数成分股列表。"""
    items = await ConstituentService.get_list(db, index_code=index_code, limit=limit)
    if not items:
        return {
            "items": [],
            "message": f"指数 {index_code} 暂无成分股数据，请等待成分股同步任务执行（每交易日 17:10）",
        }

    return {
        "index_code": index_code,
        "index_name": items[0].index_name,
        "record_date": str(items[0].record_date),
        "items": [
            {
                "stock_code": it.stock_code,
                "stock_name": it.stock_name,
                "weight": float(it.weight) if it.weight else None,
            }
            for it in items
        ],
    }


@register_tool(
    name="get_limit_up_stocks",
    description="获取当日涨停股票列表，包含股票代码、名称、连板数、封板资金、涨停原因、所属行业等。用于分析市场涨停热点和打板情绪。",
    parameters={
        "type": "object",
        "properties": {
            "market_board": {
                "type": "string",
                "enum": ["all", "main", "chinext", "star", "bse"],
                "description": "市场板块过滤：all-全部，main-主板，chinext-创业板，star-科创板，bse-北交所。默认 all",
                "default": "all",
            },
            "limit": {
                "type": "integer",
                "description": "返回条目数，默认 15",
                "default": 15,
            },
        },
    },
)
async def get_limit_up_stocks(
    db: AsyncSession, market_board: str = "all", limit: int = 15
) -> dict[str, Any]:
    """获取涨停股列表。"""
    items, total = await LimitUpService.get_list(
        db, market_board=market_board, offset=0, limit=limit
    )
    if not items:
        return {"items": [], "total": 0, "message": "当前无涨停数据"}

    return {
        "total": total,
        "record_date": str(items[0].record_date) if items else None,
        "items": [
            {
                "stock_code": item.stock_code,
                "stock_name": item.stock_name,
                "market_board": item.market_board,
                "latest_price": float(item.latest_price) if item.latest_price else None,
                "change_pct": float(item.change_pct) if item.change_pct else None,
                "consecutive_limit_up": item.consecutive_limit_up,
                "seal_amount": float(item.seal_amount) if item.seal_amount else None,
                "turnover": float(item.turnover) if item.turnover else None,
                "turnover_rate": float(item.turnover_rate) if item.turnover_rate else None,
                "first_limit_up_time": item.first_limit_up_time,
                "break_count": item.break_count,
                "industry": item.industry,
                "limit_up_reason": item.limit_up_reason,
            }
            for item in items
        ],
    }
