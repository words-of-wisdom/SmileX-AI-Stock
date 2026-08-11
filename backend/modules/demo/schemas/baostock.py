#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Baostock 示例接口 Schema
"""
from typing import Optional

from pydantic import Field

from modules.common.schemas.base import BaseEntity


class KlineItem(BaseEntity):
    """日 K 线数据项（baostock query_history_k_data_plus 返回原始字符串）"""

    date: str = Field(..., description="交易日期 YYYY-MM-DD")
    code: str = Field(..., description="证券代码，如 sh.600519")
    open: Optional[str] = Field(None, description="开盘价")
    high: Optional[str] = Field(None, description="最高价")
    low: Optional[str] = Field(None, description="最低价")
    close: Optional[str] = Field(None, description="收盘价")
    volume: Optional[str] = Field(None, description="成交量（股）")
    amount: Optional[str] = Field(None, description="成交额（元）")
    pctChg: Optional[str] = Field(None, description="涨跌幅(%)")
