#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""券商研报相关 Schema"""
from datetime import date, datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, BeforeValidator


def _norm_query_code(v) -> Optional[str]:
    """股票代码 query 参数：空串/非法归 None"""
    if not v or not isinstance(v, str):
        return None
    digits = "".join(ch for ch in v if ch.isdigit())
    return digits.zfill(6) if digits else None


def _norm_query_text(v) -> Optional[str]:
    """文本 query 参数：空串归 None"""
    if not v or not isinstance(v, str):
        return None
    v = v.strip()
    return v or None


def _norm_query_date(v) -> Optional[str]:
    """日期 query 参数：非 YYYY-MM-DD 归 None"""
    if not v or not isinstance(v, str):
        return None
    v = v.strip()
    try:
        return date.fromisoformat(v).isoformat()
    except ValueError:
        return None


StockCodeQuery = Annotated[Optional[str], BeforeValidator(_norm_query_code)]
TextQuery = Annotated[Optional[str], BeforeValidator(_norm_query_text)]
DateQuery = Annotated[Optional[str], BeforeValidator(_norm_query_date)]


class ResearchReportItem(BaseModel):
    """券商研报记录"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_code: str
    stock_name: Optional[str] = None
    title: str
    url: str
    org_name: Optional[str] = None
    rating: Optional[str] = None
    industry: Optional[str] = None
    forecast: Optional[dict] = None
    published_date: Optional[date] = None
    fetched_at: Optional[datetime] = None


class ResearchRatingCount(BaseModel):
    rating: str
    count: int


class ResearchNameCount(BaseModel):
    name: Optional[str] = None
    count: int


class ResearchStatsItem(BaseModel):
    """研报概览统计"""

    days: int
    total: int
    stock_count: int
    org_count: int
    rating_distribution: list[ResearchRatingCount] = []
    hot_stocks: list[ResearchNameCount] = []
    hot_orgs: list[ResearchNameCount] = []


class ResearchSyncBody(BaseModel):
    """手动同步请求体"""

    stock_codes: list[str] = []


class ResearchSyncResult(BaseModel):
    """同步结果"""

    codes: int
    saved: int
    failed: int
