#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
akshare SDK 示例接口
"""
from fastapi import APIRouter, Depends, Query

from core.response import ResponseModel, response_base
from modules.admin.deps.auth.user_manager import current_user
from modules.demo.schemas.akshare import StockInfoItem
from modules.demo.services.akshare_service import AkshareDemoService

akshare_demo_router = APIRouter(prefix="/akshare", tags=["示例/akshare"])


@akshare_demo_router.get(
    "/stock-info",
    response_model=ResponseModel[list[StockInfoItem]],
    summary="akshare 示例：获取个股基础信息",
)
async def get_stock_info(
    symbol: str = Query(..., description="6 位股票代码，如 600519"),
    user=Depends(current_user),
):
    """通过 akshare stock_individual_info_em 获取个股基础信息"""
    data = await AkshareDemoService.get_stock_info(symbol)
    return response_base.success(data=data)
