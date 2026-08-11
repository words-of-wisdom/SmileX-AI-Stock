#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
行业/概念板块抓取层
数据源降级链：
- 行业：akshare-东财（主源，含换手率/涨跌家数）→ 腾讯板块排行（兜底，含换手率/成交额/净流入/涨跌家数）→ 同花顺（末级兜底，无换手率）
- 概念：akshare-东财（主源）→ 腾讯板块排行（兜底，同花顺无概念行情列表）
- 东财 push2 接口对高频请求有 IP 级封禁，异常/限流时自动降级
- 腾讯板块排行（getRank）字段完整但分类体系为申万行业（hy2=申万二级）/腾讯概念，
  与东财板块代码体系不同，跨源快照不可混用对比
"""
import asyncio
import io
import logging

import httpx

from modules.stock.services._common import num, normalize_code

logger = logging.getLogger(__name__)

_QQ_GETRANK_URL = "https://proxy.finance.qq.com/cgi/cgi-bin/rank/pt/getRank"
_QQ_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
}
_THS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"
)
_THS_RANK_URL = "http://q.10jqka.com.cn/thshy/index/field/199112/order/desc/page/{page}/ajax/1/"


def _pick(row, *keys):
    """从 DataFrame 行中按候选列名取第一个非空值"""
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return None


async def fetch_board_list(board_type: str) -> list[dict]:
    """抓取板块列表（行业或概念），按降级链自动切换数据源

    Args:
        board_type: "industry" 或 "concept"
    """
    try:
        return await _fetch_board_list_em(board_type)
    except Exception as e:
        logger.warning("东财板块列表抓取失败(%s)，降级腾讯板块排行: %s", board_type, e)
    try:
        return await _fetch_board_list_qq(board_type)
    except Exception as e:
        logger.warning("腾讯板块排行抓取失败(%s)，尝试降级: %s", board_type, e)
    if board_type == "industry":
        return await _fetch_board_list_ths()
    raise RuntimeError(f"板块列表数据源全部不可用({board_type})")


async def _fetch_board_list_em(board_type: str) -> list[dict]:
    """东财主源：板块实时行情列表（akshare stock_board_*_name_em）"""
    import akshare as ak

    if board_type == "industry":
        df = await asyncio.to_thread(ak.stock_board_industry_name_em)
    else:
        df = await asyncio.to_thread(ak.stock_board_concept_name_em)

    items = []
    for _, row in df.iterrows():
        board_code = str(row.get("板块代码", row.get("排名", ""))).strip()
        board_name = str(row.get("板块名称", "")).strip()
        if not board_code:
            board_code = board_name

        items.append({
            "board_type": board_type,
            "board_code": board_code,
            "board_name": board_name,
            "change_pct": num(row.get("涨跌幅")),
            # 东财板块列表接口不提供成交额/成交量，置空而非错用总市值
            "turnover": None,
            "turnover_rate": num(row.get("换手率")),
            "volume": None,
            "rising_count": num(row.get("上涨家数")),
            "falling_count": num(row.get("下跌家数")),
            # 领涨股票列是名称不是代码，代码字段留空
            "leading_stock_code": None,
            "leading_stock_name": str(row.get("领涨股票", "")).strip() or None,
            "leading_stock_change_pct": num(row.get("领涨股票-涨跌幅")),
        })
    if not items:
        raise RuntimeError(f"东财板块列表为空({board_type})")
    return items


def _ths_v_code() -> str:
    """执行同花顺反爬 JS 生成 v cookie（hexin-v）"""
    import py_mini_racer
    from akshare.datasets import get_ths_js

    js = py_mini_racer.MiniRacer()
    with open(get_ths_js("ths.js"), encoding="utf-8") as f:
        js.eval(f.read())
    return js.call("v")


def _fetch_board_list_ths_sync() -> list[dict]:
    """同花顺行业板块一览表（同步实现，供 asyncio.to_thread 调用）

    页面含成交额/净流入/上涨家数/下跌家数/领涨股，无换手率与股票代码。
    同花顺对 v cookie 校验严格，必须走 http 且每次请求刷新 v 值。
    """
    import pandas as pd
    from bs4 import BeautifulSoup

    import akshare as ak

    name_code_map = {
        str(r["name"]).strip(): str(r["code"]).strip()
        for _, r in ak.stock_board_industry_name_ths().iterrows()
    }

    def _get(page: int) -> str:
        v = _ths_v_code()
        resp = httpx.get(
            _THS_RANK_URL.format(page=page),
            headers={"User-Agent": _THS_UA, "Cookie": f"v={v}"},
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text

    first_html = _get(1)
    page_info = BeautifulSoup(first_html, features="lxml").find(
        name="span", attrs={"class": "page_info"}
    )
    total_pages = int(page_info.text.split("/")[1]) if page_info else 1

    frames = [pd.read_html(io.StringIO(first_html))[0]]
    for page in range(2, total_pages + 1):
        frames.append(pd.read_html(io.StringIO(_get(page)))[0])
    df = pd.concat(frames, ignore_index=True)
    # pandas 对重名列自动加 .1 后缀：涨跌幅(%).1 是领涨股涨跌幅
    df.columns = [str(c).strip() for c in df.columns]

    items = []
    for _, row in df.iterrows():
        board_name = str(row.get("板块", "")).strip()
        if not board_name:
            continue
        turnover = num(row.get("总成交额（亿元）"))
        net_inflow = num(row.get("净流入（亿元）"))
        volume = num(row.get("总成交量（万手）"))
        items.append({
            "board_type": "industry",
            "board_code": name_code_map.get(board_name, board_name),
            "board_name": board_name,
            "change_pct": num(row.get("涨跌幅(%)")),
            "turnover": turnover * 1e8 if turnover is not None else None,
            # 同花顺列表无换手率
            "turnover_rate": None,
            "volume": volume * 1e4 if volume is not None else None,
            "net_inflow": net_inflow * 1e8 if net_inflow is not None else None,
            "rising_count": num(row.get("上涨家数")),
            "falling_count": num(row.get("下跌家数")),
            "leading_stock_code": None,
            "leading_stock_name": str(row.get("领涨股", "")).strip() or None,
            "leading_stock_change_pct": num(row.get("涨跌幅(%).1")),
        })
    if not items:
        raise RuntimeError("同花顺行业板块列表为空")
    return items


async def _fetch_board_list_ths() -> list[dict]:
    return await asyncio.to_thread(_fetch_board_list_ths_sync)


async def _fetch_board_list_qq(board_type: str) -> list[dict]:
    """腾讯板块排行兜底：getRank 接口（行业 hy2=申万二级 / 概念 gn）

    字段比 mktHs 行情排行完整：换手率(hsl)/成交额(turnover)/成交量(volume)/
    主力净流入(zljlr)/涨跌家数(zgb "涨/跌")/领涨股(lzg)。
    金额单位为万元，入库前换算为元；成交量单位为手。
    """
    qq_board_type = "hy2" if board_type == "industry" else "gn"

    items: list[dict] = []
    async with httpx.AsyncClient(timeout=15, headers=_QQ_HEADERS) as client:
        offset = 0
        page_size = 100
        while True:
            resp = await client.get(
                _QQ_GETRANK_URL,
                params={
                    "board_type": qq_board_type,
                    "sort_type": "turnover",
                    "direct": "down",
                    "offset": offset,
                    "count": page_size,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("data") or {}
            if payload.get("code") != 0 or not isinstance(data, dict):
                raise RuntimeError(f"腾讯板块排行返回错误: {payload.get('msg')}")
            rows = data.get("rank_list") or []
            for row in rows:
                board_code = str(row.get("code", "")).strip()
                board_name = str(row.get("name", "")).strip()
                if not board_code or not board_name:
                    continue
                turnover = num(row.get("turnover"))
                net_inflow = num(row.get("zljlr"))
                rising_count, falling_count = None, None
                breadth = str(row.get("zgb") or "")
                if "/" in breadth:
                    up, down = breadth.split("/", 1)
                    rising_count, falling_count = num(up), num(down)
                leading = row.get("lzg") or {}
                items.append({
                    "board_type": board_type,
                    "board_code": board_code,
                    "board_name": board_name,
                    "change_pct": num(row.get("zdf")),
                    "turnover": turnover * 1e4 if turnover is not None else None,
                    "turnover_rate": num(row.get("hsl")),
                    "volume": num(row.get("volume")),
                    "net_inflow": net_inflow * 1e4 if net_inflow is not None else None,
                    "rising_count": int(rising_count) if rising_count is not None else None,
                    "falling_count": int(falling_count) if falling_count is not None else None,
                    "leading_stock_code": normalize_code(leading.get("code")) or None,
                    "leading_stock_name": str(leading.get("name", "")).strip() or None,
                    "leading_stock_change_pct": num(leading.get("zdf")),
                })
            offset += len(rows)
            total = num(data.get("total")) or 0
            if not rows or offset >= total:
                break
            await asyncio.sleep(0.5)

    if not items:
        raise RuntimeError(f"腾讯板块排行为空({board_type})")
    return items


async def fetch_board_fund_flow(board_type: str) -> dict[str, float | None]:
    """抓取板块资金流排行，返回 {board_name: net_inflow} 映射"""
    import akshare as ak

    indicator = "今日"
    sector_type = "行业资金流" if board_type == "industry" else "概念资金流"

    try:
        df = await asyncio.to_thread(
            ak.stock_sector_fund_flow_rank,
            indicator=indicator,
            sector_type=sector_type,
        )
    except Exception as exc:
        logger.warning("板块资金流抓取失败(%s): %s", sector_type, exc)
        return {}

    result = {}
    flow_col = "今日主力净流入-净额" if "今日主力净流入-净额" in df.columns else "主力净流入-净额"
    for _, row in df.iterrows():
        name = str(row.get("名称", "")).strip()
        if name:
            result[name] = num(row.get(flow_col))
    return result
