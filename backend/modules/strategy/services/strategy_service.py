#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 分析策略 CRUD 服务
"""
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception.errors import CustomError
from core.response.response_code import CustomErrorCode
from database.models.business.strategy import BusinessAiStrategy
from modules.strategy.schemas.strategy import (
    EXECUTE_PERIODS,
    STRATEGY_CATEGORIES,
    StrategyCreateRequest,
    StrategyItem,
)

logger = logging.getLogger(__name__)


def _validate_periods(periods: list[str]) -> None:
    invalid = [p for p in periods if p not in EXECUTE_PERIODS]
    if invalid:
        raise CustomError(
            error=CustomErrorCode.STRATEGY_EXECUTE_FAILED,
            msg=f"不支持的执行时段: {invalid}，可选值: {list(EXECUTE_PERIODS)}",
        )


def _validate_category(category: str) -> None:
    if category not in STRATEGY_CATEGORIES:
        raise CustomError(
            error=CustomErrorCode.STRATEGY_EXECUTE_FAILED,
            msg=f"不支持的策略分类: {category}，可选值: {list(STRATEGY_CATEGORIES)}",
        )


class StrategyService:
    """AI 分析策略服务类"""

    @staticmethod
    async def get_by_id(db: AsyncSession, strategy_id: int) -> BusinessAiStrategy:
        result = await db.execute(
            select(BusinessAiStrategy).where(
                BusinessAiStrategy.id == strategy_id,
                BusinessAiStrategy.deleted_at.is_(None),
            )
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            raise CustomError(
                error=CustomErrorCode.STRATEGY_NOT_FOUND,
                msg=f"策略 [{strategy_id}] 不存在",
            )
        return strategy

    @staticmethod
    async def get_list(
        db: AsyncSession,
        name: str | None = None,
        status: bool | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StrategyItem], int]:
        """分页查询策略列表，返回 (items, total)"""
        conditions = [BusinessAiStrategy.deleted_at.is_(None)]
        if name:
            conditions.append(BusinessAiStrategy.name.ilike(f"%{name}%"))
        if status is not None:
            conditions.append(BusinessAiStrategy.status == status)
        if category:
            conditions.append(BusinessAiStrategy.category == category)

        count_result = await db.execute(
            select(func.count()).select_from(BusinessAiStrategy).where(*conditions)
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            select(BusinessAiStrategy)
            .where(*conditions)
            .order_by(BusinessAiStrategy.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [
            StrategyItem.model_validate(row) for row in result.scalars().all()
        ]
        return items, total

    @staticmethod
    async def get_enabled(db: AsyncSession) -> list[BusinessAiStrategy]:
        """获取全部启用策略（调度任务用）"""
        result = await db.execute(
            select(BusinessAiStrategy).where(
                BusinessAiStrategy.status == True,  # noqa: E712
                BusinessAiStrategy.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, req: StrategyCreateRequest) -> StrategyItem:
        _validate_periods(req.execute_periods)
        _validate_category(req.category)

        exist = await db.execute(
            select(BusinessAiStrategy.id).where(
                BusinessAiStrategy.name == req.name,
                BusinessAiStrategy.deleted_at.is_(None),
            )
        )
        if exist.scalar_one_or_none() is not None:
            raise CustomError(
                error=CustomErrorCode.STRATEGY_NAME_EXIST,
                msg=f"策略名称 [{req.name}] 已存在",
            )

        strategy = BusinessAiStrategy(
            name=req.name,
            description=req.description,
            category=req.category,
            prompt_template=req.prompt_template,
            stock_pool=req.stock_pool,
            execute_periods=req.execute_periods,
            max_positions=req.max_positions,
            stop_loss_pct=req.stop_loss_pct,
            take_profit_pct=req.take_profit_pct,
            status=req.status,
        )
        db.add(strategy)
        await db.commit()
        await db.refresh(strategy)
        return StrategyItem.model_validate(strategy)

    @staticmethod
    async def update(
        db: AsyncSession, strategy_id: int, req: StrategyCreateRequest
    ) -> StrategyItem:
        _validate_periods(req.execute_periods)
        _validate_category(req.category)
        strategy = await StrategyService.get_by_id(db, strategy_id)

        # 名称查重（排除自身）
        exist = await db.execute(
            select(BusinessAiStrategy.id).where(
                BusinessAiStrategy.name == req.name,
                BusinessAiStrategy.id != strategy_id,
                BusinessAiStrategy.deleted_at.is_(None),
            )
        )
        if exist.scalar_one_or_none() is not None:
            raise CustomError(
                error=CustomErrorCode.STRATEGY_NAME_EXIST,
                msg=f"策略名称 [{req.name}] 已存在",
            )

        strategy.name = req.name
        strategy.description = req.description
        strategy.category = req.category
        strategy.prompt_template = req.prompt_template
        strategy.stock_pool = req.stock_pool
        strategy.execute_periods = req.execute_periods
        strategy.max_positions = req.max_positions
        strategy.stop_loss_pct = req.stop_loss_pct
        strategy.take_profit_pct = req.take_profit_pct
        strategy.status = req.status
        await db.commit()
        await db.refresh(strategy)
        return StrategyItem.model_validate(strategy)

    @staticmethod
    async def delete(db: AsyncSession, strategy_id: int) -> None:
        strategy = await StrategyService.get_by_id(db, strategy_id)
        strategy.soft_delete()
        await db.commit()

    @staticmethod
    async def toggle_status(db: AsyncSession, strategy_id: int, status: bool) -> StrategyItem:
        strategy = await StrategyService.get_by_id(db, strategy_id)
        strategy.status = status
        await db.commit()
        await db.refresh(strategy)
        return StrategyItem.model_validate(strategy)
