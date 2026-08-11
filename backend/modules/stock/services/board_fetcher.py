#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
行业/概念板块抓取层
通过 akshare 抓取板块列表（含涨跌幅、成交额、领涨股）和板块资金流
"""
import asyncio
import logging

from modules.stock.services._common import num, normalize_code

logger = logging.getLogger(__name__)


def _pick(row, *keys):
    """从 DataFrame 行中按候选列名取第一个非空值"""
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return None


async def fetch_board_list(board_type: str) -> list[dict]:
    """抓取板块列表（行业或概念）

    Args:
        board_type: "industry" 或 "concept"
    """
    import akshare as ak

    if board_type == "industry":
        df = await asyncio.to_thread(ak.stock_board_industry_name_em)
    else:
        df = await asyncio.to_thread(ak.stock_board_concept_name_em)

    items = []
    for _, row in df.iterrows():
        board_code = str(row.get("板块代码", row.get("排名", ""))).strip()
        board_name = str(row.get("板块名称", "")).strip()
        if not board_code:
            board_code = board_name

        items.append({
            "board_type": board_type,
            "board_code": board_code,
            "board_name": board_name,
            "change_pct": num(row.get("涨跌幅")),
            # 东财板块列表接口不提供成交额/成交量，置空而非错用总市值
            "turnover": None,
            "turnover_rate": num(row.get("换手率")),
            "volume": None,
            "rising_count": num(row.get("上涨家数")),
            "falling_count": num(row.get("下跌家数")),
            # 领涨股票列是名称不是代码，代码字段留空
            "leading_stock_code": None,
            "leading_stock_name": str(row.get("领涨股票", "")).strip() or None,
            "leading_stock_change_pct": num(row.get("领涨股票-涨跌幅")),
        })
    return items


async def fetch_board_fund_flow(board_type: str) -> dict[str, float | None]:
    """抓取板块资金流排行，返回 {board_name: net_inflow} 映射"""
    import akshare as ak

    indicator = "今日"
    sector_type = "行业资金流" if board_type == "industry" else "概念资金流"

    try:
        df = await asyncio.to_thread(
            ak.stock_sector_fund_flow_rank,
            indicator=indicator,
            sector_type=sector_type,
        )
    except Exception as exc:
        logger.warning("板块资金流抓取失败(%s): %s", sector_type, exc)
        return {}

    result = {}
    flow_col = "今日主力净流入-净额" if "今日主力净流入-净额" in df.columns else "主力净流入-净额"
    for _, row in df.iterrows():
        name = str(row.get("名称", "")).strip()
        if name:
            result[name] = num(row.get(flow_col))
    return result
