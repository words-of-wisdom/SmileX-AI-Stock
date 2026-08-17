#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 分析策略定时任务
1. strategy_run_execute: 周一至周五 9-16 点每 10 分钟检查启用策略，
   按当前时间匹配执行时段（集合竞价/早盘/午盘/尾盘/盘后）触发 LLM 分析
2. strategy_position_track: 交易时段内每 5 分钟刷新持仓最新价/浮盈，
   触发止损/止盈/预估卖点自动平仓

说明：与 stock_hot_sync 相同的坑——APScheduler 星期字段 Monday=0，
数字 "1-5" 实为周二至周六，必须用 mon-fri。
"""

import logging
from datetime import datetime, time as dt_time

from modules.scheduler.core.registry import scheduled_task

logger = logging.getLogger(__name__)

# 各执行时段的触发窗口（本地时区 Asia/Shanghai，周一至周五）
# 每个时段取窗口内第一次检查时触发，靠 StrategyRun 的 (strategy, run_date, run_period) 去重
_PERIOD_WINDOWS: dict[str, tuple[dt_time, dt_time]] = {
    "pre_market": (dt_time(9, 15), dt_time(9, 25)),   # 早盘集合竞价
    "morning": (dt_time(9, 30), dt_time(11, 30)),     # 早盘
    "noon": (dt_time(13, 0), dt_time(14, 30)),        # 午盘
    "tail": (dt_time(14, 30), dt_time(15, 0)),        # 尾盘
    "post_close": (dt_time(15, 5), dt_time(16, 0)),   # 盘后
}

# 连续竞价时段（持仓跟踪窗口）
_TRADING_WINDOWS: tuple[tuple[dt_time, dt_time], ...] = (
    (dt_time(9, 30), dt_time(11, 30)),
    (dt_time(13, 0), dt_time(15, 0)),
)


def _match_period(now: datetime) -> str | None:
    """当前时间命中的执行时段（周一至周五）"""
    if now.weekday() >= 5:
        return None
    current = now.time()
    for period, (start, end) in _PERIOD_WINDOWS.items():
        if start <= current <= end:
            return period
    return None


def _in_trading_hours(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    current = now.time()
    return any(start <= current <= end for start, end in _TRADING_WINDOWS)


@scheduled_task(
    cron="*/10 9-16 * * mon-fri",
    name="AI策略时段执行",
    description="按各启用策略配置的执行时段（集合竞价/早盘/午盘/尾盘/盘后）触发 LLM 买卖点分析，同日同时段去重",
    task_key="strategy.run_execute",
    is_system=True,
)
async def strategy_run_execute():
    """检查并执行当前时段命中的启用策略"""
    from sqlalchemy import select

    from database.db_manager import get_session
    from database.models.business.strategy import BusinessStrategyRun
    from database.utils.timezone import timezone
    from modules.strategy.services.strategy_service import StrategyService
    from modules.strategy.services.strategy_executor import StrategyExecutor

    now = timezone.now()
    period = _match_period(now)
    if not period:
        return {"skipped": True, "reason": "非策略执行时段"}

    run_date = now.strftime("%Y-%m-%d")
    total = {"period": period, "executed": 0, "skipped": 0, "failed": 0}
    async for db in get_session():
        strategies = await StrategyService.get_enabled(db)
        for strategy in strategies:
            periods = strategy.execute_periods or []
            if period not in periods:
                continue
            # 同日同时段去重
            dup = await db.execute(
                select(BusinessStrategyRun.id).where(
                    BusinessStrategyRun.strategy_id == strategy.id,
                    BusinessStrategyRun.run_period == period,
                    BusinessStrategyRun.run_date == run_date,
                    BusinessStrategyRun.deleted_at.is_(None),
                ).limit(1)
            )
            if dup.scalar_one_or_none() is not None:
                total["skipped"] += 1
                continue
            result = await StrategyExecutor.run(db, strategy, run_period=period)
            if result.status:
                total["executed"] += 1
            else:
                total["failed"] += 1
    return total


@scheduled_task(
    cron="*/5 9-15 * * mon-fri",
    name="AI策略持仓跟踪",
    description="交易时段内每 5 分钟刷新策略持仓最新价/浮盈，触发止损/止盈/预估卖点自动平仓并计算收益率",
    task_key="strategy.position_track",
    is_system=True,
)
async def strategy_position_track():
    """交易时段内刷新全部策略持仓"""
    from database.db_manager import get_session
    from database.utils.timezone import timezone
    from modules.strategy.services.position_service import PositionService

    now = timezone.now()
    if not _in_trading_hours(now):
        return {"skipped": True, "reason": "非交易时段"}

    total = {"tracked": 0, "closed": 0}
    async for db in get_session():
        total = await PositionService.track_positions(db)
    return total
