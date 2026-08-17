#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
指数成分股定时同步任务
- 每交易日收盘后从 BaoStock 拉取沪深300/中证500 成分股快照
（蓝筹白马类 AI 策略的结构化选股池数据源）

注意：APScheduler 的星期字段 Monday=0，数字写法 "1-5" 实为周二至周六
（周六触发、跳过周一），周一到周五必须用 mon-fri。
"""
import logging

from modules.scheduler.core.registry import scheduled_task

logger = logging.getLogger(__name__)


@scheduled_task(
    cron="10 17 * * mon-fri",
    name="指数成分股同步",
    description="收盘后从 BaoStock 拉取沪深300/中证500 成分股并写入当日快照",
    task_key="stock.constituent_sync",
    is_system=True,
)
async def constituent_sync():
    """指数成分股同步入库"""
    from database.db_manager import get_session
    from modules.stock.services.constituent_service import ConstituentService

    async for db in get_session():
        return await ConstituentService.sync_all(db)
