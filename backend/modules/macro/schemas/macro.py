#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""宏观指数相关 Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MacroIndicatorItem(BaseModel):
    """宏观指标记录（序列点 / 最新值卡片共用）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    country: str
    indicator_code: str
    indicator_name: str
    period: str
    value: Optional[float] = None
    yoy: Optional[float] = None
    mom: Optional[float] = None
    unit: str = "%"
    source: Optional[str] = None
    released_at: Optional[datetime] = None


class MacroSyncResult(BaseModel):
    """手动同步结果"""

    sources: dict[str, int]
    saved: int
