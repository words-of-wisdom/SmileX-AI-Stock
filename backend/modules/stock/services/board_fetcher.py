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
from modules.stock.services.market_fetcher import FUND_FLOW_RETRY_DELAY

logger = logging.getLogger(__name__)

_QQ_GETRANK_URL = "https://proxy.finance.qq.com/cgi/cgi-bin/rank/pt/getRank"
_QQ_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
}
_EM_CLIST_HOSTS = (
    "push2.eastmoney.com",       # 实时行情（主）
    "push2delay.eastmoney.com",  # 延时行情（实时源 IP 限流时降级，收盘后同步数据无差异）
)
# 板块内个股涨幅榜并发上限与单请求间隔：push2 对高频请求有 IP 级封禁，概念板块量大需限速
_EM_TOP_STOCKS_CONCURRENCY = 5
_EM_TOP_STOCKS_INTERVAL = 0.1
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


def _single_leading_item(code, name, change_pct) -> list[dict]:
    """兜底数据源只提供单只领涨股时，包装为 leading_stocks 单元素列表"""
    if not name:
        return []
    return [{"code": code or None, "name": name, "change_pct": change_pct}]


async def _pick_em_clist_url(client: httpx.AsyncClient) -> str:
    """探测可用的东财行情 clist 接口地址：逐域名试探，实时源被 IP 限流时降级延时源"""
    params = {"pn": 1, "pz": 1, "po": 1, "np": 1, "fltt": 2, "invt": 2,
              "fid": "f3", "fs": "b:BK0475", "fields": "f12"}
    last_error: Exception | None = None
    for host in _EM_CLIST_HOSTS:
        url = f"https://{host}/api/qt/clist/get"
        try:
            resp = await client.get(url, params=params)
            if resp.json().get("rc") == 0:
                return url
        except Exception as e:  # noqa: BLE001
            last_error = e
    raise RuntimeError(f"东财 clist 接口全部不可用: {last_error}")


async def _fetch_board_leading_stocks_em(
    client: httpx.AsyncClient, clist_url: str, board_code: str, top_n: int = 3
) -> list[dict]:
    """东财 push2 板块内个股涨幅榜，返回前 top_n 名 [{code, name, change_pct}]

    板块列表接口的领涨股列只有名称无代码，需按板块逐个补抓成分涨幅前三。
    """
    resp = await client.get(
        clist_url,
        params={
            "pn": 1,
            "pz": top_n,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",  # 按涨跌幅降序
            "fs": f"b:{board_code}",
            "fields": "f12,f14,f3",
        },
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("rc") != 0:
        raise RuntimeError(f"东财板块个股榜返回错误: {payload.get('rt')}")
    diff = (payload.get("data") or {}).get("diff") or []
    items = []
    for d in diff:
        name = str(d.get("f14", "")).strip()
        if not name:
            continue
        items.append({
            "code": normalize_code(d.get("f12")) or None,
            "name": name,
            "change_pct": num(d.get("f3")),
        })
    return items


async def _enrich_leading_stocks(items: list[dict]) -> None:
    """为东财板块列表补抓每个板块的领涨股前三名（含代码）

    单板块失败不影响整体，回退为列表自带单只领涨股（名称无代码）；
    补抓成功时用 top1 回填旧三字段，补齐东财源缺失的领涨股代码。
    """
    sem = asyncio.Semaphore(_EM_TOP_STOCKS_CONCURRENCY)

    async with httpx.AsyncClient(timeout=10, headers=_QQ_HEADERS) as client:
        # 域名探测一次：实时源被限流时整批切到延时源，避免逐板块重复探测
        clist_url = await _pick_em_clist_url(client)

        async def _enrich_one(it: dict) -> None:
            async with sem:
                try:
                    leading = await _fetch_board_leading_stocks_em(client, clist_url, it["board_code"])
                except Exception as e:
                    logger.warning(
                        "板块领涨股前三名抓取失败(%s %s): %s",
                        it["board_code"], it["board_name"], e,
                    )
                    leading = []
                await asyncio.sleep(_EM_TOP_STOCKS_INTERVAL)
            if leading:
                it["leading_stocks"] = leading
                top1 = leading[0]
                it["leading_stock_code"] = top1["code"]
                it["leading_stock_name"] = top1["name"]
                it["leading_stock_change_pct"] = top1["change_pct"]
            else:
                it["leading_stocks"] = _single_leading_item(
                    it.get("leading_stock_code"),
                    it.get("leading_stock_name"),
                    it.get("leading_stock_change_pct"),
                )

        await asyncio.gather(*(_enrich_one(it) for it in items))


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
            # 领涨股票列是名称不是代码，代码字段留空，随后 _enrich_leading_stocks 补齐
            "leading_stock_code": None,
            "leading_stock_name": str(row.get("领涨股票", "")).strip() or None,
            "leading_stock_change_pct": num(row.get("领涨股票-涨跌幅")),
        })
    if not items:
        raise RuntimeError(f"东财板块列表为空({board_type})")

    # 逐板块补抓领涨股前三名（含代码），失败时回退列表自带单只领涨股
    await _enrich_leading_stocks(items)
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
        leading_name = str(row.get("领涨股", "")).strip() or None
        leading_pct = num(row.get("涨跌幅(%).1"))
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
            "leading_stock_name": leading_name,
            "leading_stock_change_pct": leading_pct,
            # 同花顺列表领涨股仅名称无代码
            "leading_stocks": _single_leading_item(None, leading_name, leading_pct),
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
                leading_code = normalize_code(leading.get("code")) or None
                leading_name = str(leading.get("name", "")).strip() or None
                leading_pct = num(leading.get("zdf"))
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
                    "leading_stock_code": leading_code,
                    "leading_stock_name": leading_name,
                    "leading_stock_change_pct": leading_pct,
                    # 腾讯源领涨股仅单只，但自带代码
                    "leading_stocks": _single_leading_item(leading_code, leading_name, leading_pct),
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
    """抓取板块资金流排行，返回 {board_name: net_inflow} 映射

    东财单源无兜底，被限流时退避重试一次，仍失败返回空映射（净流入留空）
    """
    import akshare as ak

    indicator = "今日"
    sector_type = "行业资金流" if board_type == "industry" else "概念资金流"

    df = None
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            df = await asyncio.to_thread(
                ak.stock_sector_fund_flow_rank,
                indicator=indicator,
                sector_type=sector_type,
            )
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt == 0:
                logger.warning("板块资金流抓取失败(%s)，%ds 后重试一次", sector_type, FUND_FLOW_RETRY_DELAY)
                await asyncio.sleep(FUND_FLOW_RETRY_DELAY)
    if df is None:
        logger.warning("板块资金流抓取最终失败(%s): %s", sector_type, last_exc)
        return {}

    result = {}
    flow_col = "今日主力净流入-净额" if "今日主力净流入-净额" in df.columns else "主力净流入-净额"
    for _, row in df.iterrows():
        name = str(row.get("名称", "")).strip()
        if name:
            result[name] = num(row.get(flow_col))
    return result
