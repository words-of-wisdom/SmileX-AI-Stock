#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
宏观指数服务层
- sync_all: 抓取全部指标并 upsert 入库（定时每日一次 + 手动触发）
- get_series / get_latest: 查询接口（图表 + 最新值卡片）
"""
import logging

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.macro import BusinessMacroIndicator
from database.utils.timezone import timezone
from modules.macro.services import macro_fetcher

logger = logging.getLogger(__name__)

# 允许查询的指标代码白名单（同时用于错误校验）
INDICATOR_CODES = ("cpi", "ppi", "m0", "m1", "m2", "core_cpi")
COUNTRY_CODES = ("CN", "US")

# 每个指标默认保留的最近期次数（图表序列长度）
SERIES_LIMIT = 24


class MacroService:

    @staticmethod
    async def sync_all(db: AsyncSession) -> dict:
        """全量同步：抓取 → 按「国家×指标×期次」upsert，返回统计"""
        data = await macro_fetcher.fetch_all()
        now = timezone.now()
        saved = 0
        for source, items in data.items():
            for it in items:
                result = await db.execute(
                    select(BusinessMacroIndicator.id).where(
                        BusinessMacroIndicator.country == it["country"],
                        BusinessMacroIndicator.indicator_code == it["indicator_code"],
                        BusinessMacroIndicator.period == it["period"],
                        BusinessMacroIndicator.deleted_at.is_(None),
                    ).limit(1)
                )
                existing_id = result.scalar_one_or_none()
                values = {
                    "indicator_name": it["indicator_name"],
                    "value": it["value"],
                    "yoy": it["yoy"],
                    "mom": it["mom"],
                    "unit": it["unit"],
                    "source": it["source"],
                    "released_at": now,
                }
                if existing_id is not None:
                    await db.execute(
                        BusinessMacroIndicator.__table__.update()
                        .where(BusinessMacroIndicator.id == existing_id)
                        .values(**values)
                    )
                else:
                    db.add(BusinessMacroIndicator(
                        country=it["country"],
                        indicator_code=it["indicator_code"],
                        period=it["period"],
                        **values,
                    ))
                saved += 1
        await db.commit()
        stats = {k: len(v) for k, v in data.items()}
        logger.info("宏观指标同步完成: %s saved=%s", stats, saved)
        return {"sources": stats, "saved": saved}

    @staticmethod
    async def get_series(
        db: AsyncSession,
        country: str = "CN",
        indicator: str = "cpi",
        limit: int = SERIES_LIMIT,
    ) -> list[BusinessMacroIndicator]:
        """按国家×指标取最近 N 期序列（period 升序，供图表直接使用）"""
        # 先取最近 N 期（倒序），再翻转为升序
        result = await db.execute(
            select(BusinessMacroIndicator)
            .where(
                BusinessMacroIndicator.country == country,
                BusinessMacroIndicator.indicator_code == indicator,
                BusinessMacroIndicator.deleted_at.is_(None),
            )
            .order_by(desc(BusinessMacroIndicator.period))
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    @staticmethod
    async def get_latest(db: AsyncSession) -> list[BusinessMacroIndicator]:
        """每个「国家×指标」的最新一期（卡片展示用）"""
        latest_sq = (
            select(
                BusinessMacroIndicator.country,
                BusinessMacroIndicator.indicator_code,
                func.max(BusinessMacroIndicator.period).label("max_period"),
            )
            .where(BusinessMacroIndicator.deleted_at.is_(None))
            .group_by(BusinessMacroIndicator.country, BusinessMacroIndicator.indicator_code)
            .subquery()
        )
        result = await db.execute(
            select(BusinessMacroIndicator)
            .join(
                latest_sq,
                (BusinessMacroIndicator.country == latest_sq.c.country)
                & (BusinessMacroIndicator.indicator_code == latest_sq.c.indicator_code)
                & (BusinessMacroIndicator.period == latest_sq.c.max_period),
            )
            .where(BusinessMacroIndicator.deleted_at.is_(None))
            .order_by(BusinessMacroIndicator.country, BusinessMacroIndicator.indicator_code)
        )
        return list(result.scalars().all())
