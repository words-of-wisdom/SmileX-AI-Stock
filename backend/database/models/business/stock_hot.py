#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票热榜快照表
存储多源抓取的热门股排名快照，用于每日排名变化跟踪
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Numeric, Date, Boolean, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped

from database.models.base import Base


class BusinessStockHotRank(Base):
    """
    股票热榜快照表
    """

    __table_args__ = (
        UniqueConstraint(
            "record_date", "source", "stock_code",
            name="uk_stock_hot_rank_date_source_code",
        ),
        {"comment": "股票热榜快照表"},
    )

    record_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="排名快照日（本地时区）"
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="榜单源 key"
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False, comment="当日排名")
    stock_code: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="股票代码"
    )
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="股票名称")
    latest_price: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 4), nullable=True, comment="最新价", default=None
    )
    change_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), nullable=True, comment="涨跌幅(%)", default=None
    )
    hot_value: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 4), nullable=True, comment="热度/关注数", default=None
    )


class BusinessStockHotSyncLog(Base):
    """
    股票热榜采集日志表
    记录每次按源抓取的结果
    """

    source: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="榜单源 key"
    )
    status: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="采集状态：True-成功，False-失败"
    )
    fetched_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="抓取条数", default=0
    )
    saved_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="入库条数", default=0
    )
    error_msg: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="错误信息", default=None
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="开始时间", default=None
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="结束时间", default=None
    )
