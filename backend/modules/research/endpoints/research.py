#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""券商研报采集与查询相关接口"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from core.response import ResponseModel, ResponsePageDataModel, response_base
from core.response.response_code import CustomErrorCode
from core.exception.errors import CustomError
from modules.admin.deps.auth.user_manager import current_user
from modules.admin.deps.auth.permission import require_permission
from modules.research.services.research_service import ResearchService
from modules.research.schemas.research import (
    StockCodeQuery,
    TextQuery,
    DateQuery,
    ResearchReportItem,
    ResearchStatsItem,
    ResearchSyncBody,
    ResearchSyncResult,
)

logger = logging.getLogger(__name__)

research_router = APIRouter(prefix="", tags=["AI助手/研报中心"])


def _page_data(records, page, page_size, total):
    return ResponsePageDataModel(
        records=records, page=page, page_size=page_size, total=total,
        total_pages=(total + page_size - 1) // page_size if page_size else 0,
    )


@research_router.get(
    "/reports",
    response_model=ResponseModel[ResponsePageDataModel[ResearchReportItem]],
    summary="分页获取券商研报列表（可按股票/关键词/机构/评级/日期区间筛选）",
    dependencies=[Depends(require_permission("research:list"))],
)
async def get_research_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    stock_code: StockCodeQuery = None,
    keyword: TextQuery = None,
    org_name: TextQuery = None,
    rating: TextQuery = None,
    start_date: DateQuery = None,
    end_date: DateQuery = None,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    records, total = await ResearchService.list_reports(
        db, page=page, page_size=page_size,
        stock_code=stock_code, keyword=keyword, org_name=org_name,
        rating=rating, start_date=start_date, end_date=end_date,
    )
    items = [ResearchReportItem.model_validate(r) for r in records]
    return response_base.success(data=_page_data(items, page, page_size, total))


@research_router.get(
    "/reports/stats",
    response_model=ResponseModel[ResearchStatsItem],
    summary="获取研报概览统计（近 N 天研报数/评级分布/覆盖股票与机构数/热门 TOP）",
    dependencies=[Depends(require_permission("research:list"))],
)
async def get_research_stats(
    days: int = Query(30, ge=1, le=180),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    stats = await ResearchService.get_stats(db, days=days)
    return response_base.success(data=ResearchStatsItem.model_validate(stats))


@research_router.post(
    "/reports/sync",
    response_model=ResponseModel[ResearchSyncResult],
    summary="手动触发研报同步（不传 stock_codes 时自动同步持仓+近期信号标的，空库时用兜底热门池）",
    dependencies=[Depends(require_permission("research:sync"))],
)
async def sync_research_reports(
    body: ResearchSyncBody,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    codes = [c for c in (c.strip() for c in body.stock_codes) if c]
    if not codes:
        codes = await ResearchService.collect_sync_codes(db)
    if not codes:
        raise CustomError(
            error=CustomErrorCode.RESEARCH_SYNC_FAILED,
            msg="未找到可同步的股票标的",
        )
    result = await ResearchService.sync_codes(db, codes)
    return response_base.success(
        data=ResearchSyncResult(**result),
        msg=f"研报同步完成：{result['saved']} 条入库，{result['failed']} 只失败",
    )
