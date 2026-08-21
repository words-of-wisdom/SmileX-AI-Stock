#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 大盘/板块分析定时任务
1. analysis_auto_generate: 周一至周五 16:05 / 16:25（在指数 15:30 / 板块 15:31 / 涨停 15:35
   行情同步完成后）自动生成当日大盘与板块「收盘分析」；第二轮为失败补跑点，
   当日已有成功/执行中记录则跳过
2. analysis_morning_generate: 周一至周五 9:20 / 9:35 自动生成当日大盘与板块「早盘分析」
   （昨日收盘数据 + 近24小时资讯，侧重隔夜消息面与今日开盘前瞻；资讯由 news.sync_all
   每 5 分钟同步，无需额外排序依赖）；9:35 同样为失败补跑点

说明：与 strategy_run 相同的坑——APScheduler 星期字段 Monday=0，
数字 "1-5" 实为周二至周六，必须用 mon-fri。
"""

import logging

from core.exception.errors import CustomError
from modules.scheduler.core.registry import scheduled_task

logger = logging.getLogger(__name__)


async def _generate_for_types(session: str) -> dict:
    """依次生成 market/sector 指定时段的分析（submit_run 落库即返，LLM 在后台任务中进行）"""
    from sqlalchemy import select

    from database.db_manager import get_session
    from database.models.business.analysis import BusinessAnalysisRun
    from database.utils.timezone import timezone
    from modules.analysis.services.analysis_executor import AnalysisExecutor

    now = timezone.now()
    run_date = now.strftime("%Y-%m-%d")
    total = {"run_date": run_date, "session": session, "submitted": 0, "skipped": 0, "rejected": 0}
    async for db in get_session():
        for analysis_type in ("market", "sector"):
            # 同日同类型同时段去重：已有成功/执行中记录则跳过；
            # failed 不算——下个触发点（补跑点）可重新生成，避免当日一次失败导致全天缺报告
            dup = await db.execute(
                select(BusinessAnalysisRun.id).where(
                    BusinessAnalysisRun.analysis_type == analysis_type,
                    BusinessAnalysisRun.session == session,
                    BusinessAnalysisRun.run_date == run_date,
                    BusinessAnalysisRun.status.in_(("success", "running")),
                    BusinessAnalysisRun.deleted_at.is_(None),
                ).limit(1)
            )
            if dup.scalar_one_or_none() is not None:
                total["skipped"] += 1
                continue
            try:
                await AnalysisExecutor.submit_run(
                    db, analysis_type, trigger_type="schedule", session=session,
                )
                total["submitted"] += 1
            except CustomError:
                # 并发守卫：该类型同时段已有 running 记录（如手动触发正在进行）
                total["rejected"] += 1
    return total


@scheduled_task(
    cron="5,25 16 * * mon-fri",
    name="AI大盘板块收盘分析生成",
    description="收盘后行情数据同步完成时，自动生成当日大盘点评与板块轮动解读（结合近期资讯；16:25 为失败补跑点，同日同类型已有成功记录则跳过）",
    task_key="analysis.auto_generate",
    is_system=True,
)
async def analysis_auto_generate():
    """生成 market/sector 收盘分析（16:05）"""
    return await _generate_for_types("close")


@scheduled_task(
    cron="20,35 9 * * mon-fri",
    name="AI大盘板块早盘分析生成",
    description="交易日 9:20 竞价阶段，基于昨日收盘数据与近24小时资讯自动生成当日大盘与板块早盘前瞻（9:35 为失败补跑点，成功后跳过）",
    task_key="analysis.morning_generate",
    is_system=True,
)
async def analysis_morning_generate():
    """生成 market/sector 早盘分析（9:20）"""
    return await _generate_for_types("morning")
