#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Baostock SDK 示例接口
"""
from fastapi import APIRouter, Depends, Query

from core.response import ResponseModel, response_base
from modules.admin.deps.auth.user_manager import current_user
from modules.demo.schemas.baostock import KlineItem
from modules.demo.services.baostock_service import BaostockDemoService

baostock_demo_router = APIRouter(prefix="/baostock", tags=["示例/Baostock"])


@baostock_demo_router.get(
    "/kline",
    response_model=ResponseModel[list[KlineItem]],
    summary="Baostock 示例：获取日 K 线数据",
)
async def get_kline(
    code: str = Query(..., description="证券代码，如 sh.600519"),
    days: int = Query(30, ge=1, le=365, description="回看天数"),
    user=Depends(current_user),
):
    """通过 baostock query_history_k_data_plus 获取日 K 线数据"""
    data = await BaostockDemoService.get_kline(code, days)
    return response_base.success(data=data)
