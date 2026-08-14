#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大宗交易（暗盘）相关接口
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from core.response import ResponseModel, response_base
from modules.admin.deps.auth.user_manager import current_user
from modules.admin.deps.auth.permission import require_permission
from modules.stock.services.block_trade_service import BlockTradeService
from modules.stock.services.block_trade_fetcher import ACTIVE_WINDOWS
from modules.stock.schemas.block_trade import (
    BlockTradeDailyItem,
    BlockTradeActiveItem,
    BlockTradeSourceItem,
    BlockTradeHistoryItem,
)

logger = logging.getLogger(__name__)

block_trade_router = APIRouter(prefix="/block-trade", tags=["系统管理/暗盘跟踪"])


@block_trade_router.post(
    "/sync",
    response_model=ResponseModel[dict],
    summary="手动触发暗盘数据抓取同步",
    dependencies=[Depends(require_permission("stock:block_trade:sync"))],
)
async def sync_block_trade(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """手动触发全部暗盘子榜抓取（每日统计 + 活跃A股各窗口）并写入快照"""
    result = await BlockTradeService.sync_all(db)
    return response_base.success(data=result, msg="暗盘数据同步完成")


@block_trade_router.get(
    "/sources",
    response_model=ResponseModel[list[BlockTradeSourceItem]],
    summary="获取暗盘子榜概览",
    dependencies=[Depends(require_permission("stock:block_trade:list"))],
)
async def get_block_trade_sources(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取所有暗盘子榜（每日统计 + 活跃A股各窗口）及其最新统计"""
    data = await BlockTradeService.get_sources(db)
    return response_base.success(data=data)


@block_trade_router.get(
    "/daily-list",
    response_model=ResponseModel[list[BlockTradeDailyItem]],
    summary="获取每日统计榜单",
    dependencies=[Depends(require_permission("stock:block_trade:list"))],
)
async def get_block_trade_daily_list(
    date: str | None = Query(None, description="快照日期 YYYY-MM-DD，为空取最新"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取大宗交易每日统计榜单（按占流通市值比排名，含排名变化）"""
    data = await BlockTradeService.get_daily_list(db, date)
    return response_base.success(data=data)


@block_trade_router.get(
    "/active-list",
    response_model=ResponseModel[list[BlockTradeActiveItem]],
    summary="获取活跃A股榜单",
    dependencies=[Depends(require_permission("stock:block_trade:list"))],
)
async def get_block_trade_active_list(
    stat_window: str = Query("近一月", description=f"统计窗口：{ACTIVE_WINDOWS}"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取大宗交易活跃A股榜单（按上榜次数排名）"""
    data = await BlockTradeService.get_active_list(db, stat_window)
    return response_base.success(data=data)


@block_trade_router.get(
    "/dates",
    response_model=ResponseModel[list[str]],
    summary="获取可回看日期列表",
    dependencies=[Depends(require_permission("stock:block_trade:list"))],
)
async def get_block_trade_dates(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取每日统计所有可回看的快照日期（降序）"""
    dates = await BlockTradeService.get_dates(db)
    return response_base.success(data=[d.isoformat() for d in dates])


@block_trade_router.get(
    "/history",
    response_model=ResponseModel[list[BlockTradeHistoryItem]],
    summary="获取单股排名趋势",
    dependencies=[Depends(require_permission("stock:block_trade:view"))],
)
async def get_block_trade_history(
    stock_code: str = Query(..., description="股票代码"),
    days: int = Query(30, ge=1, le=365, description="回看天数"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取单股历史排名趋势（按占流通市值比在当日全部个股中的排名）"""
    data = await BlockTradeService.get_history(db, stock_code, days)
    return response_base.success(data=data)
