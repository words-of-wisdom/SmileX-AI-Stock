#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大宗交易（暗盘）Schema
"""

from datetime import date, datetime

from pydantic import Field

from modules.common.schemas.base import BaseEntity


class BlockTradeDailyItem(BaseEntity):
    """每日统计单项响应（含排名变化）"""

    id: int
    record_date: date | None = None
    rank: int = Field(0, description="按 amount_ratio 降序的当日排名")
    rank_change: int | None = Field(None, description="排名变化：正=上升，负=下降，null=新进榜")
    stock_code: str
    stock_name: str
    change_pct: float | None = None
    close_price: float | None = None
    trade_price: float | None = None
    premium_rate: float | None = Field(None, description="折溢率(%)，正=溢价，负=折价")
    trade_count: int | None = None
    trade_volume: float | None = None
    trade_amount: float | None = Field(None, description="成交总额(万元)")
    amount_ratio: float | None = Field(None, description="成交总额/流通市值(%)")


class BlockTradeActiveItem(BaseEntity):
    """活跃A股统计单项响应"""

    id: int
    stat_window: str
    rank: int = Field(0, description="按 list_count_total 降序的排名")
    stock_code: str
    stock_name: str
    latest_price: float | None = None
    change_pct: float | None = None
    last_list_date: date | None = None
    list_count_total: int | None = None
    list_count_premium: int | None = None
    list_count_discount: int | None = None
    total_amount: float | None = Field(None, description="总成交额(万元)")
    premium_rate: float | None = None
    amount_ratio: float | None = None
    avg_change_1d: float | None = None
    avg_change_5d: float | None = None
    avg_change_10d: float | None = None
    avg_change_20d: float | None = None


class BlockTradeSourceItem(BaseEntity):
    """暗盘子榜统计项"""

    sub_board: str
    source_name: str
    stat_window: str | None = None
    last_record_date: date | None = Field(None, description="最近快照日期")
    last_sync_at: datetime | None = Field(None, description="最近同步时间")
    count: int = Field(0, description="最新快照条数")


class BlockTradeHistoryItem(BaseEntity):
    """单股历史排名趋势"""

    record_date: date
    rank: int
