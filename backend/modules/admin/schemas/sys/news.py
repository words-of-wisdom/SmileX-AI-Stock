#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from pydantic import Field

from modules.common.schemas.base import BaseEntity
from modules.common.schemas.page import PageRequest


class NewsQueryParams(PageRequest):
    """新闻列表查询参数"""

    keyword: str | None = Field(None, description="关键词（标题模糊匹配）")
    source: str | None = Field(None, description="新闻源 key")
    group: str | None = Field(None, description="来源分组（按组过滤）")
    start_time: str | None = Field(None, description="开始时间")
    end_time: str | None = Field(None, description="结束时间")


class NewsResponse(BaseEntity):
    """新闻列表项响应"""

    id: int
    title: str
    summary: str | None = None
    url: str
    source: str
    source_name: str
    author: str | None = None
    published_at: datetime | None = None
    created_at: datetime | None = None


class NewsDetailResponse(NewsResponse):
    """新闻详情响应"""

    content: str | None = None
    raw_time: str | None = None


class NewsSourceItem(BaseEntity):
    """新闻源统计项"""

    source: str
    source_name: str
    group: str = Field("", description="来源分组")
    count: int = Field(0, description="当日该来源条数")
