#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 分析策略配置服务：大盘/板块每类型一条（prompt 定制 + 明日研判开关），
无记录时按默认策略处理（prompt 为空、明日研判开启）
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.analysis import BusinessAnalysisConfig
from database.utils.timezone import timezone
from modules.analysis.schemas.analysis import (
    AnalysisConfigItem,
    AnalysisConfigUpdateRequest,
)

logger = logging.getLogger(__name__)


class AnalysisConfigService:
    """分析策略配置服务"""

    @staticmethod
    async def get_config(
        db: AsyncSession, analysis_type: str
    ) -> BusinessAnalysisConfig | None:
        result = await db.execute(
            select(BusinessAnalysisConfig).where(
                BusinessAnalysisConfig.analysis_type == analysis_type,
                BusinessAnalysisConfig.deleted_at.is_(None),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_effective(db: AsyncSession, analysis_type: str) -> AnalysisConfigItem:
        """获取生效配置（无记录时返回默认值，data 始终非空）"""
        config = await AnalysisConfigService.get_config(db, analysis_type)
        if config is None:
            return AnalysisConfigItem(analysis_type=analysis_type)
        return AnalysisConfigItem.model_validate(config)

    @staticmethod
    async def update_config(
        db: AsyncSession, analysis_type: str, req: AnalysisConfigUpdateRequest
    ) -> AnalysisConfigItem:
        """保存配置（upsert：已有记录则更新，否则新建）"""
        config = await AnalysisConfigService.get_config(db, analysis_type)
        if config is None:
            config = BusinessAnalysisConfig(
                analysis_type=analysis_type,
                prompt_template=req.prompt_template,
                include_tomorrow=req.include_tomorrow,
            )
            db.add(config)
            logger.info("新建分析策略配置: type=%s", analysis_type)
        else:
            config.prompt_template = req.prompt_template
            config.include_tomorrow = req.include_tomorrow
            config.updated_at = timezone.now()
        await db.commit()
        # 直接从请求构造响应，避免 commit 后 ORM 属性过期引发的惰性刷新问题
        return AnalysisConfigItem(
            analysis_type=analysis_type,
            prompt_template=req.prompt_template,
            include_tomorrow=req.include_tomorrow,
        )
