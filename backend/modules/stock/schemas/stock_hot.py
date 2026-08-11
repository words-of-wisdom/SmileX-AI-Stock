#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票热榜 Schema
"""

from datetime import date, datetime

from pydantic import Field

from modules.common.schemas.base import BaseEntity


class StockHotQueryParams(BaseEntity):
    """股票热榜查询参数"""

    source: str | None = Field(None, description="榜单源 key")
    record_date: str | None = Field(None, description="快照日期（YYYY-MM-DD），为空取最新")


class StockHotRankItem(BaseEntity):
    """热榜单项响应（含排名变化）"""

    id: int
    source: str
    source_name: str = ""
    record_date: date | None = None
    rank: int
    rank_change: int | None = Field(None, description="排名变化：正=上升，负=下降，null=新进榜")
    stock_code: str
    stock_name: str
    latest_price: float | None = None
    change_pct: float | None = None
    hot_value: float | None = None


class StockHotHistoryItem(BaseEntity):
    """单股历史排名趋势"""

    record_date: date
    rank: int


class StockHotSourceItem(BaseEntity):
    """热榜源统计项"""

    source: str
    source_name: str
    group: str = ""
    last_record_date: date | None = Field(None, description="最近快照日期")
    last_sync_at: datetime | None = Field(None, description="最近同步时间")
    count: int = Field(0, description="最新快照条数")
