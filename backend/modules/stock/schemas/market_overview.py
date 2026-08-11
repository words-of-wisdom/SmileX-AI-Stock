#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大盘指数 Schema
"""

from datetime import date

from pydantic import Field

from modules.common.schemas.base import BaseEntity


class MarketIndexItem(BaseEntity):
    """大盘指数快照项"""

    id: int
    record_date: date
    index_code: str
    index_name: str
    latest_price: float | None = None
    change_pct: float | None = None
    change_amount: float | None = None
    volume: float | None = None
    turnover: float | None = None
    amplitude: float | None = None
    high: float | None = None
    low: float | None = None
    open: float | None = None
    prev_close: float | None = None


class MarketIndexHistoryItem(BaseEntity):
    """单指数历史趋势项"""

    record_date: date
    latest_price: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    turnover: float | None = None
    high: float | None = None
    low: float | None = None
    open: float | None = None
    prev_close: float | None = None


class MarketIndexOption(BaseEntity):
    """指数下拉选项"""

    index_code: str
    index_name: str


class MarketFundFlowItem(BaseEntity):
    """大盘资金流日快照项"""

    id: int
    record_date: date
    main_net_inflow: float | None = None
    super_large_net_inflow: float | None = None
    large_net_inflow: float | None = None
    medium_net_inflow: float | None = None
    small_net_inflow: float | None = None
