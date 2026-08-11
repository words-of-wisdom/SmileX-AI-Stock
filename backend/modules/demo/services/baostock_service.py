#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Baostock SDK 简单调用示例
"""
import asyncio
import re

from core.exception.errors import CustomError

# baostock 证券代码格式：sh.600519 / sz.000001 / bj.430047
_CODE_PATTERN = re.compile(r"^(sh|sz|bj)\.\d{6}$")


class BaostockDemoService:
    """Baostock 示例服务"""

    @staticmethod
    async def get_kline(code: str, days: int = 30) -> list[dict]:
        """获取日 K 线数据（bs.query_history_k_data_plus）

        Args:
            code: 证券代码，格式 sh.600519 / sz.000001 / bj.430047
            days: 回看天数（按自然日向前取）
        """
        if not _CODE_PATTERN.match(code):
            raise CustomError(msg="证券代码格式错误，应为 sh.600519 / sz.000001 形式")

        try:
            return await asyncio.to_thread(_fetch_kline, code, days)
        except CustomError:
            raise
        except Exception as exc:
            raise CustomError(msg=f"Baostock 调用失败: {exc}")


def _fetch_kline(code: str, days: int) -> list[dict]:
    from datetime import datetime, timedelta

    import baostock as bs

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    fields = "date,code,open,high,low,close,volume,amount,pctChg"
    items: list[dict] = []

    login_result = bs.login()
    if login_result.error_code != "0":
        raise CustomError(msg=f"Baostock 登录失败: {login_result.error_msg}")
    try:
        rs = bs.query_history_k_data_plus(
            code,
            fields,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            frequency="d",
            adjustflag="3",
        )
        if rs.error_code != "0":
            raise CustomError(msg=f"Baostock 查询失败: {rs.error_msg}")
        while rs.next():
            row = rs.get_row_data()
            items.append(dict(zip(fields.split(","), row)))
    finally:
        bs.logout()

    return items
