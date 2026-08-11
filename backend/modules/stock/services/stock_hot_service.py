#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票热榜抓取入库 + 排名对比 服务
"""
import logging
from datetime import date

import httpx
from sqlalchemy import select, and_, delete, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.stock_hot import (
    BusinessStockHotRank,
    BusinessStockHotSyncLog,
)
from database.utils.timezone import timezone
from modules.stock.schemas.stock_hot import (
    StockHotRankItem,
    StockHotSourceItem,
    StockHotHistoryItem,
)
from modules.stock.services.stock_hot_fetcher import STOCK_HOT_SOURCES

logger = logging.getLogger(__name__)


class StockHotService:
    """股票热榜服务类"""

    # ------------------------------------------------------------------
    # 抓取入库
    # ------------------------------------------------------------------
    @staticmethod
    async def sync_all(db: AsyncSession) -> dict:
        """抓取所有热榜源并写入当日快照。

        返回汇总：{fetched, saved, failed_sources}
        """
        fetched_total = 0
        saved_total = 0
        failed_sources: list[dict] = []
        today = timezone.now().date()

        async with httpx.AsyncClient(headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        }) as client:
            for source in STOCK_HOT_SOURCES:
                key = source["key"]
                started_at = timezone.now()
                try:
                    raw_items = await source["fetch"](client)
                    raw_items = [it for it in raw_items if it]
                    fetched_count = len(raw_items)

                    rows = [
                        {
                            "record_date": today,
                            "source": key,
                            "rank": it["rank"],
                            "stock_code": it["stock_code"],
                            "stock_name": it["stock_name"],
                            "latest_price": it.get("latest_price"),
                            "change_pct": it.get("change_pct"),
                            "hot_value": it.get("hot_value"),
                            "created_at": timezone.now(),
                        }
                        for it in raw_items
                    ]

                    saved_count = 0
                    if rows:
                        # 清理当天该源历史遗留的"带交易所前缀"脏数据
                        # （雪球旧代码存成了 SH600519），避免与规范化后的
                        # 纯数字记录同日并存导致前端列表出现重复行
                        await db.execute(
                            delete(BusinessStockHotRank).where(
                                BusinessStockHotRank.record_date == today,
                                BusinessStockHotRank.source == key,
                                or_(
                                    BusinessStockHotRank.stock_code.like("SH%"),
                                    BusinessStockHotRank.stock_code.like("SZ%"),
                                    BusinessStockHotRank.stock_code.like("BJ%"),
                                ),
                            )
                        )
                        stmt = insert(BusinessStockHotRank).values(rows)
                        stmt = stmt.on_conflict_do_nothing(
                            index_elements=["record_date", "source", "stock_code"]
                        )
                        result = await db.execute(stmt)
                        saved_count = result.rowcount or 0

                    fetched_total += fetched_count
                    saved_total += saved_count
                    db.add(BusinessStockHotSyncLog(
                        source=key,
                        status=True,
                        fetched_count=fetched_count,
                        saved_count=saved_count,
                        started_at=started_at,
                        finished_at=timezone.now(),
                    ))
                    await db.commit()
                    logger.info(
                        "热榜源 %s 抓取完成: fetched=%d saved=%d",
                        key, fetched_count, saved_count,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("热榜源 %s 抓取失败: %s", key, exc)
                    await db.rollback()
                    failed_sources.append({"source": key, "error": str(exc)})
                    db.add(BusinessStockHotSyncLog(
                        source=key,
                        status=False,
                        fetched_count=0,
                        saved_count=0,
                        error_msg=str(exc)[:1000],
                        started_at=started_at,
                        finished_at=timezone.now(),
                    ))
                    await db.commit()

        return {
            "fetched": fetched_total,
            "saved": saved_total,
            "failed_sources": failed_sources,
        }

    # ------------------------------------------------------------------
    # 查询：最新榜单（含排名变化）
    # ------------------------------------------------------------------
    @staticmethod
    async def _get_recent_dates(
        db: AsyncSession, source: str, limit: int = 2
    ) -> list[date]:
        """取指定源最近的 N 个快照日期（降序）"""
        result = await db.execute(
            select(BusinessStockHotRank.record_date)
            .where(
                BusinessStockHotRank.source == source,
                BusinessStockHotRank.deleted_at.is_(None),
            )
            .distinct()
            .order_by(BusinessStockHotRank.record_date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_rank_list(
        db: AsyncSession,
        source: str,
        record_date: str | None = None,
    ) -> list[StockHotRankItem]:
        """获取热榜列表，自动计算排名变化。

        - record_date 指定时取该日期的快照，否则取最新。
        - 排名变化 = 上一快照排名 - 当前排名（正=上升，负=下降，null=新进榜）。
        """
        source_name = _source_name(source)

        # 确定当前日期
        if record_date:
            cur_date = date.fromisoformat(record_date)
        else:
            recent = await StockHotService._get_recent_dates(db, source, limit=1)
            if not recent:
                return []
            cur_date = recent[0]

        # 取当前快照
        cur_result = await db.execute(
            select(BusinessStockHotRank)
            .where(
                BusinessStockHotRank.source == source,
                BusinessStockHotRank.record_date == cur_date,
                BusinessStockHotRank.deleted_at.is_(None),
            )
            .order_by(BusinessStockHotRank.rank.asc())
        )
        cur_rows = cur_result.scalars().all()
        if not cur_rows:
            return []

        # 取上一快照（cur_date 之前最近的一天）
        prev_result = await db.execute(
            select(BusinessStockHotRank.stock_code, BusinessStockHotRank.rank)
            .where(
                BusinessStockHotRank.source == source,
                BusinessStockHotRank.record_date < cur_date,
                BusinessStockHotRank.deleted_at.is_(None),
            )
            .order_by(BusinessStockHotRank.record_date.desc())
            .limit(200)
        )
        # 取最近一个日期的全部（可能分页，这里用 dict 存最新出现排名）
        prev_map: dict[str, int] = {}
        prev_date = None
        # 重新查询：取 cur_date 之前最近日期的全部快照
        prev_date_result = await db.execute(
            select(BusinessStockHotRank.record_date)
            .where(
                BusinessStockHotRank.source == source,
                BusinessStockHotRank.record_date < cur_date,
                BusinessStockHotRank.deleted_at.is_(None),
            )
            .distinct()
            .order_by(BusinessStockHotRank.record_date.desc())
            .limit(1)
        )
        prev_date = prev_date_result.scalar_one_or_none()

        if prev_date:
            prev_full = await db.execute(
                select(BusinessStockHotRank.stock_code, BusinessStockHotRank.rank)
                .where(
                    BusinessStockHotRank.source == source,
                    BusinessStockHotRank.record_date == prev_date,
                    BusinessStockHotRank.deleted_at.is_(None),
                )
            )
            for row in prev_full.all():
                prev_map[row.stock_code] = row.rank

        items = []
        for row in cur_rows:
            prev_rank = prev_map.get(row.stock_code)
            rank_change = (prev_rank - row.rank) if prev_rank is not None else None
            items.append(StockHotRankItem(
                id=row.id,
                source=row.source,
                source_name=source_name,
                record_date=row.record_date,
                rank=row.rank,
                rank_change=rank_change,
                stock_code=row.stock_code,
                stock_name=row.stock_name,
                latest_price=float(row.latest_price) if row.latest_price is not None else None,
                change_pct=float(row.change_pct) if row.change_pct is not None else None,
                hot_value=float(row.hot_value) if row.hot_value is not None else None,
            ))
        return items

    # ------------------------------------------------------------------
    # 查询：源列表
    # ------------------------------------------------------------------
    @staticmethod
    async def get_sources(db: AsyncSession) -> list[StockHotSourceItem]:
        """获取所有热榜源及其最新快照统计"""
        items = []
        for s in STOCK_HOT_SOURCES:
            key = s["key"]
            recent = await StockHotService._get_recent_dates(db, key, limit=1)
            last_date = recent[0] if recent else None
            count = 0
            if last_date:
                cnt_result = await db.execute(
                    select(BusinessStockHotRank)
                    .where(
                        BusinessStockHotRank.source == key,
                        BusinessStockHotRank.record_date == last_date,
                        BusinessStockHotRank.deleted_at.is_(None),
                    )
                )
                count = len(cnt_result.scalars().all())

            # 最近同步时间
            sync_result = await db.execute(
                select(BusinessStockHotSyncLog.finished_at)
                .where(
                    BusinessStockHotSyncLog.source == key,
                    BusinessStockHotSyncLog.deleted_at.is_(None),
                )
                .order_by(BusinessStockHotSyncLog.finished_at.desc().nullslast())
                .limit(1)
            )
            last_sync = sync_result.scalar_one_or_none()

            items.append(StockHotSourceItem(
                source=key,
                source_name=s["name"],
                group=s.get("group", ""),
                last_record_date=last_date,
                last_sync_at=last_sync,
                count=count,
            ))
        return items

    # ------------------------------------------------------------------
    # 查询：可回看日期列表
    # ------------------------------------------------------------------
    @staticmethod
    async def get_dates(db: AsyncSession, source: str) -> list[date]:
        """获取指定源所有可回看的快照日期（降序）"""
        result = await db.execute(
            select(BusinessStockHotRank.record_date)
            .where(
                BusinessStockHotRank.source == source,
                BusinessStockHotRank.deleted_at.is_(None),
            )
            .distinct()
            .order_by(BusinessStockHotRank.record_date.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 查询：单股历史排名
    # ------------------------------------------------------------------
    @staticmethod
    async def get_history(
        db: AsyncSession,
        source: str,
        stock_code: str,
        days: int = 30,
    ) -> list[StockHotHistoryItem]:
        """获取单股历史排名趋势"""
        result = await db.execute(
            select(
                BusinessStockHotRank.record_date,
                BusinessStockHotRank.rank,
            )
            .where(
                BusinessStockHotRank.source == source,
                BusinessStockHotRank.stock_code == stock_code,
                BusinessStockHotRank.deleted_at.is_(None),
            )
            .order_by(BusinessStockHotRank.record_date.desc())
            .limit(days)
        )
        rows = result.all()
        return [
            StockHotHistoryItem(record_date=row.record_date, rank=row.rank)
            for row in reversed(rows)
        ]


def _source_name(source_key: str) -> str:
    """从注册表取源中文名"""
    for s in STOCK_HOT_SOURCES:
        if s["key"] == source_key:
            return s["name"]
    return source_key
