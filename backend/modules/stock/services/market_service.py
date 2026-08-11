#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大盘指数服务：同步入库 + 查询
"""
import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.stock_market import (
    BusinessMarketFundFlow,
    BusinessMarketIndexDaily,
)
from database.utils.timezone import timezone
from modules.stock.schemas.market_overview import (
    MarketFundFlowItem,
    MarketIndexItem,
    MarketIndexHistoryItem,
    MarketIndexOption,
)
from modules.stock.services import market_fetcher

logger = logging.getLogger(__name__)


class MarketService:
    """大盘指数服务"""

    @staticmethod
    async def sync_all(db: AsyncSession) -> dict:
        """抓取主要指数实时行情并写入当日快照；同时同步大盘资金流（失败不影响指数快照）"""
        today = timezone.now().date()
        raw_items = await market_fetcher.fetch_index_spot()
        if not raw_items:
            return {"fetched": 0, "saved": 0, "fund_flow": 0}

        rows = [
            {
                # akshare 实时数据无 record_date 取当天；baostock 降级时用 bar 的真实交易日
                "record_date": date.fromisoformat(it["record_date"]) if it.get("record_date") else today,
                "index_code": it["index_code"],
                "index_name": it["index_name"],
                "latest_price": it.get("latest_price"),
                "change_pct": it.get("change_pct"),
                "change_amount": it.get("change_amount"),
                "volume": it.get("volume"),
                "turnover": it.get("turnover"),
                "amplitude": it.get("amplitude"),
                "high": it.get("high"),
                "low": it.get("low"),
                "open": it.get("open"),
                "prev_close": it.get("prev_close"),
                "created_at": timezone.now(),
            }
            for it in raw_items
        ]

        stmt = insert(BusinessMarketIndexDaily).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["record_date", "index_code"],
            set_={
                "index_name": stmt.excluded.index_name,
                "latest_price": stmt.excluded.latest_price,
                "change_pct": stmt.excluded.change_pct,
                "change_amount": stmt.excluded.change_amount,
                "volume": stmt.excluded.volume,
                "turnover": stmt.excluded.turnover,
                "amplitude": stmt.excluded.amplitude,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "open": stmt.excluded.open,
                "prev_close": stmt.excluded.prev_close,
                "updated_at": timezone.now(),
            },
        )
        result = await db.execute(stmt)
        await db.commit()

        # 大盘资金流为东财单一数据源，限流期间可能失败，不阻塞指数快照入库
        fund_flow_saved = 0
        try:
            fund_flow_saved = await MarketService.sync_fund_flow(db)
        except Exception:
            logger.warning("大盘资金流同步失败（不影响指数快照）", exc_info=True)

        return {
            "fetched": len(raw_items),
            "saved": result.rowcount or 0,
            "fund_flow": fund_flow_saved,
        }

    @staticmethod
    async def sync_fund_flow(db: AsyncSession) -> int:
        """抓取大盘资金流历史并 UPSERT 入库，返回写入行数"""
        raw_items = await market_fetcher.fetch_market_fund_flow()
        if not raw_items:
            return 0

        rows = [
            {
                "record_date": date.fromisoformat(it["record_date"]),
                "main_net_inflow": it.get("main_net_inflow"),
                "super_large_net_inflow": it.get("super_large_net_inflow"),
                "large_net_inflow": it.get("large_net_inflow"),
                "medium_net_inflow": it.get("medium_net_inflow"),
                "small_net_inflow": it.get("small_net_inflow"),
                "created_at": timezone.now(),
            }
            for it in raw_items
        ]
        stmt = insert(BusinessMarketFundFlow).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["record_date"],
            set_={
                "main_net_inflow": stmt.excluded.main_net_inflow,
                "super_large_net_inflow": stmt.excluded.super_large_net_inflow,
                "large_net_inflow": stmt.excluded.large_net_inflow,
                "medium_net_inflow": stmt.excluded.medium_net_inflow,
                "small_net_inflow": stmt.excluded.small_net_inflow,
                "updated_at": timezone.now(),
            },
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount or 0

    @staticmethod
    async def _query_fund_flow_rows(db: AsyncSession, days: int) -> list[BusinessMarketFundFlow]:
        result = await db.execute(
            select(BusinessMarketFundFlow)
            .where(BusinessMarketFundFlow.deleted_at.is_(None))
            .order_by(BusinessMarketFundFlow.record_date.desc())
            .limit(days)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_fund_flow(db: AsyncSession, days: int = 60) -> list[MarketFundFlowItem]:
        """获取大盘资金流历史（按日期升序）；本地为空时先尝试同步回补"""
        rows = await MarketService._query_fund_flow_rows(db, days)
        if not rows:
            try:
                await MarketService.sync_fund_flow(db)
            except Exception:
                logger.warning("大盘资金流回补失败", exc_info=True)
            rows = await MarketService._query_fund_flow_rows(db, days)
        return [
            MarketFundFlowItem.model_validate(row)
            for row in reversed(rows)
        ]

    @staticmethod
    async def get_indices(
        db: AsyncSession, record_date: str | None = None
    ) -> list[MarketIndexItem]:
        """获取指数列表，record_date 为空时取最新快照日"""
        if record_date:
            target_date = date.fromisoformat(record_date)
        else:
            latest = await db.execute(
                select(BusinessMarketIndexDaily.record_date)
                .where(BusinessMarketIndexDaily.deleted_at.is_(None))
                .distinct()
                .order_by(BusinessMarketIndexDaily.record_date.desc())
                .limit(1)
            )
            target_date = latest.scalar_one_or_none()
            if not target_date:
                return []

        result = await db.execute(
            select(BusinessMarketIndexDaily)
            .where(
                BusinessMarketIndexDaily.record_date == target_date,
                BusinessMarketIndexDaily.deleted_at.is_(None),
            )
            .order_by(BusinessMarketIndexDaily.index_code)
        )
        return [
            MarketIndexItem.model_validate(row)
            for row in result.scalars().all()
        ]

    @staticmethod
    async def get_index_options(db: AsyncSession) -> list[MarketIndexOption]:
        """获取所有曾同步过的指数代码+名称，供前端下拉选择"""
        result = await db.execute(
            select(
                BusinessMarketIndexDaily.index_code,
                BusinessMarketIndexDaily.index_name,
            )
            .where(BusinessMarketIndexDaily.deleted_at.is_(None))
            .distinct()
            .order_by(BusinessMarketIndexDaily.index_code)
        )
        return [
            MarketIndexOption(index_code=row[0], index_name=row[1])
            for row in result.all()
        ]

    @staticmethod
    async def _query_history_rows(
        db: AsyncSession, index_code: str, days: int
    ) -> list[BusinessMarketIndexDaily]:
        result = await db.execute(
            select(BusinessMarketIndexDaily)
            .where(
                BusinessMarketIndexDaily.index_code == index_code,
                BusinessMarketIndexDaily.deleted_at.is_(None),
            )
            .order_by(BusinessMarketIndexDaily.record_date.desc())
            .limit(days)
        )
        return list(result.scalars().all())

    @staticmethod
    async def _backfill_history(db: AsyncSession, index_code: str, days: int) -> int:
        """历史回补：从数据源（akshare，失败自动降级 baostock）抓取日线并 UPSERT 入库"""
        end = timezone.now().date()
        # 自然日按 2 倍冗余，覆盖周末与节假日，确保拿到约 days 个交易日
        start = end - timedelta(days=days * 2)
        try:
            bars = await market_fetcher.fetch_index_history(
                index_code, start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
            )
        except Exception:
            logger.exception("指数历史回补失败 code=%s", index_code)
            return 0
        bars = [b for b in bars if b.get("record_date") and b.get("latest_price") is not None]
        if not bars:
            return 0

        name = next(
            (it["name"] for it in market_fetcher.TRACKED_INDICES if it["code"] == index_code),
            index_code,
        )
        rows = [
            {
                "record_date": date.fromisoformat(b["record_date"]),
                "index_code": index_code,
                "index_name": name,
                "latest_price": b.get("latest_price"),
                "change_pct": b.get("change_pct"),
                "change_amount": b.get("change_amount"),
                "volume": b.get("volume"),
                "turnover": b.get("turnover"),
                "amplitude": b.get("amplitude"),
                "high": b.get("high"),
                "low": b.get("low"),
                "open": b.get("open"),
                "prev_close": b.get("prev_close"),
                "created_at": timezone.now(),
            }
            for b in bars
        ]
        stmt = insert(BusinessMarketIndexDaily).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["record_date", "index_code"],
            set_={
                "index_name": stmt.excluded.index_name,
                "latest_price": stmt.excluded.latest_price,
                "change_pct": stmt.excluded.change_pct,
                "change_amount": stmt.excluded.change_amount,
                "volume": stmt.excluded.volume,
                "turnover": stmt.excluded.turnover,
                "amplitude": stmt.excluded.amplitude,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "open": stmt.excluded.open,
                "prev_close": stmt.excluded.prev_close,
                "updated_at": timezone.now(),
            },
        )
        result = await db.execute(stmt)
        await db.commit()
        logger.info("指数历史回补完成 code=%s, %d 行", index_code, len(rows))
        return result.rowcount or 0

    @staticmethod
    async def get_history(
        db: AsyncSession,
        index_code: str,
        days: int = 90,
    ) -> list[MarketIndexHistoryItem]:
        """从 DB 获取单指数历史趋势；本地数据过少时自动从数据源回补入库后再读"""
        rows = await MarketService._query_history_rows(db, index_code, days)
        # 行数明显不足（新部署/数据刚起步）时触发回补；日常由每日同步追加，不重复抓取
        if len(rows) < min(days, 20):
            await MarketService._backfill_history(db, index_code, days)
            rows = await MarketService._query_history_rows(db, index_code, days)
        return [
            MarketIndexHistoryItem(
                record_date=row.record_date,
                latest_price=float(row.latest_price) if row.latest_price is not None else None,
                change_pct=float(row.change_pct) if row.change_pct is not None else None,
                volume=float(row.volume) if row.volume is not None else None,
                turnover=float(row.turnover) if row.turnover is not None else None,
                high=float(row.high) if row.high is not None else None,
                low=float(row.low) if row.low is not None else None,
                open=float(row.open) if row.open is not None else None,
                prev_close=float(row.prev_close) if row.prev_close is not None else None,
            )
            for row in reversed(rows)
        ]

    @staticmethod
    async def get_dates(db: AsyncSession) -> list[date]:
        """获取所有可回看的快照日期（降序）"""
        result = await db.execute(
            select(BusinessMarketIndexDaily.record_date)
            .where(BusinessMarketIndexDaily.deleted_at.is_(None))
            .distinct()
            .order_by(BusinessMarketIndexDaily.record_date.desc())
        )
        return list(result.scalars().all())
