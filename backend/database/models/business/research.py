#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
券商研报表
- BusinessResearchReport: 个股券商研报快照（东财 stock_research_report_em，按 url 唯一去重）

注意：Base 为 MappedAsDataclass，必填字段必须放在可选字段之前。
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Date, DateTime, JSON, Index, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped

from database.models.base import Base


class BusinessResearchReport(Base):
    """券商研报表"""

    __table_args__ = (
        UniqueConstraint("url", name="uk_research_report_url"),
        Index("ix_research_report_code_date", "stock_code", "published_date"),
        {"comment": "券商研报表"},
    )

    stock_code: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="股票代码（6 位）",
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="研报标题",
    )
    url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="研报 PDF 链接（去重键）",
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="抓取时间",
    )
    stock_name: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default=None, comment="股票名称",
    )
    org_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, default=None, comment="券商机构名称",
    )
    rating: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, default=None, comment="评级（买入/增持/中性/减持等）",
    )
    industry: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default=None, comment="所属行业",
    )
    published_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, default=None, comment="研报发布日期",
    )
    forecast: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=None,
        comment="盈利预测：{年份: {eps, pe}}（东财预测收益/市盈率）",
    )
