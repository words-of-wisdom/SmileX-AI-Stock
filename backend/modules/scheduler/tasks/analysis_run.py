#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 大盘/板块分析定时任务
1. analysis_auto_generate: 周一至周五 16:05（在指数 15:30 / 板块 15:31 / 涨停 15:35
   行情同步完成后）自动生成当日大盘与板块 AI 分析，同日已有成功记录则跳过

说明：与 strategy_run 相同的坑——APScheduler 星期字段 Monday=0，
数字 "1-5" 实为周二至周六，必须用 mon-fri。
"""

import logging

from core.exception.errors import CustomError
from modules.scheduler.core.registry import scheduled_task

logger = logging.getLogger(__name__)


@scheduled_task(
    cron="5 16 * * mon-fri",
    name="AI大盘板块分析生成",
    description="收盘后行情数据同步完成时，自动生成当日大盘点评与板块轮动解读（同日同类型已有成功记录则跳过）",
    task_key="analysis.auto_generate",
    is_system=True,
)
async def analysis_auto_generate():
    """依次生成大盘/板块分析（submit_run 落库即返，LLM 在后台任务中进行）"""
    from sqlalchemy import select

    from database.db_manager import get_session
    from database.models.business.analysis import BusinessAnalysisRun
    from database.utils.timezone import timezone
    from modules.analysis.services.analysis_executor import AnalysisExecutor

    now = timezone.now()
    run_date = now.strftime("%Y-%m-%d")
    total = {"run_date": run_date, "submitted": 0, "skipped": 0, "rejected": 0}
    async for db in get_session():
        for analysis_type in ("market", "sector"):
            # 同日同类型去重：已有任意记录（含成功/执行中）则跳过
            dup = await db.execute(
                select(BusinessAnalysisRun.id).where(
                    BusinessAnalysisRun.analysis_type == analysis_type,
                    BusinessAnalysisRun.run_date == run_date,
                    BusinessAnalysisRun.deleted_at.is_(None),
                ).limit(1)
            )
            if dup.scalar_one_or_none() is not None:
                total["skipped"] += 1
                continue
            try:
                await AnalysisExecutor.submit_run(db, analysis_type, trigger_type="schedule")
                total["submitted"] += 1
            except CustomError:
                # 并发守卫：该类型已有 running 记录（如手动触发正在进行）
                total["rejected"] += 1
    return total
