#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票热榜相关接口
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from core.response import ResponseModel, response_base
from modules.admin.deps.auth.user_manager import current_user
from modules.admin.deps.auth.permission import require_permission
from modules.stock.services.stock_hot_service import StockHotService
from modules.stock.schemas.stock_hot import (
    StockHotRankItem,
    StockHotSourceItem,
    StockHotHistoryItem,
)

logger = logging.getLogger(__name__)

stock_hot_router = APIRouter(prefix="/stock-hot", tags=["系统管理/股票热榜"])


@stock_hot_router.post(
    "/sync",
    response_model=ResponseModel[dict],
    summary="手动触发热榜抓取同步",
    dependencies=[Depends(require_permission("sys:stock_hot:sync"))],
)
async def sync_stock_hot(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """手动触发所有热榜源抓取并写入当日快照"""
    result = await StockHotService.sync_all(db)
    return response_base.success(data=result, msg="热榜同步完成")


@stock_hot_router.get(
    "/sources",
    response_model=ResponseModel[list[StockHotSourceItem]],
    summary="获取热榜源列表",
    dependencies=[Depends(require_permission("sys:stock_hot:list"))],
)
async def get_stock_hot_sources(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取所有热榜源及其最新快照统计"""
    data = await StockHotService.get_sources(db)
    return response_base.success(data=data)


@stock_hot_router.get(
    "/list",
    response_model=ResponseModel[list[StockHotRankItem]],
    summary="获取热榜排名列表",
    dependencies=[Depends(require_permission("sys:stock_hot:list"))],
)
async def get_stock_hot_list(
    source: str = Query(..., description="榜单源 key"),
    date: str | None = Query(None, description="快照日期 YYYY-MM-DD，为空取最新"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取指定源的热榜列表（含排名变化）"""
    data = await StockHotService.get_rank_list(db, source, date)
    return response_base.success(data=data)


@stock_hot_router.get(
    "/dates",
    response_model=ResponseModel[list[str]],
    summary="获取可回看日期列表",
    dependencies=[Depends(require_permission("sys:stock_hot:list"))],
)
async def get_stock_hot_dates(
    source: str = Query(..., description="榜单源 key"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取指定源所有可回看的快照日期（降序）"""
    dates = await StockHotService.get_dates(db, source)
    return response_base.success(data=[d.isoformat() for d in dates])


@stock_hot_router.get(
    "/history",
    response_model=ResponseModel[list[StockHotHistoryItem]],
    summary="获取单股排名趋势",
    dependencies=[Depends(require_permission("sys:stock_hot:view"))],
)
async def get_stock_hot_history(
    source: str = Query(..., description="榜单源 key"),
    stock_code: str = Query(..., description="股票代码"),
    days: int = Query(30, ge=1, le=365, description="回看天数"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取单股历史排名趋势"""
    data = await StockHotService.get_history(db, source, stock_code, days)
    return response_base.success(data=data)
