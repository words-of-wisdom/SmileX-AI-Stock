#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
akshare SDK 简单调用示例
"""
import asyncio
import re

from core.exception.errors import CustomError

# 纯 6 位数字股票代码
_SYMBOL_PATTERN = re.compile(r"^\d{6}$")


class AkshareDemoService:
    """akshare 示例服务"""

    @staticmethod
    async def get_stock_info(symbol: str) -> list[dict]:
        """获取个股基础信息（ak.stock_individual_info_em）

        Args:
            symbol: 6 位数字股票代码，如 600519
        """
        if not _SYMBOL_PATTERN.match(symbol):
            raise CustomError(msg="股票代码格式错误，应为 6 位数字，如 600519")

        try:
            return await asyncio.to_thread(_fetch_stock_info, symbol)
        except CustomError:
            raise
        except Exception as exc:
            raise CustomError(msg=f"akshare 调用失败: {exc}")


def _fetch_stock_info(symbol: str) -> list[dict]:
    import akshare as ak

    df = ak.stock_individual_info_em(symbol=symbol)
    return [
        {"item": str(row.get("item", "")), "value": str(row.get("value", ""))}
        for _, row in df.iterrows()
    ]
