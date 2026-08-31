#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
涨停股池 Schema
"""

from datetime import date

from pydantic import Field

from modules.common.schemas.base import BaseEntity


class ContinuationFactor(BaseEntity):
    """连板概率评分因子"""

    type: str = Field(..., description="因子类型: consecutive/seal_ratio/break_count/first_seal/turnover_rate")
    value: float | str | None = Field(None, description="因子原始值，缺失为 None")


class LimitUpStockItem(BaseEntity):
    """涨停股单项"""

    id: int
    record_date: date
    stock_code: str
    stock_name: str
    market_board: str = Field(..., description="市场板块: main/chinext/star/bse")
    latest_price: float | None = None
    change_pct: float | None = None
    turnover_rate: float | None = None
    turnover: float | None = None
    amplitude: float | None = None
    seal_amount: float | None = None
    first_limit_up_time: str | None = None
    last_limit_up_time: str | None = None
    break_count: int | None = None
    consecutive_limit_up: int | None = None
    industry: str | None = None
    limit_up_reason: str | None = None
    continuation_probability: int | None = Field(None, description="连板概率评分(0-100)，读时按封板质量启发式计算")
    continuation_factors: list[ContinuationFactor] | None = Field(None, description="连板概率评分因子明细")


class LimitUpStats(BaseEntity):
    """当日涨停统计"""

    record_date: date | None = None
    total_count: int = 0
    main_count: int = 0
    chinext_count: int = 0
    star_count: int = 0
    bse_count: int = 0
    max_consecutive: int = 0
    board_distribution: dict[str, int] = Field(
        default_factory=dict, description="行业分布统计"
    )
