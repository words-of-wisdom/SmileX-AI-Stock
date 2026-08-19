#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 大盘/板块分析表
- BusinessAnalysisRun: 分析执行记录（submit_run 落库即返，LLM 在后台任务中生成，
  结果为 markdown 报告原文 + 结构化摘要，支持历史回看）
- BusinessAnalysisConfig: 分析策略配置（大盘/板块每类型一条：策略提示词 + 明日研判开关）
"""

from typing import Optional

from sqlalchemy import String, Text, Boolean, JSON, Index
from sqlalchemy.orm import mapped_column, Mapped

from database.models.base import Base


class BusinessAnalysisRun(Base):
    """AI 分析执行记录表"""

    __table_args__ = (
        Index("ix_analysis_run_type_created", "analysis_type", "created_at"),
        Index("ix_analysis_run_type_date", "analysis_type", "run_date"),
        {"comment": "AI 分析执行记录表"},
    )

    analysis_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="分析类型：market-大盘分析，sector-板块分析",
    )
    run_date: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="执行日期 YYYY-MM-DD（定时任务同日去重用）"
    )
    trigger_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="schedule",
        comment="触发方式：schedule-定时，manual-手动",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running",
        comment="执行状态：running-执行中，success-成功，failed-失败",
    )
    ai_raw_response: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None, comment="AI 分析报告原文（markdown）"
    )
    parsed_result: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=None,
        comment="结构化摘要：大盘{sentiment,score,summary,key_points}；板块{hot_boards,rotation_summary,key_points}",
    )
    error_msg: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None, comment="错误信息"
    )


class BusinessAnalysisConfig(Base):
    """AI 分析策略配置表（大盘/板块每类型一条）"""

    __table_args__ = (
        Index("ix_analysis_config_type", "analysis_type", unique=True),
        {"comment": "AI 分析策略配置表"},
    )

    analysis_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="分析类型：market-大盘分析，sector-板块分析（唯一）",
    )
    prompt_template: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None,
        comment="分析策略定制提示词（关注面/风格/风控偏好等，空则使用默认策略）",
    )
    include_tomorrow: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否包含明日研判章节"
    )
    tomorrow_prompt_template: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None,
        comment="明日研判定制提示词（方法论与侧重点，空则使用内置专业研判框架）",
    )
