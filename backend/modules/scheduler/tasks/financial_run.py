#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
企业财报自动解读定时任务
每日 08:00（工作日）：检查持仓 + 近30天策略信号标的，拉取最新披露财报，
对最新报告期尚无成功解读记录的个股自动提交 AI 解读（同报告期去重防重复解读）。
"""

from modules.scheduler.core.registry import scheduled_task


@scheduled_task(
    cron="0 8 * * mon-fri",
    name="持仓财报自动解读",
    description="工作日 08:00 对持仓与近期信号标的拉取最新财报并自动提交 AI 解读（最新报告期已有成功解读则跳过）",
    task_key="financial.auto_interpret",
    is_system=True,
)
async def financial_auto_interpret():
    """持仓标的财报自动解读"""
    from database.db_manager import get_session
    from modules.financial.services.financial_service import FinancialService

    result = {}
    async for db in get_session():
        # 先补抓财报（无财报的个股无法解读）
        result = await FinancialService.auto_interpret_holding_codes(db)
    return result
