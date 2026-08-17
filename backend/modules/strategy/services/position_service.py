#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
持仓服务：跟踪刷新、查询、手动平仓、跟踪日志、回报率统计
"""
import logging
from typing import Optional

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception.errors import CustomError
from core.response.response_code import CustomErrorCode
from database.models.business.strategy import (
    BusinessStrategyPosition,
    BusinessPositionTrackLog,
)
from database.utils.timezone import timezone
from modules.strategy.services.quote_helper import fetch_latest_prices
from modules.strategy.schemas.strategy import PositionItem, TrackLogItem, StrategyStatsItem

logger = logging.getLogger(__name__)


class PositionService:
    """策略持仓服务类"""

    # ------------------------------------------------------------------
    # 持仓跟踪（定时任务调用）
    # ------------------------------------------------------------------
    @staticmethod
    async def track_positions(db: AsyncSession) -> dict:
        """刷新全部持仓中个股的最新价/浮盈，触发止损/止盈/目标价自动平仓。

        返回：{tracked, closed, failed}
        """
        now = timezone.now()
        result = await db.execute(
            select(BusinessStrategyPosition).where(
                BusinessStrategyPosition.status == "holding",
                BusinessStrategyPosition.deleted_at.is_(None),
            )
        )
        positions = list(result.scalars().all())
        if not positions:
            return {"tracked": 0, "closed": 0}

        codes = list({p.stock_code for p in positions})
        prices = await fetch_latest_prices(codes)

        tracked = closed = 0
        for pos in positions:
            price = prices.get(pos.stock_code)
            if not price:
                # 停牌/接口缺失时仍写一条日志便于排查
                db.add(BusinessPositionTrackLog(
                    position_id=pos.id, track_time=now,
                    latest_price=pos.latest_price, pnl_pct=pos.floating_pnl_pct,
                ))
                continue

            buy_price = float(pos.buy_price)
            pnl_pct = round((price - buy_price) / buy_price * 100, 4)
            pos.latest_price = price
            pos.floating_pnl_pct = pnl_pct
            pos.tracked_at = now
            tracked += 1

            # ---- 触发条件判断：止损 / 止盈 / 达到预估卖点 ----
            sell_reason = None
            if pos.stop_loss_price and price <= float(pos.stop_loss_price):
                sell_reason = "stop_loss"
            elif pos.target_sell_price and price >= float(pos.target_sell_price):
                sell_reason = "target_reached"

            if sell_reason:
                pos.status = "closed"
                pos.sell_price = price
                pos.sell_time = now
                pos.sell_reason = sell_reason
                pos.return_rate = pnl_pct
                closed += 1

            db.add(BusinessPositionTrackLog(
                position_id=pos.id, track_time=now,
                latest_price=price, pnl_pct=pnl_pct,
            ))

        await db.commit()
        logger.info("持仓跟踪完成: total=%d tracked=%d closed=%d",
                    len(positions), tracked, closed)
        return {"tracked": tracked, "closed": closed, "total": len(positions)}

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    @staticmethod
    async def get_positions(
        db: AsyncSession,
        strategy_id: Optional[int] = None,
        status: Optional[str] = None,
        stock_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PositionItem], int]:
        """分页查询持仓列表，holding 在前、按建仓时间倒序"""
        conditions = [BusinessStrategyPosition.deleted_at.is_(None)]
        if strategy_id:
            conditions.append(BusinessStrategyPosition.strategy_id == strategy_id)
        if status:
            conditions.append(BusinessStrategyPosition.status == status)
        if stock_code:
            conditions.append(BusinessStrategyPosition.stock_code.ilike(f"%{stock_code}%"))

        count_result = await db.execute(
            select(func.count()).select_from(BusinessStrategyPosition).where(*conditions)
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            select(BusinessStrategyPosition)
            .where(*conditions)
            .order_by(
                # holding 排前，其余按卖出时间/建仓时间倒序
                case((BusinessStrategyPosition.status == "holding", 0), else_=1),
                BusinessStrategyPosition.buy_time.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [PositionItem.model_validate(row) for row in result.scalars().all()]
        return items, total

    @staticmethod
    async def get_tracks(
        db: AsyncSession, position_id: int, limit: int = 100
    ) -> list[TrackLogItem]:
        """获取持仓跟踪日志（最新在前）"""
        result = await db.execute(
            select(BusinessPositionTrackLog)
            .where(
                BusinessPositionTrackLog.position_id == position_id,
                BusinessPositionTrackLog.deleted_at.is_(None),
            )
            .order_by(BusinessPositionTrackLog.track_time.desc())
            .limit(limit)
        )
        return [TrackLogItem.model_validate(row) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # 手动平仓
    # ------------------------------------------------------------------
    @staticmethod
    async def close_position(
        db: AsyncSession, position_id: int, price: Optional[float], reason: Optional[str]
    ) -> PositionItem:
        now = timezone.now()
        result = await db.execute(
            select(BusinessStrategyPosition).where(
                BusinessStrategyPosition.id == position_id,
                BusinessStrategyPosition.deleted_at.is_(None),
            )
        )
        pos = result.scalar_one_or_none()
        if not pos:
            raise CustomError(
                error=CustomErrorCode.POSITION_NOT_FOUND,
                msg=f"持仓 [{position_id}] 不存在",
            )
        if pos.status != "holding":
            raise CustomError(
                error=CustomErrorCode.POSITION_ALREADY_CLOSED,
                msg=f"持仓 [{pos.stock_name}] 已平仓",
            )

        sell_price = price
        if not sell_price:
            prices = await fetch_latest_prices([pos.stock_code])
            sell_price = prices.get(pos.stock_code) or pos.latest_price or float(pos.buy_price)

        buy_price = float(pos.buy_price)
        pos.status = "closed"
        pos.sell_price = sell_price
        pos.sell_time = now
        pos.sell_reason = "manual"
        pos.latest_price = sell_price
        pos.return_rate = round((sell_price - buy_price) / buy_price * 100, 4)
        pos.floating_pnl_pct = pos.return_rate
        await db.commit()
        await db.refresh(pos)
        return PositionItem.model_validate(pos)

    # ------------------------------------------------------------------
    # 回报率统计
    # ------------------------------------------------------------------
    @staticmethod
    async def get_stats(db: AsyncSession, strategy_id: Optional[int] = None) -> list[StrategyStatsItem]:
        """按策略维度统计回报率（strategy_id 为空时返回全部策略）"""
        from database.models.business.strategy import BusinessAiStrategy

        str_conditions = [BusinessAiStrategy.deleted_at.is_(None)]
        if strategy_id:
            str_conditions.append(BusinessAiStrategy.id == strategy_id)
        str_result = await db.execute(
            select(BusinessAiStrategy).where(*str_conditions).order_by(BusinessAiStrategy.id)
        )
        strategies = list(str_result.scalars().all())
        if not strategies:
            return []

        pos_conditions = [
            BusinessStrategyPosition.deleted_at.is_(None),
            BusinessStrategyPosition.strategy_id.in_([s.id for s in strategies]),
        ]
        pos_result = await db.execute(
            select(BusinessStrategyPosition).where(*pos_conditions)
        )
        positions = list(pos_result.scalars().all())

        stats: list[StrategyStatsItem] = []
        for s in strategies:
            own = [p for p in positions if p.strategy_id == s.id]
            holding = [p for p in own if p.status == "holding"]
            closed = [p for p in own if p.status == "closed" and p.return_rate is not None]
            returns = [float(p.return_rate) for p in closed]
            wins = [r for r in returns if r > 0]

            stats.append(StrategyStatsItem(
                strategy_id=s.id,
                strategy_name=s.name,
                holding_count=len(holding),
                closed_count=len(closed),
                win_count=len(wins),
                loss_count=len(returns) - len(wins),
                win_rate=round(len(wins) / len(returns) * 100, 4) if returns else None,
                total_return_rate=round(sum(returns), 4) if returns else None,
                avg_return_rate=round(sum(returns) / len(returns), 4) if returns else None,
                best_return_rate=max(returns) if returns else None,
                worst_return_rate=min(returns) if returns else None,
            ))
        return stats
