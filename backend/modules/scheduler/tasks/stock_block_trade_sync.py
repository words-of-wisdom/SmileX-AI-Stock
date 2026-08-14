#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A股大宗交易（暗盘）定时任务
- 收盘后抓取当日大宗交易每日统计 + 活跃A股各窗口统计

注意：APScheduler 的星期字段 Monday=0，数字写法 "1-5" 实为周二至周六
（周六触发、跳过周一），周一到周五必须用 mon-fri。
"""
import logging

from modules.scheduler.core.registry import scheduled_task

logger = logging.getLogger(__name__)


@scheduled_task(
    cron="40 15 * * mon-fri",
    name="暗盘数据同步",
    description="收盘后抓取大宗交易每日统计与活跃A股统计并写入快照（源：东方财富/akshare）",
    task_key="stock.block_trade_sync",
    is_system=True,
)
async def block_trade_sync():
    """大宗交易（暗盘）同步入库"""
    from database.db_manager import get_session
    from modules.stock.services.block_trade_service import BlockTradeService

    async for db in get_session():
        return await BlockTradeService.sync_all(db)
