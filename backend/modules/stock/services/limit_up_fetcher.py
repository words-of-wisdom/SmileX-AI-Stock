#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
涨停股池抓取层
通过 akshare stock_zt_pool_em 抓取涨停股池数据
"""
import asyncio
import logging

from modules.stock.services._common import num, normalize_code, derive_market_board

logger = logging.getLogger(__name__)


async def fetch_limit_up_pool(trade_date: str) -> list[dict]:
    """抓取涨停股池

    Args:
        trade_date: 交易日期 "YYYYMMDD"
    """
    import akshare as ak

    df = await asyncio.to_thread(ak.stock_zt_pool_em, date=trade_date)
    items = []
    for _, row in df.iterrows():
        code = normalize_code(row.get("代码", ""))
        if not code:
            continue

        # 振幅若接口不提供，从 high/low/prev_close 计算
        amplitude = num(row.get("振幅"))
        high = num(row.get("最高"))
        low = num(row.get("最低"))
        prev_close = num(row.get("昨收"))
        if amplitude is None and high is not None and low is not None and prev_close and prev_close != 0:
            amplitude = round((high - low) / prev_close * 100, 4)

        items.append({
            "stock_code": code,
            "stock_name": str(row.get("名称", "")).strip(),
            "market_board": derive_market_board(code),
            "latest_price": num(row.get("最新价")),
            "change_pct": num(row.get("涨跌幅")),
            "turnover_rate": num(row.get("换手率")),
            "turnover": num(row.get("成交额")),
            "amplitude": amplitude,
            "seal_amount": num(row.get("封板资金")),
            "first_limit_up_time": _fmt_time(row.get("首次封板时间")),
            "last_limit_up_time": _fmt_time(row.get("最后封板时间")),
            "break_count": num(row.get("炸板次数")),
            "consecutive_limit_up": num(row.get("连板数")),
            "industry": str(row.get("所属行业", "")).strip() or None,
            "limit_up_reason": None,
        })

    if not items:
        logger.warning("涨停股池抓取返回空数据: date=%s", trade_date)
    return items


def _fmt_time(val) -> str | None:
    """格式化封板时间：akshare 可能返回 Timestamp 或字符串"""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "nat", "none"):
        return None
    # 提取 HH:MM:SS 部分
    if " " in s:
        s = s.split(" ")[-1]
    return s[:20]
