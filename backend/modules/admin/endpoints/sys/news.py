#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻聚合相关接口
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from core.response import ResponseModel, ResponsePageModel, response_base
from modules.common.schemas.page import PageRequest, get_page_params, get_paginated_results
from modules.admin.deps.auth.user_manager import current_user
from modules.admin.deps.auth.permission import require_permission
from modules.admin.services.sys.news_service import NewsService
from modules.admin.schemas.sys.news import (
    NewsQueryParams,
    NewsResponse,
    NewsDetailResponse,
    NewsSourceItem,
)

logger = logging.getLogger(__name__)

news_router = APIRouter(prefix="/news", tags=["系统管理/资讯聚合"])


@news_router.get(
    "/list",
    response_model=ResponsePageModel[NewsResponse],
    summary="获取新闻列表",
    dependencies=[Depends(require_permission("sys:news:list"))],
)
async def get_news_list(
    query_params: NewsQueryParams = Depends(),
    page_params: PageRequest = Depends(get_page_params),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """分页查询新闻聚合列表，按发布时间倒序"""
    query = NewsService.build_news_query(query_params)
    page_data = await get_paginated_results(
        db=db,
        page_params=page_params,
        query=query,
        schema=NewsResponse,
    )
    return response_base.page(data=page_data)


@news_router.get(
    "/sources",
    response_model=ResponseModel[list[NewsSourceItem]],
    summary="获取新闻源统计",
    dependencies=[Depends(require_permission("sys:news:list"))],
)
async def get_news_sources(
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """按新闻源统计条数（供前端源侧栏展示）"""
    data = await NewsService.get_source_stats(db)
    return response_base.success(data=data)


@news_router.get(
    "/{news_id}",
    response_model=ResponseModel[NewsDetailResponse],
    summary="获取新闻详情",
    dependencies=[Depends(require_permission("sys:news:view"))],
)
async def get_news_detail(
    news_id: int,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """获取单条新闻详情"""
    news = await NewsService.get_news(db, news_id)
    return response_base.success(data=NewsDetailResponse.model_validate(news))
