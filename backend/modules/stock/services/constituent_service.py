#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
指数成分股服务：BaoStock 拉取沪深300/中证500 成分股 + 同步入库 + 查询
（蓝筹白马类 AI 策略的结构化选股池数据源）
"""
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.stock_market import BusinessIndexConstituent
from database.utils.timezone import timezone
from modules.stock.services._baostock import fetch_index_constituents

logger = logging.getLogger(__name__)


class ConstituentService:
    """指数成分股服务"""

    @staticmethod
    async def sync_all(db: AsyncSession) -> dict:
        """拉取沪深300/中证500 成分股并 UPSERT 入库，返回同步统计"""
        raw_items = await fetch_index_constituents()
        if not raw_items:
            return {"fetched": 0, "saved": 0}

        now = timezone.now()
        rows = []
        for it in raw_items:
            record_date = (
                date.fromisoformat(it["record_date"])
                if it.get("record_date") else now.date()
            )
            rows.append(
                {
                    "record_date": record_date,
                    "index_code": it["index_code"],
                    "index_name": it["index_name"],
                    "stock_code": it["stock_code"],
                    "stock_name": it["stock_name"],
                    "weight": it.get("weight"),
                    "created_at": now,
                }
            )

        stmt = insert(BusinessIndexConstituent).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["record_date", "index_code", "stock_code"],
            set_={
                "index_name": stmt.excluded.index_name,
                "stock_name": stmt.excluded.stock_name,
                "weight": stmt.excluded.weight,
                "updated_at": now,
            },
        )
        result = await db.execute(stmt)
        await db.commit()
        logger.info("指数成分股同步完成: %d 条", len(rows))
        return {"fetched": len(rows), "saved": result.rowcount or 0}

    @staticmethod
    async def get_list(
        db: AsyncSession,
        index_code: str = "000300",
        limit: int = 100,
    ) -> list[BusinessIndexConstituent]:
        """查询指定指数最新快照日的成分股列表（权重优先，无权重时按代码）"""
        # 先取该指数最新快照日
        latest_date = await db.execute(
            select(BusinessIndexConstituent.record_date)
            .where(
                BusinessIndexConstituent.index_code == index_code,
                BusinessIndexConstituent.deleted_at.is_(None),
            )
            .order_by(BusinessIndexConstituent.record_date.desc())
            .limit(1)
        )
        record_date = latest_date.scalar_one_or_none()
        if record_date is None:
            return []

        result = await db.execute(
            select(BusinessIndexConstituent)
            .where(
                BusinessIndexConstituent.index_code == index_code,
                BusinessIndexConstituent.record_date == record_date,
                BusinessIndexConstituent.deleted_at.is_(None),
            )
            # BaoStock 当前可能不返回权重，无权重时按代码稳定排序
            .order_by(
                BusinessIndexConstituent.weight.desc().nullslast(),
                BusinessIndexConstituent.stock_code,
            )
            .limit(limit)
        )
        return list(result.scalars().all())
