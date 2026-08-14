#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大宗交易（暗盘）抓取入库 + 查询 服务
"""
import logging
from datetime import date, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.business.block_trade import (
    BusinessBlockTradeDaily,
    BusinessBlockTradeActive,
    BusinessBlockTradeSyncLog,
)
from database.utils.timezone import timezone
from modules.stock.schemas.block_trade import (
    BlockTradeDailyItem,
    BlockTradeActiveItem,
    BlockTradeSourceItem,
    BlockTradeHistoryItem,
)
from modules.stock.services.block_trade_fetcher import (
    fetch_daily,
    fetch_active,
    ACTIVE_WINDOWS,
)

logger = logging.getLogger(__name__)


class BlockTradeService:
    """大宗交易（暗盘）服务类"""

    # ------------------------------------------------------------------
    # 抓取入库
    # ------------------------------------------------------------------
    @staticmethod
    async def sync_daily(db: AsyncSession, target_date: date | None = None) -> dict:
        """抓取指定日期（默认今日）的大宗交易每日统计并 upsert。

        返回：{fetched, saved, record_date}
        """
        today = target_date or timezone.now().date()
        date_str = today.strftime("%Y%m%d")
        started_at = timezone.now()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        }
        try:
            async with httpx.AsyncClient(headers=headers) as client:
                raw_items = await fetch_daily(client, date_str, date_str)
            raw_items = [it for it in raw_items if it]
            fetched_count = len(raw_items)

            saved_count = 0
            if raw_items:
                rows = [
                    {
                        "record_date": today,
                        "stock_code": it["stock_code"],
                        "stock_name": it["stock_name"],
                        "change_pct": it.get("change_pct"),
                        "close_price": it.get("close_price"),
                        "trade_price": it.get("trade_price"),
                        "premium_rate": it.get("premium_rate"),
                        "trade_count": it.get("trade_count"),
                        "trade_volume": it.get("trade_volume"),
                        "trade_amount": it.get("trade_amount"),
                        "amount_ratio": it.get("amount_ratio"),
                        "created_at": timezone.now(),
                        "updated_at": timezone.now(),
                    }
                    for it in raw_items
                ]
                stmt = insert(BusinessBlockTradeDaily).values(rows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["record_date", "stock_code"],
                    set_={
                        "stock_name": stmt.excluded.stock_name,
                        "change_pct": stmt.excluded.change_pct,
                        "close_price": stmt.excluded.close_price,
                        "trade_price": stmt.excluded.trade_price,
                        "premium_rate": stmt.excluded.premium_rate,
                        "trade_count": stmt.excluded.trade_count,
                        "trade_volume": stmt.excluded.trade_volume,
                        "trade_amount": stmt.excluded.trade_amount,
                        "amount_ratio": stmt.excluded.amount_ratio,
                        "updated_at": stmt.excluded.updated_at,
                    },
                )
                result = await db.execute(stmt)
                saved_count = result.rowcount or 0

            db.add(BusinessBlockTradeSyncLog(
                sub_board="daily",
                status=True,
                fetched_count=fetched_count,
                saved_count=saved_count,
                started_at=started_at,
                finished_at=timezone.now(),
            ))
            await db.commit()
            logger.info("暗盘每日统计抓取完成: date=%s fetched=%d saved=%d",
                        today, fetched_count, saved_count)
            return {"fetched": fetched_count, "saved": saved_count, "record_date": today.isoformat()}
        except Exception as exc:  # noqa: BLE001
            logger.warning("暗盘每日统计抓取失败: %s", exc)
            await db.rollback()
            db.add(BusinessBlockTradeSyncLog(
                sub_board="daily",
                status=False,
                fetched_count=0,
                saved_count=0,
                error_msg=str(exc)[:1000],
                started_at=started_at,
                finished_at=timezone.now(),
            ))
            await db.commit()
            raise

    @staticmethod
    async def sync_active(db: AsyncSession, stat_window: str) -> dict:
        """抓取指定窗口的活跃A股统计并 upsert（先清旧再插，避免残留）。

        返回：{fetched, saved, stat_window}
        """
        if stat_window not in ACTIVE_WINDOWS:
            raise ValueError(f"不支持的统计窗口: {stat_window}")
        started_at = timezone.now()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        }
        try:
            async with httpx.AsyncClient(headers=headers) as client:
                raw_items = await fetch_active(client, stat_window)
            raw_items = [it for it in raw_items if it]
            fetched_count = len(raw_items)

            saved_count = 0
            if raw_items:
                rows = [
                    {
                        "stat_window": stat_window,
                        "stock_code": it["stock_code"],
                        "stock_name": it["stock_name"],
                        "latest_price": it.get("latest_price"),
                        "change_pct": it.get("change_pct"),
                        "last_list_date": it.get("last_list_date"),
                        "list_count_total": it.get("list_count_total"),
                        "list_count_premium": it.get("list_count_premium"),
                        "list_count_discount": it.get("list_count_discount"),
                        "total_amount": it.get("total_amount"),
                        "premium_rate": it.get("premium_rate"),
                        "amount_ratio": it.get("amount_ratio"),
                        "avg_change_1d": it.get("avg_change_1d"),
                        "avg_change_5d": it.get("avg_change_5d"),
                        "avg_change_10d": it.get("avg_change_10d"),
                        "avg_change_20d": it.get("avg_change_20d"),
                        "created_at": timezone.now(),
                        "updated_at": timezone.now(),
                    }
                    for it in raw_items
                ]
                stmt = insert(BusinessBlockTradeActive).values(rows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["stat_window", "stock_code"],
                    set_={
                        "stock_name": stmt.excluded.stock_name,
                        "latest_price": stmt.excluded.latest_price,
                        "change_pct": stmt.excluded.change_pct,
                        "last_list_date": stmt.excluded.last_list_date,
                        "list_count_total": stmt.excluded.list_count_total,
                        "list_count_premium": stmt.excluded.list_count_premium,
                        "list_count_discount": stmt.excluded.list_count_discount,
                        "total_amount": stmt.excluded.total_amount,
                        "premium_rate": stmt.excluded.premium_rate,
                        "amount_ratio": stmt.excluded.amount_ratio,
                        "avg_change_1d": stmt.excluded.avg_change_1d,
                        "avg_change_5d": stmt.excluded.avg_change_5d,
                        "avg_change_10d": stmt.excluded.avg_change_10d,
                        "avg_change_20d": stmt.excluded.avg_change_20d,
                        "updated_at": stmt.excluded.updated_at,
                    },
                )
                result = await db.execute(stmt)
                saved_count = result.rowcount or 0

            db.add(BusinessBlockTradeSyncLog(
                sub_board="active",
                stat_window=stat_window,
                status=True,
                fetched_count=fetched_count,
                saved_count=saved_count,
                started_at=started_at,
                finished_at=timezone.now(),
            ))
            await db.commit()
            logger.info("暗盘活跃A股抓取完成: window=%s fetched=%d saved=%d",
                        stat_window, fetched_count, saved_count)
            return {"fetched": fetched_count, "saved": saved_count, "stat_window": stat_window}
        except Exception as exc:  # noqa: BLE001
            logger.warning("暗盘活跃A股抓取失败: %s", exc)
            await db.rollback()
            db.add(BusinessBlockTradeSyncLog(
                sub_board="active",
                stat_window=stat_window,
                status=False,
                fetched_count=0,
                saved_count=0,
                error_msg=str(exc)[:1000],
                started_at=started_at,
                finished_at=timezone.now(),
            ))
            await db.commit()
            raise

    @staticmethod
    async def sync_all(db: AsyncSession) -> dict:
        """抓取全部暗盘子榜（每日统计当日 + 全部活跃窗口）。

        单个子榜失败不阻断其它；返回 {daily, active, failed}。
        """
        result = {"daily": None, "active": [], "failed": []}

        # 每日统计
        try:
            result["daily"] = await BlockTradeService.sync_daily(db)
        except Exception as exc:  # noqa: BLE001
            result["failed"].append({"sub_board": "daily", "error": str(exc)})

        # 活跃A股各窗口
        for window in ACTIVE_WINDOWS:
            try:
                r = await BlockTradeService.sync_active(db, window)
                result["active"].append(r)
            except Exception as exc:  # noqa: BLE001
                result["failed"].append({"sub_board": "active", "stat_window": window, "error": str(exc)})

        return result

    # ------------------------------------------------------------------
    # 查询：每日统计列表（含排名变化）
    # ------------------------------------------------------------------
    @staticmethod
    async def _get_recent_dates(
        db: AsyncSession, limit: int = 2
    ) -> list[date]:
        """取最近 N 个快照日期（降序）"""
        result = await db.execute(
            select(BusinessBlockTradeDaily.record_date)
            .where(BusinessBlockTradeDaily.deleted_at.is_(None))
            .distinct()
            .order_by(BusinessBlockTradeDaily.record_date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_daily_list(
        db: AsyncSession,
        record_date: str | None = None,
    ) -> list[BlockTradeDailyItem]:
        """获取每日统计列表，按 amount_ratio 降序排名并计算排名变化。

        - record_date 指定时取该日期的快照，否则取最新。
        - 排名变化 = 上一快照排名 - 当前排名（正=上升，负=下降，null=新进榜）。
        """
        # 确定当前日期
        if record_date:
            cur_date = date.fromisoformat(record_date)
        else:
            recent = await BlockTradeService._get_recent_dates(db, limit=1)
            if not recent:
                return []
            cur_date = recent[0]

        # 当前快照，按 amount_ratio 降序
        cur_result = await db.execute(
            select(BusinessBlockTradeDaily)
            .where(
                BusinessBlockTradeDaily.record_date == cur_date,
                BusinessBlockTradeDaily.deleted_at.is_(None),
            )
        )
        cur_rows = list(cur_result.scalars().all())
        if not cur_rows:
            return []
        # 内存排序并赋予排名
        cur_rows.sort(key=lambda r: (r.amount_ratio if r.amount_ratio is not None else -1), reverse=True)
        cur_rank_map: dict[str, int] = {r.stock_code: idx for idx, r in enumerate(cur_rows, 1)}

        # 取上一快照（cur_date 之前最近日期）
        prev_date_result = await db.execute(
            select(BusinessBlockTradeDaily.record_date)
            .where(
                BusinessBlockTradeDaily.record_date < cur_date,
                BusinessBlockTradeDaily.deleted_at.is_(None),
            )
            .distinct()
            .order_by(BusinessBlockTradeDaily.record_date.desc())
            .limit(1)
        )
        prev_date = prev_date_result.scalar_one_or_none()

        prev_rank_map: dict[str, int] = {}
        if prev_date:
            prev_result = await db.execute(
                select(
                    BusinessBlockTradeDaily.stock_code,
                    BusinessBlockTradeDaily.amount_ratio,
                )
                .where(
                    BusinessBlockTradeDaily.record_date == prev_date,
                    BusinessBlockTradeDaily.deleted_at.is_(None),
                )
            )
            prev_rows = list(prev_result.all())
            prev_rows.sort(key=lambda r: (r.amount_ratio if r.amount_ratio is not None else -1), reverse=True)
            prev_rank_map = {r.stock_code: idx for idx, r in enumerate(prev_rows, 1)}

        items = []
        for row in cur_rows:
            rank = cur_rank_map[row.stock_code]
            prev_rank = prev_rank_map.get(row.stock_code)
            rank_change = (prev_rank - rank) if prev_rank is not None else None
            items.append(BlockTradeDailyItem(
                id=row.id,
                record_date=row.record_date,
                rank=rank,
                rank_change=rank_change,
                stock_code=row.stock_code,
                stock_name=row.stock_name,
                change_pct=float(row.change_pct) if row.change_pct is not None else None,
                close_price=float(row.close_price) if row.close_price is not None else None,
                trade_price=float(row.trade_price) if row.trade_price is not None else None,
                premium_rate=float(row.premium_rate) if row.premium_rate is not None else None,
                trade_count=row.trade_count,
                trade_volume=float(row.trade_volume) if row.trade_volume is not None else None,
                trade_amount=float(row.trade_amount) if row.trade_amount is not None else None,
                amount_ratio=float(row.amount_ratio) if row.amount_ratio is not None else None,
            ))
        return items

    # ------------------------------------------------------------------
    # 查询：活跃A股列表
    # ------------------------------------------------------------------
    @staticmethod
    async def get_active_list(
        db: AsyncSession,
        stat_window: str,
    ) -> list[BlockTradeActiveItem]:
        """获取指定窗口的活跃A股统计，按 list_count_total 降序排名"""
        result = await db.execute(
            select(BusinessBlockTradeActive)
            .where(
                BusinessBlockTradeActive.stat_window == stat_window,
                BusinessBlockTradeActive.deleted_at.is_(None),
            )
        )
        rows = list(result.scalars().all())
        rows.sort(key=lambda r: (r.list_count_total if r.list_count_total is not None else -1), reverse=True)

        items = []
        for idx, row in enumerate(rows, 1):
            items.append(BlockTradeActiveItem(
                id=row.id,
                stat_window=row.stat_window,
                rank=idx,
                stock_code=row.stock_code,
                stock_name=row.stock_name,
                latest_price=float(row.latest_price) if row.latest_price is not None else None,
                change_pct=float(row.change_pct) if row.change_pct is not None else None,
                last_list_date=row.last_list_date,
                list_count_total=row.list_count_total,
                list_count_premium=row.list_count_premium,
                list_count_discount=row.list_count_discount,
                total_amount=float(row.total_amount) if row.total_amount is not None else None,
                premium_rate=float(row.premium_rate) if row.premium_rate is not None else None,
                amount_ratio=float(row.amount_ratio) if row.amount_ratio is not None else None,
                avg_change_1d=float(row.avg_change_1d) if row.avg_change_1d is not None else None,
                avg_change_5d=float(row.avg_change_5d) if row.avg_change_5d is not None else None,
                avg_change_10d=float(row.avg_change_10d) if row.avg_change_10d is not None else None,
                avg_change_20d=float(row.avg_change_20d) if row.avg_change_20d is not None else None,
            ))
        return items

    # ------------------------------------------------------------------
    # 查询：子榜概览
    # ------------------------------------------------------------------
    @staticmethod
    async def get_sources(db: AsyncSession) -> list[BlockTradeSourceItem]:
        """获取所有暗盘子榜及其最新统计"""
        items: list[BlockTradeSourceItem] = []

        # 每日统计
        recent = await BlockTradeService._get_recent_dates(db, limit=1)
        last_date = recent[0] if recent else None
        count = 0
        if last_date:
            cnt_result = await db.execute(
                select(BusinessBlockTradeDaily).where(
                    BusinessBlockTradeDaily.record_date == last_date,
                    BusinessBlockTradeDaily.deleted_at.is_(None),
                )
            )
            count = len(cnt_result.scalars().all())
        sync_result = await db.execute(
            select(BusinessBlockTradeSyncLog.finished_at)
            .where(
                BusinessBlockTradeSyncLog.sub_board == "daily",
                BusinessBlockTradeSyncLog.deleted_at.is_(None),
            )
            .order_by(BusinessBlockTradeSyncLog.finished_at.desc().nullslast())
            .limit(1)
        )
        items.append(BlockTradeSourceItem(
            sub_board="daily",
            source_name="每日统计",
            last_record_date=last_date,
            last_sync_at=sync_result.scalar_one_or_none(),
            count=count,
        ))

        # 活跃A股各窗口
        for window in ACTIVE_WINDOWS:
            cnt_result = await db.execute(
                select(BusinessBlockTradeActive).where(
                    BusinessBlockTradeActive.stat_window == window,
                    BusinessBlockTradeActive.deleted_at.is_(None),
                )
            )
            count = len(cnt_result.scalars().all())
            sync_result = await db.execute(
                select(BusinessBlockTradeSyncLog.finished_at)
                .where(
                    BusinessBlockTradeSyncLog.sub_board == "active",
                    BusinessBlockTradeSyncLog.stat_window == window,
                    BusinessBlockTradeSyncLog.deleted_at.is_(None),
                )
                .order_by(BusinessBlockTradeSyncLog.finished_at.desc().nullslast())
                .limit(1)
            )
            items.append(BlockTradeSourceItem(
                sub_board="active",
                source_name="活跃A股",
                stat_window=window,
                last_sync_at=sync_result.scalar_one_or_none(),
                count=count,
            ))
        return items

    # ------------------------------------------------------------------
    # 查询：可回看日期列表（每日统计）
    # ------------------------------------------------------------------
    @staticmethod
    async def get_dates(db: AsyncSession) -> list[date]:
        """获取每日统计所有可回看的快照日期（降序）"""
        result = await db.execute(
            select(BusinessBlockTradeDaily.record_date)
            .where(BusinessBlockTradeDaily.deleted_at.is_(None))
            .distinct()
            .order_by(BusinessBlockTradeDaily.record_date.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 查询：单股历史排名趋势（按 amount_ratio 排名）
    # ------------------------------------------------------------------
    @staticmethod
    async def get_history(
        db: AsyncSession,
        stock_code: str,
        days: int = 30,
    ) -> list[BlockTradeHistoryItem]:
        """获取单股历史排名趋势（按 amount_ratio 在当日全部个股中的排名）"""
        # 取该股有记录的最近 days 天
        own_result = await db.execute(
            select(BusinessBlockTradeDaily.record_date)
            .where(
                BusinessBlockTradeDaily.stock_code == stock_code,
                BusinessBlockTradeDaily.deleted_at.is_(None),
            )
            .distinct()
            .order_by(BusinessBlockTradeDaily.record_date.desc())
            .limit(days)
        )
        own_dates = [r for r in own_result.scalars().all()]
        if not own_dates:
            return []

        own_dates_set = set(own_dates)
        # 取这些日期内全部记录，计算每日该股排名
        all_result = await db.execute(
            select(
                BusinessBlockTradeDaily.record_date,
                BusinessBlockTradeDaily.stock_code,
                BusinessBlockTradeDaily.amount_ratio,
            )
            .where(
                BusinessBlockTradeDaily.record_date.in_(own_dates_set),
                BusinessBlockTradeDaily.deleted_at.is_(None),
            )
        )
        # 按日期分组
        by_date: dict[date, list[tuple[str, float | None]]] = {}
        for row in all_result.all():
            by_date.setdefault(row.record_date, []).append((row.stock_code, row.amount_ratio))

        items = []
        # 按日期升序输出趋势
        for d in sorted(own_dates):
            rows = by_date.get(d, [])
            rows.sort(key=lambda x: (x[1] if x[1] is not None else -1), reverse=True)
            rank = next((idx for idx, (code, _) in enumerate(rows, 1) if code == stock_code), None)
            if rank is not None:
                items.append(BlockTradeHistoryItem(record_date=d, rank=rank))
        return items
