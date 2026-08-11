#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
示例模块路由（SDK 简单调用演示）
"""
from fastapi import APIRouter

from .endpoints import akshare_demo_router, baostock_demo_router

router = APIRouter(prefix="/admin/demo")

router.include_router(akshare_demo_router)
router.include_router(baostock_demo_router)

__all__ = ["router"]
