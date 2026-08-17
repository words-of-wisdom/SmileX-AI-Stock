#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
个股实时行情辅助层：基于新浪批量行情接口（复用 stock 模块 _sina）
供策略建仓定价与持仓跟踪刷新使用
"""
import logging

from modules.stock.services._sina import fetch_spot_quotes

logger = logging.getLogger(__name__)


def _to_sina_code(code: str) -> str:
    """6位证券代码 → 新浪格式：sh600519 / sz000001 / bj430047"""
    if code.startswith(("sh", "sz", "bj")):
        return code
    if code.startswith(("6", "9")):
        return f"sh{code}"
    if code.startswith(("0", "2", "3")):
        return f"sz{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    return code


async def fetch_latest_prices(codes: list[str]) -> dict[str, float]:
    """批量获取个股最新价。返回 {原始6位代码: 最新价}，失败/停牌的代码缺席。"""
    if not codes:
        return {}
    sina_map = {_to_sina_code(c): c for c in codes}
    try:
        quotes = await fetch_spot_quotes(list(sina_map.keys()))
    except Exception as exc:  # noqa: BLE001
        logger.warning("批量获取最新价失败: %s", exc)
        return {}
    result: dict[str, float] = {}
    for sina_code, quote in quotes.items():
        price = quote.get("latest_price")
        origin = sina_map.get(sina_code)
        if origin and price:
            result[origin] = price
    return result
