#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 分析执行器 —— 大盘/板块分析（复用 agent 模块模型解析），
基于库内行情快照数据生成 markdown 分析报告 + 结构化摘要，
落库为 business_analysis_run 供前端展示与历史回看。

执行流程异步化（与策略执行器一致）：
1. submit_run 创建 running 状态执行记录后立即返回（HTTP 请求毫秒级响应）
2. LLM 分析在后台 asyncio 任务中进行（独立 session）
3. 数据直接取自库内日快照（指数/资金流/涨停统计/板块排行 + 近期趋势），不走 ReAct 工具循环，
   单轮生成更快更可控

分析策略可配置（business_analysis_config，每类型一条）：
- prompt_template：分析侧重点/风格等定制要求，注入 user prompt
- include_tomorrow：报告是否包含明日研判章节（默认开启）
"""
import asyncio
import json
import logging
import re
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.response.response_code import CustomErrorCode
from core.exception.errors import CustomError
from database.models.business.analysis import BusinessAnalysisRun
from database.utils.timezone import timezone
from modules.agent.services.llm_client import resolve_model, stream_chat
from modules.analysis.schemas.analysis import AnalysisConfigItem

logger = logging.getLogger(__name__)

# 后台分析整体超时（秒）：LLM 单轮流式不设总时长上限，这里兜底防止任务悬挂
ANALYSIS_TIMEOUT = 600

# 板块分析时注入 prompt 的板块数量（行业/概念各自取涨幅榜前 N）
_SECTOR_TOP_N = 15

# 大盘资金流注入 prompt 的近几日趋势
_FUND_FLOW_DAYS = 5

# 明日研判的历史数据支撑：上证指数近 N 日 / 行业板块近 N 日涨幅榜对比
_MARKET_TREND_DAYS = 10
_SECTOR_TREND_DAYS = 3
_SECTOR_TREND_TOP_N = 5

# 后台任务强引用集合（防止 asyncio.Task 被 GC），完成后自动移除
_BACKGROUND_TASKS: set[asyncio.Task] = set()

# ------------------------------------------------------------------
# 系统提示词：要求 LLM 先输出 JSON 摘要（```json 代码块），再输出 markdown 报告；
# 明日研判章节按配置动态追加
# ------------------------------------------------------------------
_MARKET_SYSTEM_PROMPT = """你是 SmileX-AI-Stock 平台的 AI 大盘分析师，负责对A股市场当日整体表现进行点评。

我会直接提供当日真实行情数据（大盘指数、近期走势、两市资金流、涨停情绪统计），禁止凭空编造数据，分析必须基于所给数据。

输出要求（严格按以下顺序，两部分缺一不可）：
1. 先输出一个 JSON 对象（包在 ```json 代码块中）：
```json
{
  "sentiment": "看多",              // 市场情绪：看多 / 中性 / 看空
  "score": 65,                     // 市场温度评分 0-100（越高越强）
  "summary": "一句话总评",          // 30 字以内
  "key_points": ["要点1", "要点2"], // 3-5 条核心观察
  "tomorrow_outlook": {            // 明日研判（未开启明日研判时省略该字段）
    "direction": "震荡偏多",        // 明日方向：看涨 / 震荡偏多 / 震荡 / 震荡偏空 / 看跌
    "summary": "一句话研判，40 字以内"
  }
}
```
2. 再输出完整的 markdown 分析报告，结构建议：
   ## 市场概览（各指数表现点评）
   ## 资金面分析（主力资金动向解读）
   ## 情绪面（涨停/连板/赚钱效应）
   ## 后市展望（机会与风险提示）

报告使用中文，条理清晰，总长度控制在 800 字以内。不构成投资建议的免责声明无需输出。
"""

_SECTOR_SYSTEM_PROMPT = """你是 SmileX-AI-Stock 平台的 AI 板块分析师，负责对A股行业与概念板块当日表现进行轮动解读。

我会直接提供当日真实板块行情数据（涨幅榜、成交额、主力净流入、领涨股、近期轮动对比），禁止凭空编造数据，分析必须基于所给数据。

输出要求（严格按以下顺序，两部分缺一不可）：
1. 先输出一个 JSON 对象（包在 ```json 代码块中）：
```json
{
  "rotation_summary": "一句话轮动总结",   // 30 字以内
  "hot_boards": [                        // 最值得关注的 3-5 个板块
    {
      "board_name": "半导体",
      "board_type": "industry",           // industry-行业 / concept-概念
      "change_pct": 3.21,                // 涨跌幅(%)
      "viewpoint": "看好理由，40 字以内"
    }
  ],
  "key_points": ["要点1", "要点2"],       // 3-5 条核心观察
  "tomorrow_outlook": {                  // 明日研判（未开启明日研判时省略该字段）
    "direction": "轮动延续",              // 明日轮动方向：轮动延续 / 高低切换 / 热点退潮 等
    "summary": "一句话研判，40 字以内"
  }
}
```
2. 再输出完整的 markdown 分析报告，结构建议：
   ## 行业板块表现（领涨行业解读）
   ## 概念题材动向（热点题材梳理）
   ## 资金主线（主力净流入方向与持续性判断）
   ## 轮动展望（后市关注方向）

