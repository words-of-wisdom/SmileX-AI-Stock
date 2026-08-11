#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
行业/概念板块服务：同步入库 + 查询
"""
import asyncio
import logging
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.stock_market import BusinessBoardDaily
from database.utils.timezone import timezone
from modules.stock.schemas.industry_board import BoardDailyItem, BoardHistoryItem
from modules.stock.services import board_fetcher

logger = logging.getLogger(__name__)


class BoardService:
    """行业/概念板块服务"""

    @staticmethod
    async def sync_all(db: AsyncSession, board_type: str = "industry") -> dict:
        """抓取指定类型板块列表 + 资金流，写入当日快照"""
        today = timezone.now().date()
        raw_items = await board_fetcher.fetch_board_list(board_type)
        if not raw_items:
            return {"fetched": 0, "saved": 0, "board_type": board_type}

        # 同批去重：行情实时变动时分页拉取可能跨页重复，同批出现重复
        # (record_date, board_type, board_code) 会让 ON CONFLICT DO UPDATE 报错
        seen: set[str] = set()
        unique_items = []
        for it in raw_items:
            if it["board_code"] in seen:
                continue
            seen.add(it["board_code"])
            unique_items.append(it)
        if len(unique_items) != len(raw_items):
            logger.warning(
                "板块列表存在重复代码(%s)，已去重: %d -> %d",
                board_type, len(raw_items), len(unique_items),
            )
        raw_items = unique_items

        # 抓取资金流数据并按板块名称映射（东财接口对高频请求有 IP 级限流，错开间隔）
        await asyncio.sleep(1.5)
        flow_map = await board_fetcher.fetch_board_fund_flow(board_type)

        rows = []
        for it in raw_items:
            # 东财资金流按名称匹配优先；未命中时回退抓取层自带的净流入（同花顺兜底链有值）
            net_inflow = flow_map.get(it["board_name"])
            if net_inflow is None:
                net_inflow = it.get("net_inflow")
            rows.append({
                "record_date": today,
                "board_type": board_type,
                "board_code": it["board_code"],
                "board_name": it["board_name"],
                "change_pct": it.get("change_pct"),
                "turnover": it.get("turnover"),
                "turnover_rate": it.get("turnover_rate"),
                "volume": it.get("volume"),
                "net_inflow": net_inflow,
                "rising_count": it.get("rising_count"),
                "falling_count": it.get("falling_count"),
                "leading_stock_code": it.get("leading_stock_code"),
                "leading_stock_name": it.get("leading_stock_name"),
                "leading_stock_change_pct": it.get("leading_stock_change_pct"),
                "created_at": timezone.now(),
            })

        # 先清当日同类型数据再写入：降级链换源重同步时板块代码体系不同，
        # 仅靠 ON CONFLICT 会残留上一数据源的记录，造成同日多源混杂
        await db.execute(
            delete(BusinessBoardDaily).where(
                BusinessBoardDaily.record_date == today,
                BusinessBoardDaily.board_type == board_type,
            )
        )

        stmt = insert(BusinessBoardDaily).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["record_date", "board_type", "board_code"],
            set_={
                "board_name": stmt.excluded.board_name,
                "change_pct": stmt.excluded.change_pct,
                "turnover": stmt.excluded.turnover,
                "turnover_rate": stmt.excluded.turnover_rate,
                "volume": stmt.excluded.volume,
                "net_inflow": stmt.excluded.net_inflow,
                "rising_count": stmt.excluded.rising_count,
                "falling_count": stmt.excluded.falling_count,
                "leading_stock_code": stmt.excluded.leading_stock_code,
                "leading_stock_name": stmt.excluded.leading_stock_name,
                "leading_stock_change_pct": stmt.excluded.leading_stock_change_pct,
                "updated_at": timezone.now(),
            },
        )
        result = await db.execute(stmt)
        await db.commit()

        return {
            "fetched": len(raw_items),
            "saved": result.rowcount or 0,
            "board_type": board_type,
        }

    @staticmethod
    async def get_list(
        db: AsyncSession,
        board_type: str = "industry",
        record_date: str | None = None,
        sort_by: str = "change_pct",
        sort_order: str = "desc",
    ) -> list[BoardDailyItem]:
        """获取板块列表"""
        if record_date:
            target_date = date.fromisoformat(record_date)
        else:
            latest = await db.execute(
                select(BusinessBoardDaily.record_date)
                .where(
                    BusinessBoardDaily.board_type == board_type,
                    BusinessBoardDaily.deleted_at.is_(None),
                )
                .distinct()
                .order_by(BusinessBoardDaily.record_date.desc())
                .limit(1)
            )
            target_date = latest.scalar_one_or_none()
            if not target_date:
                return []

        sort_col = BusinessBoardDaily.net_inflow if sort_by == "net_inflow" else BusinessBoardDaily.change_pct
        order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

        result = await db.execute(
            select(BusinessBoardDaily)
            .where(
                BusinessBoardDaily.board_type == board_type,
                BusinessBoardDaily.record_date == target_date,
                BusinessBoardDaily.deleted_at.is_(None),
            )
            .order_by(order)
        )
        return [
            BoardDailyItem.model_validate(row)
            for row in result.scalars().all()
        ]

    @staticmethod
    async def get_history(
        db: AsyncSession,
        board_type: str,
        board_code: str,
        days: int = 30,
    ) -> list[BoardHistoryItem]:
        """获取单板块历史趋势"""
        result = await db.execute(
            select(BusinessBoardDaily)
            .where(
                BusinessBoardDaily.board_type == board_type,
                BusinessBoardDaily.board_code == board_code,
                BusinessBoardDaily.deleted_at.is_(None),
            )
            .order_by(BusinessBoardDaily.record_date.desc())
            .limit(days)
        )
        rows = result.scalars().all()
        return [
            BoardHistoryItem(
                record_date=row.record_date,
                change_pct=float(row.change_pct) if row.change_pct is not None else None,
                turnover=float(row.turnover) if row.turnover is not None else None,
                net_inflow=float(row.net_inflow) if row.net_inflow is not None else None,
                rising_count=row.rising_count,
                falling_count=row.falling_count,
            )
            for row in reversed(rows)
        ]

    @staticmethod
    async def get_dates(db: AsyncSession, board_type: str = "industry") -> list[date]:
        """获取可回看日期列表"""
        result = await db.execute(
            select(BusinessBoardDaily.record_date)
            .where(
                BusinessBoardDaily.board_type == board_type,
                BusinessBoardDaily.deleted_at.is_(None),
            )
            .distinct()
            .order_by(BusinessBoardDaily.record_date.desc())
        )
        return list(result.scalars().all())
