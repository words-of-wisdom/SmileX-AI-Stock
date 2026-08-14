#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大宗交易（暗盘）快照表
存储东方财富大宗交易榜单数据，用于暗盘跟踪
- BusinessBlockTradeDaily: 每日统计（按个股聚合的当日大宗交易排行）
- BusinessBlockTradeActive: 活跃A股统计（按时间窗口的大宗交易上榜次数排行）
- BusinessBlockTradeSyncLog: 采集日志
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Numeric, Date, Boolean, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped

from database.models.base import Base


class BusinessBlockTradeDaily(Base):
    """
    大宗交易每日统计快照表
    数据源：东方财富 data.eastmoney.com/dzjy/（akshare stock_dzjy_mrtj）
    """

    __table_args__ = (
        UniqueConstraint(
            "record_date", "stock_code",
            name="uk_block_trade_daily_date_code",
        ),
        {"comment": "大宗交易每日统计快照表"},
    )

    record_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="交易日期（本地时区）"
    )
    stock_code: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="证券代码"
    )
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="证券简称")
    change_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), nullable=True, comment="涨跌幅(%)", default=None
    )
    close_price: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 4), nullable=True, comment="收盘价", default=None
    )
    trade_price: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 4), nullable=True, comment="成交价", default=None
    )
    premium_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True, comment="折溢率(%)，正=溢价，负=折价", default=None
    )
    trade_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="成交笔数", default=None
    )
    trade_volume: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True, comment="成交总量(股)", default=None
    )
    trade_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 4), nullable=True, comment="成交总额(万元)", default=None
    )
    amount_ratio: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True, comment="成交总额/流通市值(%)", default=None
    )


class BusinessBlockTradeActive(Base):
    """
    大宗交易活跃A股统计表
    数据源：东方财富 data.eastmoney.com/dzjy/（akshare stock_dzjy_hygtj）
    按时间窗口（近一月/三月/六月/一年）统计个股大宗交易上榜频次
    """

    __table_args__ = (
        UniqueConstraint(
            "stat_window", "stock_code",
            name="uk_block_trade_active_window_code",
        ),
        {"comment": "大宗交易活跃A股统计表"},
    )

    stat_window: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="统计窗口：近一月/近三月/近六月/近一年"
    )
    stock_code: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="证券代码"
    )
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="证券简称")
    latest_price: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 4), nullable=True, comment="最新价", default=None
    )
    change_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), nullable=True, comment="涨跌幅(%)", default=None
    )
    last_list_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="最近上榜日", default=None
    )
    list_count_total: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="上榜次数-总计", default=None
    )
    list_count_premium: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="上榜次数-溢价", default=None
    )
    list_count_discount: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="上榜次数-折价", default=None
    )
    total_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 4), nullable=True, comment="总成交额(万元)", default=None
    )
    premium_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True, comment="折溢率(%)", default=None
    )
    amount_ratio: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True, comment="成交总额/流通市值(%)", default=None
    )
    avg_change_1d: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), nullable=True, comment="上榜后1日平均涨跌幅(%)", default=None
    )
    avg_change_5d: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), nullable=True, comment="上榜后5日平均涨跌幅(%)", default=None
    )
    avg_change_10d: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), nullable=True, comment="上榜后10日平均涨跌幅(%)", default=None
    )
    avg_change_20d: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), nullable=True, comment="上榜后20日平均涨跌幅(%)", default=None
    )


class BusinessBlockTradeSyncLog(Base):
    """
    大宗交易（暗盘）采集日志表
    记录每次按子榜抓取的结果，sub_board 区分 daily / active
    """

    sub_board: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="子榜：daily-每日统计 / active-活跃A股"
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
    stat_window: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="统计窗口（仅 active 子榜有值）", default=None
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
