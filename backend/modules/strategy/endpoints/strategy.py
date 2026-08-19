#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 分析策略相关接口
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from core.response import ResponseModel, ResponsePageDataModel, response_base
from modules.admin.deps.auth.user_manager import current_user
from modules.admin.deps.auth.permission import require_permission
from modules.strategy.services.strategy_service import StrategyService
from modules.strategy.services.strategy_executor import StrategyExecutor
from modules.strategy.services.position_service import PositionService
from modules.strategy.schemas.strategy import (
    StrategyCreateRequest,
    StrategyItem,
    StrategyRunSubmitResult,
    StrategyRunItem,
)

logger = logging.getLogger(__name__)

strategy_router = APIRouter(prefix="/strategies", tags=["AI助手/AI分析"])


def _page_data(records, page, page_size, total):
    return ResponsePageDataModel(
        records=records, page=page, page_size=page_size, total=total,
        total_pages=(total + page_size - 1) // page_size if page_size else 0,
    )


# ----------------------------------------------------------------------
# 策略管理
# ----------------------------------------------------------------------
@strategy_router.get(
    "",
    response_model=ResponseModel[ResponsePageDataModel[StrategyItem]],
    summary="分页获取策略列表",
    dependencies=[Depends(require_permission("strategy:manage"))],
)
async def get_strategy_list(
    name: str | None = Query(None, description="策略名称模糊查询"),
    status: bool | None = Query(None, description="状态过滤"),
    category: str | None = Query(None, description="策略分类过滤：pre_market_auction/noon/tail/blue_chip/general"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    items, total = await StrategyService.get_list(db, name, status, category, page, page_size)
    return response_base.success(data=_page_data(items, page, page_size, total))


@strategy_router.post(
    "",
    response_model=ResponseModel[StrategyItem],
    summary="创建策略",
    dependencies=[Depends(require_permission("strategy:manage"))],
)
async def create_strategy(
    req: StrategyCreateRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    item = await StrategyService.create(db, req)
    return response_base.success(data=item, msg="创建成功")


@strategy_router.put(
    "/{strategy_id}",
    response_model=ResponseModel[StrategyItem],
    summary="更新策略",
    dependencies=[Depends(require_permission("strategy:manage"))],
)
async def update_strategy(
    strategy_id: int,
    req: StrategyCreateRequest,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    item = await StrategyService.update(db, strategy_id, req)
    return response_base.success(data=item, msg="更新成功")


@strategy_router.delete(
    "/{strategy_id}",
    response_model=ResponseModel,
    summary="删除策略（软删除）",
    dependencies=[Depends(require_permission("strategy:manage"))],
)
async def delete_strategy(
    strategy_id: int,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    await StrategyService.delete(db, strategy_id)
    return response_base.success(msg="删除成功")


# ----------------------------------------------------------------------
# 策略执行
# ----------------------------------------------------------------------
@strategy_router.post(
    "/{strategy_id}/run",
    response_model=ResponseModel[StrategyRunSubmitResult],
    summary="手动触发一次策略执行（异步，立即返回）",
    dependencies=[Depends(require_permission("strategy:run"))],
)
async def run_strategy(
    strategy_id: int,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    """手动执行策略：创建执行记录后立即返回，LLM 分析在后台进行；
    产出的买卖信号由每分钟交易引擎按实时价执行模拟买卖"""
    strategy = await StrategyService.get_by_id(db, strategy_id)
    run_id = await StrategyExecutor.submit_run(db, strategy, run_period="manual", trigger_type="manual")
    return response_base.success(
        data=StrategyRunSubmitResult(run_id=run_id),
        msg="已提交执行，分析完成后信号将由交易引擎执行",
    )


@strategy_router.get(
    "/{strategy_id}/runs",
    response_model=ResponseModel[ResponsePageDataModel[StrategyRunItem]],
    summary="分页获取策略执行记录",
    dependencies=[Depends(require_permission("strategy:manage"))],
)
async def get_strategy_runs(
    strategy_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select, func
    from database.models.business.strategy import BusinessStrategyRun

    conditions = [
        BusinessStrategyRun.strategy_id == strategy_id,
        BusinessStrategyRun.deleted_at.is_(None),
    ]
    count_result = await db.execute(
        select(func.count()).select_from(BusinessStrategyRun).where(*conditions)
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(BusinessStrategyRun)
        .where(*conditions)
        .order_by(BusinessStrategyRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [StrategyRunItem.model_validate(row) for row in result.scalars().all()]
    return response_base.success(data=_page_data(items, page, page_size, total))
