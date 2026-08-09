#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻聚合定时任务
通过 @scheduled_task 装饰器注册，每 5 分钟抓取所有新闻源入库
"""

from modules.scheduler.core.registry import scheduled_task


@scheduled_task(
    cron="*/5 * * * *",
    name="新闻聚合抓取",
    description="每 5 分钟抓取 16 个新闻源并去重入库",
    task_key="news.sync_all",
    is_system=True,
)
async def news_sync_all():
    """新闻聚合抓取入库"""
    from database.db_manager import get_session
    from modules.admin.services.sys.news_sync_service import NewsSyncService

    total = {"fetched": 0, "saved": 0, "failed_sources": []}
    async for db in get_session():
        total = await NewsSyncService.sync_all(db)
    return total
