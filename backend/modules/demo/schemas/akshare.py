#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
akshare 示例接口 Schema
"""
from pydantic import Field

from modules.common.schemas.base import BaseEntity


class StockInfoItem(BaseEntity):
    """个股基础信息项（akshare stock_individual_info_em 的 item/value 对）"""

    item: str = Field(..., description="信息项名称")
    value: str = Field(..., description="信息项值")
