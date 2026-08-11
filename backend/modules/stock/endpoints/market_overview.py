#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大盘概览接口
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from core.response import ResponseModel, response_base
from modules.admin.deps.auth.user_manager import current_user
from modules.admin.deps.auth.permission import require_permission
from modules.stock.services.market_service import MarketService
from modules.stock.schemas.market_overview import (
    MarketIndexItem,
    MarketIndexHistoryItem,
    MarketIndexOption,
)

logger = logging.getLogger(__name__)

market_router = APIRouter(prefix="/market", tags=["A股/大盘概览"])


@market_router.post(
    "/sync",
    response_model=ResponseModel[dict],
    summary="手动触发大盘指数同步",
    dependencies=[Depends(require_permission("stock:market:sync"))],
)
async def sync_market(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """手动抓取主要指数实时行情并写入当日快照"""
    result = await MarketService.sync_all(db)
    return response_base.success(data=result, msg="大盘指数同步完成")


@market_router.get(
    "/indices",
    response_model=ResponseModel[list[MarketIndexItem]],
    summary="获取大盘指数列表",
    dependencies=[Depends(require_permission("stock:market:list"))],
)
async def get_indices(
    date: str | None = Query(None, description="快照日期 YYYY-MM-DD，为空取最新"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取主要指数列表（含涨跌幅、成交额等）"""
    data = await MarketService.get_indices(db, date)
    return response_base.success(data=data)


@market_router.get(
    "/indices/options",
    response_model=ResponseModel[list[MarketIndexOption]],
    summary="获取指数下拉选项",
    dependencies=[Depends(require_permission("stock:market:list"))],
)
async def get_index_options(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取所有已同步过的指数代码列表，供前端下拉选择"""
    data = await MarketService.get_index_options(db)
    return response_base.success(data=data)


@market_router.get(
    "/indices/history",
    response_model=ResponseModel[list[MarketIndexHistoryItem]],
    summary="获取单指数历史趋势",
    dependencies=[Depends(require_permission("stock:market:list"))],
)
async def get_index_history(
    index_code: str = Query(..., description="指数代码"),
    days: int = Query(90, ge=1, le=365, description="回看天数"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取单指数历史日线趋势"""
    data = await MarketService.get_history(db, index_code, days)
    return response_base.success(data=data)


@market_router.get(
    "/dates",
    response_model=ResponseModel[list[str]],
    summary="获取可回看日期列表",
    dependencies=[Depends(require_permission("stock:market:list"))],
)
async def get_market_dates(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取大盘指数所有可回看的快照日期（降序）"""
    dates = await MarketService.get_dates(db)
    return response_base.success(data=[d.isoformat() for d in dates])
