#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻聚合读服务
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.news import BusinessNews
from core.exception.errors import NotFoundError
from core.i18n import t
from modules.admin.schemas.sys.news import NewsQueryParams, NewsSourceItem

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
        if query.start_time:
            try:
                dt = datetime.fromisoformat(query.start_time)
                start = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                conditions.append(BusinessNews.published_at >= start)
            except ValueError:
                pass
        if query.end_time:
            try:
                dt = datetime.fromisoformat(query.end_time)
                end = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                conditions.append(BusinessNews.published_at <= end)
            except ValueError:
                pass

        base_query = select(BusinessNews).where(and_(*conditions))
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
        """按源统计新闻数量（供前端源侧栏展示）"""
        result = await db.execute(
            select(
                BusinessNews.source,
                func.max(BusinessNews.source_name).label("source_name"),
                func.count(BusinessNews.id).label("cnt"),
            )
            .where(BusinessNews.deleted_at.is_(None))
            .group_by(BusinessNews.source)
        )
        rows = result.all()
        return [
            NewsSourceItem(source=row.source, source_name=row.source_name, count=row.cnt)
            for row in rows
        ]
