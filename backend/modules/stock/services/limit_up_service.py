#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
涨停股池服务：同步入库 + 查询
"""
import logging
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.stock_market import BusinessLimitUpStock
from database.utils.timezone import timezone
from modules.stock.schemas.limit_up import LimitUpStockItem, LimitUpStats
from modules.stock.services import limit_up_fetcher

logger = logging.getLogger(__name__)


class LimitUpService:
    """涨停股池服务"""

    @staticmethod
    async def sync_all(db: AsyncSession) -> dict:
        """抓取当日涨停股池并写入快照"""
        today = timezone.now().date()
        trade_date = today.strftime("%Y%m%d")
        raw_items = await limit_up_fetcher.fetch_limit_up_pool(trade_date)
        if not raw_items:
            return {"fetched": 0, "saved": 0}

        rows = [
            {
                "record_date": today,
                "stock_code": it["stock_code"],
                "stock_name": it["stock_name"],
                "market_board": it["market_board"],
                "latest_price": it.get("latest_price"),
                "change_pct": it.get("change_pct"),
                "turnover_rate": it.get("turnover_rate"),
                "turnover": it.get("turnover"),
                "amplitude": it.get("amplitude"),
                "seal_amount": it.get("seal_amount"),
                "first_limit_up_time": it.get("first_limit_up_time"),
                "last_limit_up_time": it.get("last_limit_up_time"),
                "break_count": it.get("break_count"),
                "consecutive_limit_up": it.get("consecutive_limit_up"),
                "industry": it.get("industry"),
                "limit_up_reason": it.get("limit_up_reason"),
                "created_at": timezone.now(),
            }
            for it in raw_items
        ]

        stmt = insert(BusinessLimitUpStock).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["record_date", "stock_code"],
            set_={
                "stock_name": stmt.excluded.stock_name,
                "market_board": stmt.excluded.market_board,
                "latest_price": stmt.excluded.latest_price,
                "change_pct": stmt.excluded.change_pct,
                "turnover_rate": stmt.excluded.turnover_rate,
                "turnover": stmt.excluded.turnover,
                "amplitude": stmt.excluded.amplitude,
                "seal_amount": stmt.excluded.seal_amount,
                "first_limit_up_time": stmt.excluded.first_limit_up_time,
                "last_limit_up_time": stmt.excluded.last_limit_up_time,
                "break_count": stmt.excluded.break_count,
                "consecutive_limit_up": stmt.excluded.consecutive_limit_up,
                "industry": stmt.excluded.industry,
                "limit_up_reason": stmt.excluded.limit_up_reason,
                "updated_at": timezone.now(),
            },
        )
        result = await db.execute(stmt)
        await db.commit()

        return {"fetched": len(raw_items), "saved": result.rowcount or 0}

    @staticmethod
    async def _resolve_date(db: AsyncSession, record_date: str | None) -> date | None:
        if record_date:
            return date.fromisoformat(record_date)
        latest = await db.execute(
            select(BusinessLimitUpStock.record_date)
            .where(BusinessLimitUpStock.deleted_at.is_(None))
            .distinct()
            .order_by(BusinessLimitUpStock.record_date.desc())
            .limit(1)
        )
        return latest.scalar_one_or_none()

    @staticmethod
    async def get_list(
        db: AsyncSession,
        record_date: str | None = None,
        market_board: str = "all",
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[LimitUpStockItem], int]:
        """获取涨停股列表（分页），返回 (items, total)"""
        target_date = await LimitUpService._resolve_date(db, record_date)
        if not target_date:
            return [], 0

        base = select(BusinessLimitUpStock).where(
            BusinessLimitUpStock.record_date == target_date,
            BusinessLimitUpStock.deleted_at.is_(None),
        )
        if market_board != "all":
            base = base.where(BusinessLimitUpStock.market_board == market_board)

        # 按连板数降序，其次按成交额降序
        base = base.order_by(
            BusinessLimitUpStock.consecutive_limit_up.desc().nulls_last(),
            BusinessLimitUpStock.turnover.desc().nulls_last(),
        )

        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        data_q = base.offset(offset).limit(limit)
        result = await db.execute(data_q)
        items = [
            LimitUpStockItem.model_validate(row)
            for row in result.scalars().all()
        ]
        return items, total

    @staticmethod
    async def get_stats(
        db: AsyncSession, record_date: str | None = None
    ) -> LimitUpStats:
        """获取当日涨停统计"""
        target_date = await LimitUpService._resolve_date(db, record_date)
        if not target_date:
            return LimitUpStats()

        base = select(BusinessLimitUpStock).where(
            BusinessLimitUpStock.record_date == target_date,
            BusinessLimitUpStock.deleted_at.is_(None),
        )

        result = await db.execute(base)
        rows = result.scalars().all()

        stats = LimitUpStats(record_date=target_date, total_count=len(rows))
        board_dist: dict[str, int] = {}
        max_consec = 0
        for row in rows:
            board = row.market_board
            if board == "main":
                stats.main_count += 1
            elif board == "chinext":
                stats.chinext_count += 1
            elif board == "star":
                stats.star_count += 1
            elif board == "bse":
                stats.bse_count += 1

            consec = row.consecutive_limit_up or 1
            if consec > max_consec:
                max_consec = consec

            ind = row.industry or "未分类"
            board_dist[ind] = board_dist.get(ind, 0) + 1

        stats.max_consecutive = max_consec
        stats.board_distribution = board_dist
        return stats

    @staticmethod
    async def get_dates(db: AsyncSession) -> list[date]:
        """获取可回看日期列表"""
        result = await db.execute(
            select(BusinessLimitUpStock.record_date)
            .where(BusinessLimitUpStock.deleted_at.is_(None))
            .distinct()
            .order_by(BusinessLimitUpStock.record_date.desc())
        )
        return list(result.scalars().all())
