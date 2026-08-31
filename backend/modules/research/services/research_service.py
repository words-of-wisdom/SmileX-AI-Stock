#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
券商研报服务层
- sync_reports: 抓取个股研报并按 url upsert（手动/定时共用）
- list_reports: 分页列表（筛选：股票/机构/评级/日期区间）
- get_stats: 概览统计（近30天研报数、评级分布、热门股票/机构 TOP）
- collect_sync_codes: 定时任务收集待同步标的（持仓+近30天信号+热门股）
"""
import logging
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.research import BusinessResearchReport
from database.utils.timezone import timezone
from modules.research.services import research_fetcher
from modules.research.services.research_fetcher import _norm_code

logger = logging.getLogger(__name__)

# 定时同步兜底热门股池（研报覆盖密集的权重标的，防库空）
FALLBACK_CODES = [
    "600519", "000858", "601318", "600036", "300750",
    "600276", "000333", "601899", "002594", "600900",
]


class ResearchService:

    @staticmethod
    async def sync_reports(db: AsyncSession, stock_code: str) -> int:
        """抓取个股研报并 upsert（按 url 去重），返回入库条数"""
        code = _norm_code(stock_code)
        if not code:
            return 0
        items = await research_fetcher.fetch_research_reports(code)
        now = timezone.now()
        saved = 0
        for it in items:
            result = await db.execute(
                select(BusinessResearchReport.id).where(
                    BusinessResearchReport.url == it["url"],
                    BusinessResearchReport.deleted_at.is_(None),
                ).limit(1)
            )
            existing_id = result.scalar_one_or_none()
            values = {
                "stock_code": it["stock_code"],
                "stock_name": it["stock_name"],
                "published_date": (
                    date.fromisoformat(it["published_date"]) if it["published_date"] else None
                ),
                "title": it["title"],
                "org_name": it["org_name"],
                "rating": it["rating"],
                "industry": it["industry"],
                "forecast": it["forecast"],
                "fetched_at": now,
            }
            if existing_id is not None:
                await db.execute(
                    BusinessResearchReport.__table__.update()
                    .where(BusinessResearchReport.id == existing_id)
                    .values(**values)
                )
            else:
                db.add(BusinessResearchReport(url=it["url"], **values))
            saved += 1
        await db.commit()
        return saved

    @staticmethod
    async def sync_codes(db: AsyncSession, codes: list[str]) -> dict:
        """批量同步多只股票研报，返回 {codes, saved, failed}"""
        total = {"codes": len(codes), "saved": 0, "failed": 0}
        for raw in codes:
            try:
                total["saved"] += await ResearchService.sync_reports(db, raw)
            except Exception:  # noqa: BLE001
                total["failed"] += 1
                logger.warning("研报同步失败: %s", raw, exc_info=True)
        return total

    @staticmethod
    async def list_reports(
        db: AsyncSession,
        page: int = 1, page_size: int = 20,
        stock_code: str = None, keyword: str = None,
        org_name: str = None, rating: str = None,
        start_date: str = None, end_date: str = None,
    ):
        """分页研报列表（published_date 倒序），返回 (items, total)"""
        conditions = [BusinessResearchReport.deleted_at.is_(None)]
        if stock_code:
            conditions.append(BusinessResearchReport.stock_code == stock_code)
        if keyword:
            kw = f"%{keyword.strip()}%"
            conditions.append(BusinessResearchReport.title.ilike(kw))
        if org_name:
            conditions.append(BusinessResearchReport.org_name.ilike(f"%{org_name.strip()}%"))
        if rating:
            conditions.append(BusinessResearchReport.rating == rating)
        if start_date:
            conditions.append(BusinessResearchReport.published_date >= start_date)
        if end_date:
            conditions.append(BusinessResearchReport.published_date <= end_date)

        count_result = await db.execute(
            select(func.count()).select_from(BusinessResearchReport).where(*conditions)
        )
        total = count_result.scalar() or 0
        result = await db.execute(
            select(BusinessResearchReport)
            .where(*conditions)
            .order_by(BusinessResearchReport.published_date.desc().nulls_last())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def get_stats(db: AsyncSession, days: int = 30) -> dict:
        """研报概览统计：近 N 天研报数、评级分布、覆盖股票/机构数、热门股票/机构 TOP10"""
        since = (timezone.now() - timedelta(days=days)).date()
        base = [
            BusinessResearchReport.deleted_at.is_(None),
            BusinessResearchReport.published_date >= since,
        ]

        async def _count(*extra):
            cond = base + list(extra)
            r = await db.execute(
                select(func.count()).select_from(BusinessResearchReport).where(*cond)
            )
            return r.scalar() or 0

        total = await _count()
        stocks = await db.execute(
            select(func.count(func.distinct(BusinessResearchReport.stock_code))).where(*base)
        )
        orgs = await db.execute(
            select(func.count(func.distinct(BusinessResearchReport.org_name))).where(*base)
        )

        rating_rows = await db.execute(
            select(BusinessResearchReport.rating, func.count())
            .where(*base, BusinessResearchReport.rating.isnot(None))
            .group_by(BusinessResearchReport.rating)
            .order_by(func.count().desc())
        )

        async def _top(field, limit=10):
            rows = await db.execute(
                select(field, func.count())
                .where(*base, field.isnot(None))
                .group_by(field)
                .order_by(func.count().desc())
                .limit(limit)
            )
            return [{"name": r[0], "count": r[1]} for r in rows.all()]

        return {
            "days": days,
            "total": total,
            "stock_count": stocks.scalar() or 0,
            "org_count": orgs.scalar() or 0,
            "rating_distribution": [
                {"rating": r[0], "count": r[1]} for r in rating_rows.all()
            ],
            "hot_stocks": await _top(BusinessResearchReport.stock_code),
            "hot_orgs": await _top(BusinessResearchReport.org_name),
        }

    @staticmethod
    async def collect_sync_codes(db: AsyncSession) -> list[str]:
        """收集定时同步标的：持仓 + 近30天信号 + 库内已有研报的股票，空库时用兜底池"""
        from database.models.business.strategy import (
            BusinessStrategyPosition, BusinessStrategySignal,
        )

        result = await db.execute(
            select(BusinessStrategyPosition.stock_code).where(
                BusinessStrategyPosition.status == "holding",
                BusinessStrategyPosition.deleted_at.is_(None),
            ).distinct()
        )
        codes = {row[0] for row in result.all() if row[0]}
        result = await db.execute(
            select(BusinessStrategySignal.stock_code).where(
                BusinessStrategySignal.deleted_at.is_(None),
                BusinessStrategySignal.created_at >= timezone.now() - timedelta(days=30),
            ).distinct()
        )
        codes |= {row[0] for row in result.all() if row[0]}
        if not codes:
            return list(FALLBACK_CODES)
        # 控制单次同步规模（akshare 每只一次网络请求）
        return sorted(codes)[:30]
