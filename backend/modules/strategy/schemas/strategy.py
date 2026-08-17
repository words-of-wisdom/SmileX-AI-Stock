#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 分析策略相关 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

# 执行时段常量（策略配置与执行记录共用）
EXECUTE_PERIODS = ("pre_market", "morning", "noon", "tail", "post_close")

EXECUTE_PERIOD_NAMES = {
    "pre_market": "早盘集合竞价",
    "morning": "早盘",
    "noon": "午盘",
    "tail": "尾盘",
    "post_close": "盘后",
    "manual": "手动执行",
}


class StrategyCreateRequest(BaseModel):
    """创建策略请求"""

    name: str = Field(..., min_length=1, max_length=100, description="策略名称")
    description: Optional[str] = Field(None, max_length=500, description="策略描述")
    prompt_template: Optional[str] = Field(None, description="策略定制提示词")
    stock_pool: Optional[dict] = Field(None, description="股票池 {codes: [...]}")
    execute_periods: list[str] = Field(
        default_factory=lambda: ["morning"], description="执行时段列表"
    )
    max_positions: int = Field(10, ge=1, le=100, description="最大同时持仓数")
    stop_loss_pct: Optional[float] = Field(5.0, ge=0, le=100, description="默认止损比例(%)")
    take_profit_pct: Optional[float] = Field(10.0, ge=0, le=500, description="默认止盈比例(%)")
    status: bool = Field(True, description="状态：True-启用，False-停用")


class StrategyUpdateRequest(StrategyCreateRequest):
    """更新策略请求（全量字段）"""

    pass


class StrategyItem(BaseModel):
    """策略列表项"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    prompt_template: Optional[str] = None
    stock_pool: Optional[dict] = None
    execute_periods: Optional[list] = None
    max_positions: int
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    status: bool
    last_executed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class StrategyRunItem(BaseModel):
    """策略执行记录项"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    strategy_name: str
    run_period: str
    run_date: str
    trigger_type: str
    status: bool
    parsed_signals: Optional[list] = None
    opened_count: int
    closed_count: int
    error_msg: Optional[str] = None
    created_at: Optional[datetime] = None


class SignalItem(BaseModel):
    """单条 AI 信号（LLM 结构化输出）"""

    stock_code: str
    stock_name: str = ""
    action: str  # buy / sell / hold / adjust
    buy_price: Optional[float] = None
    target_sell_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    reason: Optional[str] = None


class StrategyRunResult(BaseModel):
    """策略执行结果"""

    run_id: int
    status: bool
    signals: list[SignalItem] = []
    opened_count: int = 0
    closed_count: int = 0
    error_msg: Optional[str] = None


class PositionItem(BaseModel):
    """持仓项"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    strategy_name: str
    stock_code: str
    stock_name: str
    buy_price: float
    buy_time: datetime
    buy_reason: Optional[str] = None
    quantity: int
    target_sell_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    status: str
    latest_price: Optional[float] = None
    floating_pnl_pct: Optional[float] = None
    tracked_at: Optional[datetime] = None
    sell_price: Optional[float] = None
    sell_time: Optional[datetime] = None
    sell_reason: Optional[str] = None
    return_rate: Optional[float] = None


class PositionCloseRequest(BaseModel):
    """手动平仓请求"""

    price: Optional[float] = Field(None, gt=0, description="卖出价，为空取最新价")
    reason: Optional[str] = Field(None, max_length=500, description="卖出备注")


class TrackLogItem(BaseModel):
    """持仓跟踪日志项"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    position_id: int
    track_time: datetime
    latest_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    ai_adjusted_target: Optional[float] = None
    adjust_reason: Optional[str] = None


class StrategyStatsItem(BaseModel):
    """策略回报率统计"""

    strategy_id: int
    strategy_name: str
    holding_count: int = 0
    closed_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate: Optional[float] = None  # 胜率(%)，无平仓记录时为空
    total_return_rate: Optional[float] = None  # 累计收益率(%)，各笔等权简单加总
    avg_return_rate: Optional[float] = None  # 平均单笔收益率(%)
    best_return_rate: Optional[float] = None
    worst_return_rate: Optional[float] = None
