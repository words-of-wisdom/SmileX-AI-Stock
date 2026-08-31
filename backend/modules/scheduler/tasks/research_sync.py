#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
券商研报定时同步任务
每 4 小时：同步持仓 + 近 30 天信号标的的券商研报（空库时同步兜底热门池）。
"""

from modules.scheduler.core.registry import scheduled_task


@scheduled_task(
    cron="0 */4 * * *",
    name="券商研报同步",
    description="每 4 小时同步持仓与近期信号标的的东财券商研报（按 PDF 链接去重 upsert）",
    task_key="research.sync_reports",
    is_system=True,
)
async def research_sync_reports():
    """券商研报定时同步"""
    from database.db_manager import get_session
    from modules.research.services.research_service import ResearchService

    result = {}
    async for db in get_session():
        codes = await ResearchService.collect_sync_codes(db)
        result = await ResearchService.sync_codes(db, codes)
    return result
