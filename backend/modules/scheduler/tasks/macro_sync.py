#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
宏观经济指标定时同步
每日 07:30 抓取中美 CPI/PPI/M1/M2 等指标 upsert 入库（宏观数据月度发布，日频足够）
"""

from modules.scheduler.core.registry import scheduled_task


@scheduled_task(
    cron="30 7 * * *",
    name="宏观指数同步",
    description="每日 07:30 抓取中美 CPI/PPI/M1/M2 等宏观指标并 upsert 入库",
    task_key="macro.sync_all",
    is_system=True,
)
async def macro_sync_all():
    """宏观指标同步入库"""
    from database.db_manager import get_session
    from modules.macro.services.macro_service import MacroService

    result = {}
    async for db in get_session():
        result = await MacroService.sync_all(db)
    return result