报告使用中文，条理清晰，总长度控制在 800 字以内。不构成投资建议的免责声明无需输出。
"""

# 明日研判章节要求（include_tomorrow=True 时追加到系统提示词与报告结构）
_MARKET_TOMORROW_SECTION = """
## 明日研判（必须包含）
- 明日大盘方向预判（看涨/震荡/看跌）及核心理由（结合近几日趋势、资金与情绪数据）
- 关键信号位（支撑/压力参考、量能阈值、涨跌家数变化）
- 应对建议（仓位与风格取向）
"""

_SECTOR_TOMORROW_SECTION = """
## 明日轮动研判（必须包含）
- 明日板块轮动方向判断（延续/高低切换/退潮）及理由（结合近几日涨幅榜对比与资金延续性）
- 有望接力的方向与需回避的高位方向
"""


def _build_system_prompt(analysis_type: str, include_tomorrow: bool) -> str:
    """按分析类型与配置拼装系统提示词（明日研判章节按需追加）"""
    if analysis_type == "market":
        prompt = _MARKET_SYSTEM_PROMPT
        section = _MARKET_TOMORROW_SECTION
    else:
        prompt = _SECTOR_SYSTEM_PROMPT
        section = _SECTOR_TOMORROW_SECTION
    if include_tomorrow:
        prompt += (
            "\n因当前开启了「明日研判」，报告结构中追加以下章节（放在最后）：\n"
            + section
        )
    else:
        prompt += "\n当前未开启「明日研判」，报告中不要出现对明日走势的专门预判章节，JSON 中也不要输出 tomorrow_outlook 字段。\n"
    return prompt


def _extract_json_object(text: str) -> Optional[dict]:
    """从 LLM 回复中提取 JSON 对象（容忍 ```json 代码块 / 前后杂文），失败返回 None"""
    if not text:
        return None
    candidates = []
    # 优先取 ```json ... ``` 代码块
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        candidates.append(m.group(1))
    # 否则取第一个 { 到最后一个 } 之间的内容
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _dump_rows(items: list, fields: list[str]) -> list[dict]:
    """pydantic 模型列表 → 只保留指定字段的 dict 列表（date 等转字符串）"""
    rows = []
    for it in items:
        raw = it.model_dump(mode="json")
        rows.append({k: raw.get(k) for k in fields if raw.get(k) is not None})
    return rows


async def _collect_market_data(db: AsyncSession) -> str:
    """大盘分析数据收集：指数快照 + 上证近期走势 + 近几日资金流 + 涨停情绪"""
    from modules.stock.services.market_service import MarketService
    from modules.stock.services.limit_up_service import LimitUpService

    indices = await MarketService.get_indices(db)
    fund_flow = await MarketService.get_fund_flow(db, days=_FUND_FLOW_DAYS)
    limit_stats = await LimitUpService.get_stats(db)
    # 上证指数近期走势（支撑明日研判的趋势上下文；本地不足会自动回补）
    trend = []
    try:
        trend = await MarketService.get_history(db, "000001", _MARKET_TREND_DAYS)
    except Exception:
        logger.warning("上证指数近期走势获取失败（不影响分析）", exc_info=True)

    parts = [f"当前时间：{timezone.now().strftime('%Y-%m-%d %H:%M')}"]

    if indices:
        parts.append(
            "当日大盘指数快照：\n"
            + json.dumps(
                _dump_rows(
                    indices,
                    ["index_name", "latest_price", "change_pct", "amplitude", "turnover"],
                ),
                ensure_ascii=False,
            )
        )
    else:
        parts.append("当日大盘指数快照：暂无数据（可能尚未同步，请基于其他数据分析并在报告中注明）")

    if trend:
        parts.append(
            f"上证指数近 {len(trend)} 个交易日走势（研判趋势用）：\n"
            + json.dumps(
                _dump_rows(trend, ["record_date", "latest_price", "change_pct", "turnover"]),
                ensure_ascii=False,
            )
        )

    if fund_flow:
        parts.append(
            f"近 {len(fund_flow)} 日两市资金流（净流入，单位：元，负值为净流出）：\n"
            + json.dumps(
                _dump_rows(
                    fund_flow,
                    ["record_date", "main_net_inflow", "super_large_net_inflow", "small_net_inflow"],
                ),
                ensure_ascii=False,
            )
        )

    stats_raw = limit_stats.model_dump(mode="json")
    stats_fields = {
        k: stats_raw.get(k)
        for k in ("record_date", "total_count", "main_count", "chinext_count",
                  "star_count", "max_consecutive", "board_distribution")
        if stats_raw.get(k) not in (None, {}, 0)
    }
    if stats_fields:
        parts.append(f"当日涨停情绪统计：\n{json.dumps(stats_fields, ensure_ascii=False)}")

    parts.append("请基于以上真实数据输出 JSON 摘要与 markdown 大盘分析报告。")
    return "\n\n".join(parts)


async def _collect_sector_data(db: AsyncSession) -> str:
    """板块分析数据收集：行业/概念板块涨幅榜（含资金与领涨股）+ 近几日行业榜对比"""
    from modules.stock.services.board_service import BoardService

    parts = [f"当前时间：{timezone.now().strftime('%Y-%m-%d %H:%M')}"]

    fields = [
        "board_name", "change_pct", "turnover", "net_inflow",
        "rising_count", "falling_count",
        "leading_stock_name", "leading_stock_change_pct",
    ]
    industry_boards: list = []
    for board_type, label in (("industry", "行业"), ("concept", "概念")):
        boards = await BoardService.get_list(
            db, board_type=board_type, sort_by="change_pct", sort_order="desc"
        )
        if board_type == "industry":
            industry_boards = boards
        if boards:
            top = _dump_rows(boards[:_SECTOR_TOP_N], fields)
            parts.append(
                f"当日{label}板块涨幅榜 TOP{len(top)}（change_pct-涨跌幅%，turnover-成交额，"
                f"net_inflow-主力净流入，rising/falling_count-板块内涨跌家数）：\n"
                + json.dumps(top, ensure_ascii=False)
            )
        else:
            parts.append(f"当日{label}板块数据：暂无数据（可能尚未同步，请基于其他数据分析并在报告中注明）")

    # 近几日行业涨幅榜对比（支撑轮动延续性/明日研判）
    try:
        dates = await BoardService.get_dates(db, "industry")
        recent_dates = dates[:_SECTOR_TREND_DAYS] if dates else []
        trend_lines = []
        for d in recent_dates:
            day_boards = await BoardService.get_list(
                db, board_type="industry", record_date=str(d),
                sort_by="change_pct", sort_order="desc",
            )
            if day_boards:
                names = [
                    f"{b.board_name} {float(b.change_pct):+.2f}%"
                    for b in day_boards[:_SECTOR_TREND_TOP_N]
                ]
                trend_lines.append(f"{d}：{'、'.join(names)}")
        if trend_lines:
            parts.append(
                f"近 {_SECTOR_TREND_DAYS} 个交易日行业涨幅榜 TOP{_SECTOR_TREND_TOP_N} 对比（观察轮动延续性）：\n"
                + "\n".join(trend_lines)
            )
    except Exception:
        logger.warning("行业板块近期对比获取失败（不影响分析）", exc_info=True)

    parts.append("请基于以上真实数据输出 JSON 摘要与 markdown 板块轮动分析报告。")
    return "\n\n".join(parts)


async def _run_llm(
    db: AsyncSession,
    analysis_type: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """单轮 LLM 调用（复用 agent 的模型解析，数据已注入 prompt，无需工具循环）"""
    from database.models.sys.ai_model import AiFunctionEnum

    resolved = await resolve_model(db, AiFunctionEnum.TREND_PREDICTION)
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    final_text = ""
    async for chunk in stream_chat(resolved, messages):
        if chunk.content:
            final_text += chunk.content
    return final_text


def _build_user_prompt(
    analysis_type: str,
    data_prompt: str,
    config: AnalysisConfigItem,
) -> str:
    """数据 + 分析策略配置 → user prompt"""
    parts = [data_prompt]
    if config.prompt_template:
        parts.append(
            f"分析策略要求（用户定制，生成时必须遵循）：\n{config.prompt_template}"
        )
    return "\n\n".join(parts)


class AnalysisExecutor:
    """AI 大盘/板块分析执行器：submit_run 落库即返回，LLM 分析在后台任务中进行"""

    @staticmethod
    async def submit_run(
        db: AsyncSession,
        analysis_type: str,
        trigger_type: str = "schedule",
    ) -> int:
        """提交一次分析：创建 running 状态执行记录并立即返回 run_id，
        LLM 分析在后台 asyncio 任务中进行（独立 session，只传 id 不传 ORM 实例）。

        并发守卫：同类型已存在 running 记录时抛 ANALYSIS_ALREADY_RUNNING。
        """
        dup = await db.execute(
            select(BusinessAnalysisRun.id).where(
                BusinessAnalysisRun.analysis_type == analysis_type,
                BusinessAnalysisRun.status == "running",
                BusinessAnalysisRun.deleted_at.is_(None),
            ).limit(1)
        )
        if dup.scalar_one_or_none() is not None:
            raise CustomError(
                error=CustomErrorCode.ANALYSIS_ALREADY_RUNNING,
                msg="该分析正在生成中，请稍后再试",
            )

        now = timezone.now()
        run = BusinessAnalysisRun(
            analysis_type=analysis_type,
            run_date=now.strftime("%Y-%m-%d"),
            trigger_type=trigger_type,
            status="running",
        )
        db.add(run)
        await db.commit()  # expire_on_commit=False，flush 后 run.id 可直接取用

        task = asyncio.create_task(
            AnalysisExecutor._execute_analysis(run.id, analysis_type)
        )
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)
        logger.info(
            "已提交 AI 分析: type=%s run_id=%s trigger=%s",
            analysis_type, run.id, trigger_type,
        )
        return run.id

    # ------------------------------------------------------------------
    # 后台分析
    # ------------------------------------------------------------------
    @staticmethod
    async def _execute_analysis(run_id: int, analysis_type: str) -> None:
        """后台分析入口：独立 session + 整体超时兜底，任何异常都回写 Run 失败状态"""
        from database.db_manager import get_session

        async for db in get_session():
            try:
                await asyncio.wait_for(
                    AnalysisExecutor._analyze(db, run_id, analysis_type),
                    timeout=ANALYSIS_TIMEOUT,
                )
            except Exception as exc:  # noqa: BLE001  含 TimeoutError
                if isinstance(exc, asyncio.TimeoutError):
                    err_text = f"分析执行超时（超过 {ANALYSIS_TIMEOUT} 秒）"
                else:
                    # 项目异常（CustomError 等）消息在 .msg 属性，str(exc) 可能为空
                    err_text = str(getattr(exc, "msg", None) or exc)
                logger.warning("AI 后台分析失败: run_id=%s error=%s", run_id, err_text)
                try:
                    await db.rollback()
                    await db.execute(
                        update(BusinessAnalysisRun)
                        .where(BusinessAnalysisRun.id == run_id)
                        .values(status="failed", error_msg=err_text[:1000])
                        .execution_options(synchronize_session=False)
                    )
                    await db.commit()
                except Exception:  # noqa: BLE001
                    logger.exception("回写失败分析记录异常: run_id=%s", run_id)

    @staticmethod
    async def _analyze(db: AsyncSession, run_id: int, analysis_type: str) -> None:
        """分析主体：读取策略配置 -> 收集库内数据 -> LLM 生成报告 -> 解析 JSON 摘要 -> 回写成功"""
        from modules.analysis.services.analysis_config_service import AnalysisConfigService

        run_result = await db.execute(
            select(BusinessAnalysisRun).where(
                BusinessAnalysisRun.id == run_id,
                BusinessAnalysisRun.deleted_at.is_(None),
            )
        )
        run = run_result.scalar_one_or_none()
        if run is None:
            logger.warning("分析执行记录不存在，放弃分析: run_id=%s", run_id)
            return

        # 1. 读取分析策略配置（无记录按默认：无定制提示词、明日研判开启）
        config = await AnalysisConfigService.get_effective(db, analysis_type)

        # 2. 收集数据（部分数据源失败不阻塞，prompt 中会注明缺失）
        if analysis_type == "market":
            data_prompt = await _collect_market_data(db)
        else:
            data_prompt = await _collect_sector_data(db)

        # 3. LLM 生成（系统提示词按明日研判开关动态拼装）
        system_prompt = _build_system_prompt(analysis_type, config.include_tomorrow)
        user_prompt = _build_user_prompt(analysis_type, data_prompt, config)
        raw_text = await _run_llm(db, analysis_type, system_prompt, user_prompt)
        run.ai_raw_response = raw_text[:20000]

        # 4. 解析 JSON 摘要（失败不影响报告本身，仅摘要为空；
        #    关闭明日研判时丢弃 LLM 可能误输出的 tomorrow_outlook）
        parsed = _extract_json_object(raw_text)
        if parsed is not None and not config.include_tomorrow:
            parsed.pop("tomorrow_outlook", None)
        run.parsed_result = parsed

        run.status = "success"
        await db.commit()
        logger.info(
            "AI 分析完成: type=%s run_id=%s parsed=%s tomorrow=%s",
            analysis_type, run_id, parsed is not None, config.include_tomorrow,
        )
