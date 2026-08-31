#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
行业/概念板块 Schema
"""

from datetime import date

from pydantic import Field

from modules.common.schemas.base import BaseEntity


class BoardLeadingStock(BaseEntity):
    """板块领涨股单项"""

    code: str | None = Field(None, description="股票代码，兜底数据源可能缺失")
    name: str
    change_pct: float | None = Field(None, description="涨跌幅(%)")


class BoardDailyItem(BaseEntity):
    """板块日快照项"""

    id: int
    record_date: date
    board_type: str = Field(..., description="板块类型: industry/concept")
    board_code: str
    board_name: str
    change_pct: float | None = None
    turnover: float | None = None
    turnover_rate: float | None = None
    volume: float | None = None
    net_inflow: float | None = None
    rising_count: int | None = None
    falling_count: int | None = None
    leading_stock_code: str | None = None
    leading_stock_name: str | None = None
    leading_stock_change_pct: float | None = None
    leading_stocks: list[BoardLeadingStock] | None = Field(
        None, description="领涨股前三名，按板块内涨幅降序"
    )


class BoardHistoryItem(BaseEntity):
    """单板块历史趋势项"""

    record_date: date
    change_pct: float | None = None
    turnover: float | None = None
    net_inflow: float | None = None
    rising_count: int | None = None
    falling_count: int | None = None
