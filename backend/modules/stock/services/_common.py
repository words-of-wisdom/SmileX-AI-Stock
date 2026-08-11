#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
stock 模块通用工具函数
"""
import re


def num(val) -> float | None:
    """安全转 float，失败返回 None"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        # NaN 直接落库会污染排序与统计，统一视为无值
        if val != val:
            return None
        return float(val)
    s = str(val).strip().replace("%", "").replace(",", "")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def normalize_code(raw) -> str:
    """规范化股票代码：剥离交易所前缀，返回纯数字代码"""
    s = str(raw).strip().upper()
    s = re.sub(r"^(SH|SZ|BJ)|\.(SH|SZ|BJ)$", "", s)
    return s[:20]


def derive_market_board(code: str) -> str:
    """根据股票代码推导市场板块：main/chinext/star/bse"""
    pure = normalize_code(code)
    if pure.startswith("688"):
        return "star"
    if pure.startswith("30"):
        return "chinext"
    if pure.startswith("8") or pure.startswith("4"):
        return "bse"
    return "main"
