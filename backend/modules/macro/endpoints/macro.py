#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""宏观经济指数相关接口"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from core.response import ResponseModel, response_base
from core.response.response_code import CustomErrorCode
from core.exception.errors import CustomError
from modules.admin.deps.auth.user_manager import current_user
from modules.admin.deps.auth.permission import require_permission
from modules.macro.services.macro_service import MacroService, INDICATOR_CODES, COUNTRY_CODES
from modules.macro.schemas.macro import MacroIndicatorItem, MacroSyncResult

logger = logging.getLogger(__name__)

macro_router = APIRouter(prefix="", tags=["AI助手/宏观指数"])


def _validate_query(country: str, indicator: str) -> None:
    if country not in COUNTRY_CODES or indicator not in INDICATOR_CODES:
        raise CustomError(
            error=CustomErrorCode.MACRO_INDICATOR_INVALID,
            msg=f"国家仅支持 {'/'.join(COUNTRY_CODES)}，指标仅支持 {'/'.join(INDICATOR_CODES)}",
        )


@macro_router.get(
    "/indicators",
    response_model=ResponseModel[list[MacroIndicatorItem]],
    summary="获取宏观指标历史序列（最近 N 期，period 升序，供图表）",
    dependencies=[Depends(require_permission("macro:list"))],
)
async def get_macro_series(
    country: str = Query("CN", description="国家：CN-中国，US-美国"),
    indicator: str = Query("cpi", description="指标：cpi/ppi/m0/m1/m2"),
    limit: int = Query(24, ge=1, le=120),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    _validate_query(country, indicator)
    rows = await MacroService.get_series(db, country, indicator, limit)
    return response_base.success(data=[MacroIndicatorItem.model_validate(r) for r in rows])


@macro_router.get(
    "/indicators/latest",
    response_model=ResponseModel[list[MacroIndicatorItem]],
    summary="获取全部指标最新一期（卡片展示用）",
    dependencies=[Depends(require_permission("macro:list"))],
)
async def get_macro_latest(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    rows = await MacroService.get_latest(db)
    return response_base.success(data=[MacroIndicatorItem.model_validate(r) for r in rows])


@macro_router.post(
    "/sync",
    response_model=ResponseModel[MacroSyncResult],
    summary="手动触发宏观指标同步（akshare 抓取 + upsert）",
    dependencies=[Depends(require_permission("macro:sync"))],
)
async def sync_macro(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await MacroService.sync_all(db)
    return response_base.success(data=MacroSyncResult(**result), msg="同步完成")
