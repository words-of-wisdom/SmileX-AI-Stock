#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票热榜定时任务
每小时抓取所有热榜源入库当日快照（同日多次抓取靠联合唯一约束去重）
"""

from modules.scheduler.core.registry import scheduled_task


@scheduled_task(
    cron="0 * * * *",
    name="股票热榜抓取",
    description="每小时抓取东财/雪球/同花顺热榜并写入当日快照",
    task_key="stock_hot.sync_all",
    is_system=True,
)
async def stock_hot_sync_all():
    """股票热榜抓取入库"""
    from database.db_manager import get_session
    from modules.stock.services.stock_hot_service import StockHotService

    total = {"fetched": 0, "saved": 0, "failed_sources": []}
    async for db in get_session():
        total = await StockHotService.sync_all(db)
    return total
