#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票热榜定时任务
开盘时间（周一至周五 09:30-11:30、13:00-15:00）内每 5 分钟抓取所有热榜源，
入库当日快照（同日多次抓取靠联合唯一约束去重）

说明：单条 cron 无法精确表达跨小时的分钟边界，故 cron 放宽到
周一至周五 9-15 点每 5 分钟触发，任务内再按 A 股连续竞价时段判断，
非交易时段直接跳过。注意 APScheduler 的星期字段 Monday=0，
数字写法 "1-5" 实为周二至周六，必须用 mon-fri。
"""

import logging
from datetime import datetime, time as dt_time

from modules.scheduler.core.registry import scheduled_task

logger = logging.getLogger(__name__)

# A 股连续竞价时段（本地时区，Asia/Shanghai）；
# 下午延到 15:05，让收盘后最后一轮同步（cron */5 会在 15:05 触发）
# 拿到定型的收盘价/收盘榜单
_TRADING_WINDOWS: tuple[tuple[dt_time, dt_time], ...] = (
    (dt_time(9, 30), dt_time(11, 30)),
    (dt_time(13, 0), dt_time(15, 5)),
)


def _in_trading_hours(now: datetime) -> bool:
    """判断当前是否处于 A 股连续竞价时段（周一至周五）"""
    if now.weekday() >= 5:
        return False
    current = now.time()
    return any(start <= current <= end for start, end in _TRADING_WINDOWS)


@scheduled_task(
    cron="*/5 9-15 * * mon-fri",
    name="股票热榜抓取",
    description="开盘时间（9:30-11:30、13:00-15:00）内每 5 分钟抓取东财/雪球/同花顺热榜并写入当日快照",
    task_key="stock_hot.sync_all",
    is_system=True,
)
async def stock_hot_sync_all():
    """股票热榜抓取入库，非交易时段直接跳过"""
    from database.db_manager import get_session
    from database.utils.timezone import timezone
    from modules.stock.services.stock_hot_service import StockHotService

    now = timezone.now()
    if not _in_trading_hours(now):
        logger.debug("当前 %s 非交易时段，跳过热榜抓取", now.strftime("%Y-%m-%d %H:%M"))
        return {"skipped": True, "reason": "非交易时段"}

    total = {"fetched": 0, "saved": 0, "failed_sources": []}
    async for db in get_session():
        total = await StockHotService.sync_all(db)
    return total
