#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
策略执行器 —— 调用 LLM（复用 agent 模块模型解析 + 工具注册表），
产出结构化买卖信号并落库为模拟持仓
"""
import json
import logging
import re
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.response.response_code import CustomErrorCode
from core.exception.errors import CustomError
from database.models.business.strategy import (
    BusinessAiStrategy,
    BusinessStrategyRun,
    BusinessStrategyPosition,
)
from database.utils.timezone import timezone
from modules.agent.services.llm_client import resolve_model, stream_chat
from modules.agent.services.tool_registry import get_openai_format, execute
from modules.strategy.schemas.strategy import SignalItem, StrategyRunResult
from modules.strategy.services.quote_helper import fetch_latest_prices

logger = logging.getLogger(__name__)

# ReAct 最大迭代轮数（与 agent_service 保持一致）
MAX_ITERATIONS = 8

# 系统提示词：要求 LLM 基于工具真实数据输出严格 JSON 信号
SYSTEM_PROMPT = """你是 SmileX-AI-Stock 平台的 AI 策略分析师，负责按用户策略对A股市场进行买卖点分析。

你可以调用以下工具获取系统中的真实数据：
- get_hot_stocks: 股票热榜（东财/同花顺/雪球等热度排名）
- get_market_indices: 大盘指数行情
- get_market_fund_flow: 大盘资金流向
- get_board_ranking: 行业/概念板块涨跌幅排行
- get_limit_up_stocks: 涨停股池
- get_latest_news: 最新财经新闻

工作流程：
1. 先调用工具获取真实行情数据，禁止凭空编造价格和数据
2. 结合当前持仓情况，按策略要求给出信号

