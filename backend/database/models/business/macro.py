#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
宏观经济指标表
存储中美宏观指数（CPI/PPI/M1/M2 等）的历史序列，按「国家×指标×期次」唯一 upsert
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Numeric, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import mapped_column, Mapped

from database.models.base import Base


class BusinessMacroIndicator(Base):
    """宏观经济指标表"""

    __table_args__ = (
        UniqueConstraint(
            "country", "indicator_code", "period",
            name="uk_macro_country_code_period",
        ),
        Index("ix_macro_country_code_period", "country", "indicator_code", "period"),
        {"comment": "宏观经济指标表"},
    )

    country: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="国家/地区：CN-中国，US-美国",
    )
    indicator_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="指标代码：cpi/ppi/m1/m2/core_cpi 等",
    )
    indicator_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="指标中文名：居民消费价格指数 等",
    )
    period: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="数据期次 YYYY-MM（月度指标）",
    )
    value: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 4), nullable=True, comment="指标值（单位见 unit 字段）",
    )
    yoy: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True, comment="同比增速(%)",
    )
    mom: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True, comment="环比增速(%)",
    )
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="%", comment="单位：% / 亿元 / 亿美元等",
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default=None, comment="数据来源（akshare 接口名）",
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, comment="数据发布时间",
    )
