#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻聚合读服务
"""
import logging
from datetime import datetime
from datetime import timezone as datetime_timezone

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.news import BusinessNews
from database.utils.timezone import timezone
from core.exception.errors import NotFoundError
from core.i18n import t
from modules.admin.schemas.sys.news import NewsQueryParams, NewsSourceItem
from modules.admin.services.sys.news_fetcher import NEWS_SOURCES

logger = logging.getLogger(__name__)


class NewsService:
    """新闻聚合管理服务类"""

    @staticmethod
    def build_news_query(query: NewsQueryParams):
        """构建新闻分页查询"""
        conditions = [BusinessNews.deleted_at.is_(None)]

        if query.keyword:
            conditions.append(BusinessNews.title.like(f"%{query.keyword}%"))
        if query.source:
            conditions.append(BusinessNews.source == query.source)
        elif query.group:
            source_keys = [s["key"] for s in NEWS_SOURCES if s.get("group") == query.group]
            if source_keys:
                conditions.append(BusinessNews.source.in_(source_keys))
        if query.start_time:
            try:
                dt = datetime.fromisoformat(query.start_time)
                start = dt.astimezone(datetime_timezone.utc) if dt.tzinfo else dt.replace(tzinfo=datetime_timezone.utc)
                conditions.append(BusinessNews.published_at >= start)
            except ValueError:
                pass
        if query.end_time:
            try:
                dt = datetime.fromisoformat(query.end_time)
                end = dt.astimezone(datetime_timezone.utc) if dt.tzinfo else dt.replace(tzinfo=datetime_timezone.utc)
                conditions.append(BusinessNews.published_at <= end)
            except ValueError:
                pass

        # 始终按标题去重：row_number 取每组最优行（优先 published_at 非空 + 最新 id）
        rn = func.row_number().over(
            partition_by=BusinessNews.title,
            order_by=[BusinessNews.published_at.desc().nullslast(), BusinessNews.id.desc()],
        ).label('rn')
        best_ids = (
            select(BusinessNews.id)
            .add_columns(rn)
            .where(and_(*conditions))
            .subquery()
        )
        base_query = (
            select(BusinessNews)
            .where(BusinessNews.id.in_(select(best_ids.c.id).where(best_ids.c.rn == 1)))
        )
        base_query = base_query.order_by(BusinessNews.published_at.desc().nullslast())
        return base_query

    @staticmethod
    async def get_news(db: AsyncSession, news_id: int) -> BusinessNews:
        """获取单条新闻详情"""
        result = await db.execute(
            select(BusinessNews).where(
                BusinessNews.id == news_id,
                BusinessNews.deleted_at.is_(None),
            )
        )
        news = result.scalar_one_or_none()
        if not news:
            raise NotFoundError(msg=t("error.news.not_found", id=news_id))
        return news

    @staticmethod
    async def get_source_stats(db: AsyncSession) -> list[NewsSourceItem]:
        """按源统计新闻数量，以注册表为准（无数据的源也展示 count=0）"""
        result = await db.execute(
            select(
                BusinessNews.source,
                func.count(BusinessNews.id).label("cnt"),
            )
            .where(
                BusinessNews.deleted_at.is_(None),
            )
            .group_by(BusinessNews.source)
        )
        counts = {row.source: row.cnt for row in result.all()}
        return [
            NewsSourceItem(
                source=s["key"],
                source_name=s["name"],
                group=s.get("group", ""),
                count=counts.get(s["key"], 0),
            )
            for s in NEWS_SOURCES
        ]
