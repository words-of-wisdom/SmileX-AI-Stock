"""一次性手动补拉 A 股各模块最新数据（复用现有 Service 层，不启动调度器）。

背景：定时任务（15:30-15:40）触发正常，但东财 push2 对本机 IP 限流时，
资金流/暗盘每日统计等单源数据会缺失且无补偿机制（misfire_grace_time=60）。
本脚本用于收盘后手动补拉当日数据；各 Service 内部均走多源降级链
（东财 → 新浪/腾讯 → baostock），upsert 幂等可重复执行。

用法：
    cd backend && ENVIR=dev .venv/bin/python -m scripts.sync_astock_latest
"""
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import init_pool, close_pool
from database.manager.async_manager import get_session
from modules.stock.services.market_fetcher import TRACKED_INDICES
from modules.stock.services.market_service import MarketService
from modules.stock.services.board_service import BoardService
from modules.stock.services.limit_up_service import LimitUpService
from modules.stock.services.block_trade_service import BlockTradeService

# 各步骤之间的间隔（秒），降低东财连续请求触发 IP 限流的概率
STEP_INTERVAL = 3


def _fmt(value) -> str:
    return str(value) if value is not None else "-"


async def run_step(name: str, coro_factory) -> dict:
    """执行单个同步步骤并打印结果，失败不阻断后续步骤"""
    print(f"\n==> {name} ...")
    try:
        result = await coro_factory()
        print(f"    完成: {result}")
        return {"name": name, "ok": True, "result": result}
    except Exception as exc:  # noqa: BLE001
        print(f"    失败: {exc}")
        return {"name": name, "ok": False, "result": str(exc)}


async def main() -> None:
    await init_pool()
    summary = []
    try:
        async for db in get_session():
            # 1. 大盘指数快照 + 资金流（资金流东财单源，fetcher 内已有一次退避重试）
            summary.append(await run_step(
                "大盘指数快照+资金流", lambda: MarketService.sync_all(db)))

            await asyncio.sleep(STEP_INTERVAL)

            # 2. 指数日线历史回补：get_history 在本地行数充足时不抓取，
            #    不足/缺失时回补（东财失败自动降级 baostock，收盘后日线已就绪）
            for idx in TRACKED_INDICES:
                code = idx["code"]

                async def _backfill(c: str = code) -> dict:
                    items = await MarketService.get_history(db, c, days=90)
                    return {"rows": len(items)}

                summary.append(await run_step(
                    f"指数历史回补 {code} {idx['name']}", _backfill))

            await asyncio.sleep(STEP_INTERVAL)

            # 3. 板块（行业 + 概念），列表有腾讯/同花顺兜底，资金流东财单源
            for board_type in ("industry", "concept"):
                summary.append(await run_step(
                    f"板块同步({board_type})",
                    lambda bt=board_type: BoardService.sync_all(db, bt),
                ))
                await asyncio.sleep(STEP_INTERVAL)

            # 4. 涨停股池（东财，今日定时任务已成功写入，重跑幂等）
            summary.append(await run_step("涨停股池", lambda: LimitUpService.sync_all(db)))

            await asyncio.sleep(STEP_INTERVAL)

            # 5. 暗盘：每日统计 + 三个活跃窗口（分块 upsert 已修复近六月超参数问题）
            summary.append(await run_step("暗盘(大宗交易)", lambda: BlockTradeService.sync_all(db)))
    finally:
        await close_pool()

    print("\n========== 补拉汇总 ==========")
    ok = sum(1 for s in summary if s["ok"])
    for s in summary:
        status = "✅" if s["ok"] else "❌"
        print(f"  {status} {s['name']}: {_fmt(s['result'])}")
    print(f"共 {len(summary)} 步，成功 {ok}，失败 {len(summary) - ok}")


if __name__ == "__main__":
    asyncio.run(main())