最终必须输出一个 JSON 数组（可包在 ```json 代码块中），每个元素格式如下：
[
  {
    "stock_code": "600519",            // 6位证券代码
    "stock_name": "贵州茅台",
    "action": "buy",                   // buy-新买入 / sell-卖出平仓 / adjust-调整持仓卖点 / hold-继续持有（无点位变化）
    "buy_price": 1500.0,               // 买入参考价（action=buy 时必填）
    "target_sell_price": 1620.0,       // 预估卖点/目标价（buy/adjust 时填写）
    "stop_loss_price": 1430.0,         // 止损价（buy/adjust 时填写）
    "reason": "缩量回调至10日线，资金回流"  // 简要理由
  }
]

没有合适的信号时输出空数组 []。除 JSON 外不要输出任何多余文字。回答使用中文。
"""


def _extract_json_array(text: str) -> list[dict]:
    """从 LLM 回复中提取 JSON 数组（容忍 ```json 代码块 / 前后杂文）"""
    if not text:
        return []
    # 优先取 ```json ... ``` 代码块
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    candidates = []
    if m:
        candidates.append(m.group(1))
    # 否则取第一个 [ 到最后一个 ] 之间的内容
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, list):
                return obj
        except json.JSONDecodeError:
            continue
    raise ValueError("无法从 AI 回复中解析出 JSON 数组")


def _to_signal(raw: dict) -> Optional[SignalItem]:
    """单条原始信号 → SignalItem，非法条目返回 None"""
    code = str(raw.get("stock_code") or "").strip()
    action = str(raw.get("action") or "").strip().lower()
    if not re.fullmatch(r"\d{6}", code) or action not in ("buy", "sell", "adjust", "hold"):
        return None
    return SignalItem(
        stock_code=code,
        stock_name=str(raw.get("stock_name") or "").strip()[:50],
        action=action,
        buy_price=float(raw["buy_price"]) if raw.get("buy_price") not in (None, "", 0) else None,
        target_sell_price=float(raw["target_sell_price"]) if raw.get("target_sell_price") else None,
        stop_loss_price=float(raw["stop_loss_price"]) if raw.get("stop_loss_price") else None,
        reason=str(raw.get("reason") or "").strip()[:500] or None,
    )


async def _run_llm(db: AsyncSession, user_prompt: str) -> str:
    """带工具调用的 LLM 循环（复用 agent 的 ReAct 模式，非流式消费），返回最终文本"""
    # 触发工具模块导入，完成注册
    from modules.agent.tools import stock_tools, news_tools  # noqa: F401

    from database.models.sys.ai_model import AiFunctionEnum

    resolved = await resolve_model(db, AiFunctionEnum.STOCK_PICKING)
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    tools = get_openai_format()
    final_text = ""

    for _ in range(MAX_ITERATIONS):
        collected_tool_calls: list[dict] = []
        assistant_text = ""

        async for chunk in stream_chat(resolved, messages, tools):
            if chunk.content:
                assistant_text += chunk.content
            if chunk.tool_calls:
                collected_tool_calls = chunk.tool_calls

        if not collected_tool_calls:
            final_text = assistant_text
            break

        messages.append(
            {
                "role": "assistant",
                "content": assistant_text or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(
                                tc.get("arguments", {}), ensure_ascii=False
                            ),
                        },
                    }
                    for tc in collected_tool_calls
                ],
            }
        )
        for tc in collected_tool_calls:
            result = await execute(tc["name"], tc.get("arguments", {}) or {}, db)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": tc["name"],
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )
    else:
        raise CustomError(
            err_code=CustomErrorCode.AGENT_MAX_ITERATIONS,
            msg="策略分析达到最大工具调用轮数，未产出最终结论",
        )

    return final_text


def _build_user_prompt(
    strategy: BusinessAiStrategy,
    holdings: list[BusinessStrategyPosition],
    run_period_name: str,
) -> str:
    parts = [
        f"当前执行时段：{run_period_name}，当前时间：{timezone.now().strftime('%Y-%m-%d %H:%M')}",
        f"策略名称：{strategy.name}",
    ]
    if strategy.description:
        parts.append(f"策略描述：{strategy.description}")
    parts.append(f"策略要求：{strategy.prompt_template or '无特殊要求，按市场热点与技术面自主选股'}")

    pool = (strategy.stock_pool or {}).get("codes") if strategy.stock_pool else None
    if pool:
        parts.append(f"候选股票池（仅允许在该池内选择）：{', '.join(str(c) for c in pool)}")

    parts.append(f"最大同时持仓数：{strategy.max_positions}（当前已持仓 {len(holdings)} 只，不要超限）")

    if holdings:
        hold_lines = [
            f"- {h.stock_code} {h.stock_name}：买价 {h.buy_price}，"
            f"预估卖点 {h.target_sell_price or '无'}，止损价 {h.stop_loss_price or '无'}"
            for h in holdings
        ]
        parts.append("当前持仓（对已持仓个股请重点评估是否卖出/调整卖点，action=sell 或 adjust）：\n" + "\n".join(hold_lines))

    parts.append("请基于工具获取的最新真实数据，输出 JSON 信号数组。")
    return "\n".join(parts)


class StrategyExecutor:
    """策略执行器：LLM 生成信号 → 应用到模拟持仓"""

    @staticmethod
    async def run(
        db: AsyncSession,
        strategy: BusinessAiStrategy,
        run_period: str,
        trigger_type: str = "schedule",
    ) -> StrategyRunResult:
        """执行一次策略。异常不会向上抛（记录到 Run 表），由调用方决定后续动作。"""
        from modules.strategy.schemas.strategy import EXECUTE_PERIOD_NAMES

        now = timezone.now()
        run = BusinessStrategyRun(
            strategy_id=strategy.id,
            strategy_name=strategy.name,
            run_period=run_period,
            run_date=now.strftime("%Y-%m-%d"),
            trigger_type=trigger_type,
            status=False,
        )
        db.add(run)

        try:
            # 1. 取当前持仓
            hold_result = await db.execute(
                select(BusinessStrategyPosition).where(
                    BusinessStrategyPosition.strategy_id == strategy.id,
                    BusinessStrategyPosition.status == "holding",
                    BusinessStrategyPosition.deleted_at.is_(None),
                )
            )
            holdings = list(hold_result.scalars().all())

            # 2. LLM 分析
            user_prompt = _build_user_prompt(
                strategy, holdings, EXECUTE_PERIOD_NAMES.get(run_period, run_period)
            )
            raw_text = await _run_llm(db, user_prompt)
            run.ai_raw_response = raw_text[:20000]

            # 3. 解析信号
            raw_signals = _extract_json_array(raw_text)
            signals = [s for s in (_to_signal(r) for r in raw_signals if isinstance(r, dict)) if s]
            run.parsed_signals = [s.model_dump() for s in signals]

            # 4. 应用信号
            opened, closed = await StrategyExecutor._apply_signals(db, strategy, signals, holdings)
            run.opened_count = opened
            run.closed_count = closed
            run.status = True

            strategy.last_executed_at = now
            await db.commit()
            logger.info(
                "策略执行完成: strategy=%s period=%s signals=%d opened=%d closed=%d",
                strategy.name, run_period, len(signals), opened, closed,
            )
            return StrategyRunResult(
                run_id=0, status=True, signals=signals,
                opened_count=opened, closed_count=closed,
            )
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.warning("策略执行失败: strategy=%s error=%s", strategy.name, exc)
            # 失败也要留痕（重新起一个干净对象）
            run = BusinessStrategyRun(
                strategy_id=strategy.id,
                strategy_name=strategy.name,
                run_period=run_period,
                run_date=now.strftime("%Y-%m-%d"),
                trigger_type=trigger_type,
                status=False,
                error_msg=str(exc)[:1000],
            )
            db.add(run)
            strategy.last_executed_at = now
            await db.commit()
            return StrategyRunResult(
                run_id=0, status=False, error_msg=str(exc)[:500]
            )

    # ------------------------------------------------------------------
    # 信号应用
    # ------------------------------------------------------------------
    @staticmethod
    async def _apply_signals(
        db: AsyncSession,
        strategy: BusinessAiStrategy,
        signals: list[SignalItem],
        holdings: list[BusinessStrategyPosition],
    ) -> tuple[int, int]:
        """把信号应用到模拟持仓，返回 (新建仓数, 平仓数)"""
        now = timezone.now()
        holding_map = {h.stock_code: h for h in holdings}
        opened = closed = 0

        # 批量取信号涉及个股的最新价（建仓用真实价格）
        codes = list({s.stock_code for s in signals})
        prices = await fetch_latest_prices(codes) if codes else {}

        for sig in signals:
            pos = holding_map.get(sig.stock_code)

            # ---- 买入：未持仓且还有容量 ----
            if sig.action == "buy" and pos is None:
                if len(holding_map) >= strategy.max_positions:
                    continue
                price = prices.get(sig.stock_code) or sig.buy_price
                if not price:
                    logger.warning("买入信号无法确定价格，跳过: %s", sig.stock_code)
                    continue
                pos = BusinessStrategyPosition(
                    strategy_id=strategy.id,
                    strategy_name=strategy.name,
                    stock_code=sig.stock_code,
                    stock_name=sig.stock_name or sig.stock_code,
                    buy_price=price,
                    buy_time=now,
                    buy_reason=sig.reason,
                    target_sell_price=sig.target_sell_price,
                    stop_loss_price=sig.stop_loss_price,
                    status="holding",
                    latest_price=price,
                    floating_pnl_pct=0.0,
                    tracked_at=now,
                )
                db.add(pos)
                holding_map[sig.stock_code] = pos
                opened += 1
                continue

            if pos is None:
                continue

            # ---- 卖出：直接平仓 ----
            if sig.action == "sell":
                price = prices.get(sig.stock_code) or pos.latest_price or float(pos.buy_price)
                pos.status = "closed"
                pos.sell_price = price
                pos.sell_time = now
                pos.sell_reason = "ai_signal"
                pos.latest_price = price
                pos.return_rate = round((price - float(pos.buy_price)) / float(pos.buy_price) * 100, 4)
                pos.floating_pnl_pct = pos.return_rate
                closed += 1
                continue

            # ---- 调整：更新预估卖点/止损价 ----
            if sig.action == "adjust":
                if sig.target_sell_price:
                    pos.target_sell_price = sig.target_sell_price
                if sig.stop_loss_price:
                    pos.stop_loss_price = sig.stop_loss_price

        return opened, closed
