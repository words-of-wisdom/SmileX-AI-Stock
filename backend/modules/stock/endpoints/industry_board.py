#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
行业/概念板块接口
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from core.response import ResponseModel, response_base
from modules.admin.deps.auth.user_manager import current_user
from modules.admin.deps.auth.permission import require_permission
from modules.stock.services.board_service import BoardService
from modules.stock.schemas.industry_board import BoardDailyItem, BoardHistoryItem

logger = logging.getLogger(__name__)

board_router = APIRouter(prefix="/board", tags=["A股/行业板块"])


@board_router.post(
    "/sync",
    response_model=ResponseModel[dict],
    summary="手动触发板块数据同步",
    dependencies=[Depends(require_permission("stock:board:sync"))],
)
async def sync_board(
    board_type: str = Query("industry", description="板块类型: industry/concept"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """手动抓取行业/概念板块列表及资金流并写入当日快照"""
    result = await BoardService.sync_all(db, board_type)
    return response_base.success(data=result, msg="板块数据同步完成")


@board_router.get(
    "/list",
    response_model=ResponseModel[list[BoardDailyItem]],
    summary="获取板块列表",
    dependencies=[Depends(require_permission("stock:board:list"))],
)
async def get_board_list(
    board_type: str = Query("industry", description="板块类型: industry/concept"),
    date: str | None = Query(None, description="快照日期 YYYY-MM-DD，为空取最新"),
    sort_by: str = Query("change_pct", description="排序字段: change_pct/net_inflow"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取板块列表，支持按涨跌幅或资金净流入排序"""
    data = await BoardService.get_list(db, board_type, date, sort_by, sort_order)
    return response_base.success(data=data)


@board_router.get(
    "/history",
    response_model=ResponseModel[list[BoardHistoryItem]],
    summary="获取单板块历史趋势",
    dependencies=[Depends(require_permission("stock:board:list"))],
)
async def get_board_history(
    board_type: str = Query(..., description="板块类型: industry/concept"),
    board_code: str = Query(..., description="板块代码"),
    days: int = Query(30, ge=1, le=365, description="回看天数"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取单板块历史趋势"""
    data = await BoardService.get_history(db, board_type, board_code, days)
    return response_base.success(data=data)


@board_router.get(
    "/dates",
    response_model=ResponseModel[list[str]],
    summary="获取可回看日期列表",
    dependencies=[Depends(require_permission("stock:board:list"))],
)
async def get_board_dates(
    board_type: str = Query("industry", description="板块类型: industry/concept"),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取指定类型板块所有可回看的快照日期（降序）"""
    dates = await BoardService.get_dates(db, board_type)
    return response_base.success(data=[d.isoformat() for d in dates])
