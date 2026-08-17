#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 分析策略表
支持定制策略（提示词 + 股票池 + 执行时段），LLM 生成买卖点，
模拟盘跟踪持仓并计算回报率
- BusinessAiStrategy: 策略配置
- BusinessStrategyRun: 策略执行记录（AI 原始输出 + 解析后的信号）
- BusinessStrategyPosition: 个股模拟持仓（买点/预估卖点/跟踪/回报率）
- BusinessPositionTrackLog: 持仓跟踪日志（每次跟踪的价格与浮盈快照）
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, BigInteger, Numeric, Boolean, Text, DateTime, JSON, Index
from sqlalchemy.orm import mapped_column, Mapped

from database.models.base import Base


class BusinessAiStrategy(Base):
    """AI 分析策略配置表"""

    __table_args__ = (
        Index("ix_ai_strategy_status", "status"),
        {"comment": "AI 分析策略配置表"},
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="策略名称")
    description: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None, comment="策略描述"
    )
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, default="general", index=True,
        comment="策略分类：pre_market_auction/noon/tail/blue_chip/general",
    )
    is_preset: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否系统预置策略"
    )
    prompt_template: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None, comment="策略定制提示词（选股逻辑、风控要求等）"
    )
    stock_pool: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=None,
        comment="股票池：{\"codes\": [\"600519\", ...]}，为空则由 AI 在全市场内自主选择",
    )
    execute_periods: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, default=None,
        comment="执行时段列表：pre_market/morning/noon/tail/post_close",
    )
    max_positions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10, comment="最大同时持仓数"
    )
    stop_loss_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), nullable=True, default=5.0, comment="默认止损比例(%)，相对买价"
    )
    take_profit_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), nullable=True, default=10.0, comment="默认止盈比例(%)，相对买价"
    )
    status: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="状态：True-启用，False-停用"
    )
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, comment="最近执行时间"
    )


class BusinessStrategyRun(Base):
    """策略执行记录表"""

    __table_args__ = (
        Index("ix_strategy_run_strategy", "strategy_id", "created_at"),
        {"comment": "策略执行记录表"},
    )

    strategy_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="策略 ID"
    )
    strategy_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="策略名称（执行时快照）"
    )
    run_period: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="执行时段：pre_market/morning/noon/tail/post_close/manual"
    )
    run_date: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="执行日期 YYYY-MM-DD（同日同时段去重用）"
    )
    trigger_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="schedule",
        comment="触发方式：schedule-定时，manual-手动"
    )
    status: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="执行状态：True-成功，False-失败"
    )
    ai_raw_response: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None, comment="AI 原始回复文本"
    )
    parsed_signals: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, default=None, comment="解析后的结构化信号列表"
    )
    opened_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="本次新建仓数量"
    )
    closed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="本次平仓数量"
    )
    error_msg: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None, comment="错误信息"
    )


class BusinessStrategyPosition(Base):
    """策略个股模拟持仓表"""

    __table_args__ = (
        Index("ix_strategy_position_strategy_status", "strategy_id", "status"),
        Index("ix_strategy_position_stock", "stock_code"),
        {"comment": "策略个股模拟持仓表"},
    )

    strategy_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="策略 ID"
    )
    strategy_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="策略名称（建仓时快照）"
    )
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="证券代码")
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="证券简称")

    buy_price: Mapped[float] = mapped_column(
        Numeric(16, 4), nullable=False, comment="买入价（信号触发时最新价）"
    )
    buy_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="买入时间"
    )
    buy_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None, comment="AI 给出的买入理由"
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, comment="持仓数量（股，默认一手）"
    )

    target_sell_price: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 4), nullable=True, default=None, comment="预估卖点（目标价）"
    )
    stop_loss_price: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 4), nullable=True, default=None, comment="止损价"
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="holding",
        comment="持仓状态：holding-持仓中，closed-已平仓，cancelled-已取消",
    )

    latest_price: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 4), nullable=True, default=None, comment="最新价（跟踪任务刷新）"
    )
    floating_pnl_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True, default=None, comment="浮动盈亏比例(%)"
    )
    tracked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, comment="最近跟踪时间"
    )

    sell_price: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 4), nullable=True, default=None, comment="卖出价"
    )
    sell_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, comment="卖出时间"
    )
    sell_reason: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None,
        comment="卖出原因：stop_loss/take_profit/target_reached/ai_signal/manual",
    )
    return_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True, default=None, comment="最终收益率(%)，平仓时计算"
    )


class BusinessPositionTrackLog(Base):
    """持仓跟踪日志表"""

    __table_args__ = (
        Index("ix_position_track_position", "position_id", "track_time"),
        {"comment": "持仓跟踪日志表"},
    )

    position_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="持仓 ID"
    )
    track_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="跟踪时间"
    )
    latest_price: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 4), nullable=True, default=None, comment="当时最新价"
    )
    pnl_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), nullable=True, default=None, comment="当时浮动盈亏(%)"
    )
    ai_adjusted_target: Mapped[Optional[float]] = mapped_column(
        Numeric(16, 4), nullable=True, default=None, comment="AI 本次调整后的预估卖点"
    )
    adjust_reason: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None, comment="调整理由（未调整为空）"
    )
