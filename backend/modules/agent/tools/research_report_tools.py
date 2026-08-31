"""
Agent 券商研报工具函数 —— 供 LLM 查询系统采集的个股研报与评级共识。

ResearchService 只提供查询原语，这里在工具层组装面向 LLM 的结果。
"""

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.research import BusinessResearchReport
from modules.agent.services.tool_registry import register_tool

logger = logging.getLogger(__name__)


def _norm_code(stock_code: str) -> str:
    import re

    digits = re.sub(r"\D", "", str(stock_code))
    return digits.zfill(6) if digits else ""


@register_tool(
    name="get_research_reports",
    description=(
        "获取个股近期券商研报列表（东财采集，含标题、机构、评级、盈利预测 EPS/PE、发布日期），"
        "按发布日期倒序。用于分析机构对某只股票的覆盖观点与盈利预测。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "6 位股票代码，如 600519",
            },
            "days": {
                "type": "integer",
                "description": "回看天数，默认 90，最大 365",
                "default": 90,
            },
            "limit": {
                "type": "integer",
                "description": "返回条目数，默认 10，最大 30",
                "default": 10,
            },
        },
        "required": ["stock_code"],
    },
)
async def get_research_reports(
    db: AsyncSession, stock_code: str, days: int = 90, limit: int = 10
) -> dict[str, Any]:
    """获取个股近期券商研报列表。"""
    code = _norm_code(stock_code)
    if not code:
        return {"items": [], "message": "股票代码非法"}
    days = max(1, min(int(days), 365))
    limit = max(1, min(int(limit), 30))
    since = date.today() - timedelta(days=days)

    result = await db.execute(
        select(BusinessResearchReport)
        .where(
            BusinessResearchReport.stock_code == code,
            BusinessResearchReport.deleted_at.is_(None),
            BusinessResearchReport.published_date >= since,
        )
        .order_by(BusinessResearchReport.published_date.desc().nulls_last())
        .limit(limit)
    )
    rows = result.scalars().all()
    if not rows:
        return {
            "items": [],
            "message": f"近 {days} 天无股票 {code} 的研报数据（可能未同步，建议换标的）",
        }
    return {
        "stock_code": code,
        "stock_name": rows[0].stock_name,
        "items": [
            {
                "title": row.title,
                "org_name": row.org_name,
                "rating": row.rating,
                "industry": row.industry,
                "forecast": row.forecast,
                "published_date": row.published_date.isoformat() if row.published_date else None,
            }
            for row in rows
        ],
    }


@register_tool(
    name="get_report_consensus",
    description=(
        "获取个股券商研报共识：近 N 天研报总数、评级分布（买入/增持/中性等各自数量）、"
        "覆盖机构数、最新几条评级时间线。用于快速判断机构对某股的观点倾向与关注度变化。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "6 位股票代码，如 600519",
            },
            "days": {
                "type": "integer",
                "description": "回看天数，默认 90，最大 365",
                "default": 90,
            },
        },
        "required": ["stock_code"],
    },
)
async def get_report_consensus(
    db: AsyncSession, stock_code: str, days: int = 90
) -> dict[str, Any]:
    """获取个股研报评级共识统计。"""
    code = _norm_code(stock_code)
    if not code:
        return {"message": "股票代码非法"}
    days = max(1, min(int(days), 365))
    since = date.today() - timedelta(days=days)
    base = [
        BusinessResearchReport.stock_code == code,
        BusinessResearchReport.deleted_at.is_(None),
        BusinessResearchReport.published_date >= since,
    ]

    rating_rows = await db.execute(
        select(BusinessResearchReport.rating, func.count())
        .where(*base, BusinessResearchReport.rating.isnot(None))
        .group_by(BusinessResearchReport.rating)
        .order_by(func.count().desc())
    )
    org_rows = await db.execute(
        select(func.count(func.distinct(BusinessResearchReport.org_name))).where(*base)
    )
    latest = await db.execute(
        select(BusinessResearchReport)
        .where(*base)
        .order_by(BusinessResearchReport.published_date.desc().nulls_last())
        .limit(5)
    )
    latest_rows = latest.scalars().all()
    if not latest_rows:
        return {
            "message": f"近 {days} 天无股票 {code} 的研报数据（可能未同步，建议换标的）"
        }
    rating_counts = rating_rows.all()  # Result 只能消费一次，先物化
    total = sum(r[1] for r in rating_counts)
    return {
        "stock_code": code,
        "stock_name": latest_rows[0].stock_name,
        "days": days,
        "report_count": total,
        "org_count": org_rows.scalar() or 0,
        "rating_distribution": {r[0]: r[1] for r in rating_counts},
        "latest_ratings": [
            {
                "date": row.published_date.isoformat() if row.published_date else None,
                "org_name": row.org_name,
                "rating": row.rating,
                "title": row.title,
            }
            for row in latest_rows
        ],
    }
