"""
Agent 新闻相关工具函数 —— 供 LLM 查询系统聚合的财经新闻。

NewsService 只提供 build_news_query()（返回未执行的 Select），
这里在工具层自行执行分页，避免改动现有 service。
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.news import BusinessNews
from modules.agent.services.tool_registry import register_tool

logger = logging.getLogger(__name__)


@register_tool(
    name="get_latest_news",
    description="获取最新的财经新闻列表（已按来源聚合、按发布时间倒序、标题去重），包含标题、摘要、来源、发布时间。用于了解最新市场资讯和消息面。",
    parameters={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "标题关键词过滤，留空则返回全部",
            },
            "limit": {
                "type": "integer",
                "description": "返回条目数，默认 10，最大 30",
                "default": 10,
            },
        },
    },
)
async def get_latest_news(
    db: AsyncSession, keyword: str = "", limit: int = 10
) -> dict[str, Any]:
    """获取最新财经新闻。"""
    limit = max(1, min(int(limit), 30))

    base = (
        select(BusinessNews)
        .where(BusinessNews.deleted_at.is_(None))
        .order_by(BusinessNews.published_at.desc().nulls_last())
    )
    if keyword:
        base = base.where(BusinessNews.title.contains(keyword))

    result = await db.execute(base.limit(limit))
    rows = result.scalars().all()
    if not rows:
        return {"items": [], "message": "当前无新闻数据"}

    return {
        "items": [
            {
                "title": row.title,
                "summary": row.summary,
                "source_name": row.source_name,
                "author": row.author,
                "published_at": row.published_at.strftime("%Y-%m-%d %H:%M")
                if row.published_at
                else None,
                "url": row.url,
            }
            for row in rows
        ],
    }
