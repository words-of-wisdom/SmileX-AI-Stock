#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大盘指数抓取层
数据源降级链：akshare-东财（实时主源）→ baostock（日线兜底）→ akshare-新浪（末级兜底）
- 东财接口异常/限流时自动降级，保证同步链路可用
- baostock 不覆盖科创50（000688），缺口由新浪源补齐
- 兜底源均为日线（盘后更新），非实时
"""
import asyncio
import logging
from datetime import date, timedelta

from modules.stock.services._baostock import fetch_index_daily_bars
from modules.stock.services._common import num

logger = logging.getLogger(__name__)

# 需要追踪的主要指数（东财代码格式）
TRACKED_INDICES = [
    {"code": "000001", "name": "上证指数"},
    {"code": "399001", "name": "深证成指"},
    {"code": "399006", "name": "创业板指"},
    {"code": "000688", "name": "科创50"},
    {"code": "000300", "name": "沪深300"},
    {"code": "000905", "name": "中证500"},
    {"code": "000852", "name": "中证1000"},
]


def _pick(df_row, *keys):
    """从 DataFrame 行中按候选列名取第一个非空值"""
    for k in keys:
        if k in df_row and df_row[k] is not None:
            return df_row[k]
    return None


async def fetch_index_spot() -> list[dict]:
    """抓取主要指数实时行情，akshare 失败时自动降级 baostock 最近日线

    返回标准化 dict 列表，字段：
        index_code / index_name / latest_price / change_pct / change_amount /
        volume / turnover / amplitude / high / low / open / prev_close
    baostock 降级时额外携带 record_date（数据真实所属交易日）
    """
    try:
        return await _fetch_index_spot_akshare()
    except Exception as e:
        logger.warning("akshare 指数实时行情抓取失败，降级 baostock: %s", e)
        return await _fetch_index_spot_baostock()


async def _fetch_index_spot_akshare() -> list[dict]:
    """akshare 主源：东财指数实时行情（stock_zh_index_spot_em）"""
    import akshare as ak

    df = await asyncio.to_thread(ak.stock_zh_index_spot_em, symbol="指数成份")
    # 筛选我们关注的指数
    tracked_codes = {it["code"] for it in TRACKED_INDICES}
    tracked_names = {it["code"]: it["name"] for it in TRACKED_INDICES}

    items = []
    for _, row in df.iterrows():
        raw_code = str(row.get("代码", "")).strip()
        if raw_code not in tracked_codes:
            continue
        items.append({
            "index_code": raw_code,
            "index_name": tracked_names.get(raw_code, str(row.get("名称", raw_code))),
            "latest_price": num(row.get("最新价")),
            "change_pct": num(row.get("涨跌幅")),
            "change_amount": num(row.get("涨跌额")),
            "volume": num(row.get("成交量")),
            "turnover": num(row.get("成交额")),
            "amplitude": num(row.get("振幅")),
            "high": num(row.get("最高")),
            "low": num(row.get("最低")),
            "open": num(row.get("今开")),
            "prev_close": num(row.get("昨收")),
        })

    if not items:
        raise RuntimeError("akshare 未返回任何关注的指数数据")
    return items


async def _fetch_index_spot_baostock() -> list[dict]:
    """兜底源：取各指数最近一个交易日的日线 bar 作为快照（盘后数据，非实时）

    baostock 为主（含成交额/涨跌幅）；其不覆盖的指数（如科创50 000688）由新浪日线补齐
    """
    end = date.today()
    start = end - timedelta(days=15)
    start_s, end_s = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    bars_map = await fetch_index_daily_bars(
        [it["code"] for it in TRACKED_INDICES], start_s, end_s
    )
    names = {it["code"]: it["name"] for it in TRACKED_INDICES}
    items = []
    for code, bars in bars_map.items():
        if not bars:
            continue
        items.append({"index_code": code, "index_name": names.get(code, code), **bars[-1]})

    # 新浪源补齐 baostock 缺失的指数
    covered = {it["index_code"] for it in items}
    for it in TRACKED_INDICES:
        if it["code"] in covered:
            continue
        try:
            bars = await _fetch_index_history_sina(it["code"], start_s, end_s)
        except Exception as e:
            logger.warning("sina 指数行情兜底失败(code=%s): %s", it["code"], e)
            continue
        if bars:
            items.append({"index_code": it["code"], "index_name": it["name"], **bars[-1]})

    if not items:
        raise RuntimeError("akshare/baostock/sina 均未获取到指数数据")
    return items


async def fetch_index_history(index_code: str, start_date: str, end_date: str) -> list[dict]:
    """抓取单指数日线历史，akshare 失败时自动降级 baostock

    Args:
        index_code: 纯数字指数代码，如 "000001"
        start_date: "YYYYMMDD"
        end_date: "YYYYMMDD"
    """
    try:
        items = await _fetch_index_history_akshare(index_code, start_date, end_date)
        if items:
            return items
        logger.warning("akshare-em 指数历史为空(code=%s)，降级 baostock", index_code)
    except Exception as e:
        logger.warning("akshare 指数历史抓取失败(code=%s)，降级 baostock: %s", index_code, e)
    try:
        bars = (await fetch_index_daily_bars([index_code], start_date, end_date)).get(index_code, [])
        if bars:
            return bars
        logger.warning("baostock 指数历史为空(code=%s)，降级 sina", index_code)
    except Exception as e:
        logger.warning("baostock 指数历史抓取失败(code=%s)，降级 sina: %s", index_code, e)
    return await _fetch_index_history_sina(index_code, start_date, end_date)


async def _fetch_index_history_akshare(index_code: str, start_date: str, end_date: str) -> list[dict]:
    """akshare 主源：东财指数日线历史（stock_zh_index_daily_em）"""
    import akshare as ak

    # akshare 需要带交易所前缀：沪市 0/5 开头用 sh，深市 3/1 开头用 sz
    if index_code.startswith(("0", "5")):
        symbol = f"sh{index_code}"
    else:
        symbol = f"sz{index_code}"

    df = await asyncio.to_thread(
        ak.stock_zh_index_daily_em,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )
    items = []
    for _, row in df.iterrows():
        items.append({
            "record_date": row.get("date"),
            "latest_price": num(row.get("close")),
            "open": num(row.get("open")),
            "high": num(row.get("high")),
            "low": num(row.get("low")),
            "volume": num(row.get("volume")),
            "turnover": num(row.get("amount")),
            # 日线涨跌幅从 close 差分计算，akshare 返回不带
        })

    # 计算 change_pct
    for i, item in enumerate(items):
        if i > 0 and items[i - 1]["latest_price"] and item["latest_price"]:
            prev = items[i - 1]["latest_price"]
            item["change_pct"] = round((item["latest_price"] - prev) / prev * 100, 4)
            item["prev_close"] = prev
        else:
            item["change_pct"] = None
            item["prev_close"] = None

    return items


async def _fetch_index_history_sina(index_code: str, start_date: str, end_date: str) -> list[dict]:
    """akshare-新浪末级兜底：指数日线（stock_zh_index_daily）

    覆盖科创50等 baostock 缺失的指数；无成交额字段（turnover 置 None）
    """
    import akshare as ak

    if index_code.startswith(("0", "5")):
        symbol = f"sh{index_code}"
    else:
        symbol = f"sz{index_code}"

    df = await asyncio.to_thread(ak.stock_zh_index_daily, symbol=symbol)
    if df is None or df.empty:
        return []

    start_d, end_d = date.fromisoformat(_iso(start_date)), date.fromisoformat(_iso(end_date))
    items = []
    for _, row in df.iterrows():
        d = row.get("date")
        d = d.date() if hasattr(d, "date") else d
        if not isinstance(d, date) or d < start_d or d > end_d:
            continue
        items.append({
            "record_date": d.isoformat(),
            "latest_price": num(row.get("close")),
            "open": num(row.get("open")),
            "high": num(row.get("high")),
            "low": num(row.get("low")),
            "volume": num(row.get("volume")),
            "turnover": None,
        })

    # 新浪源不带涨跌幅/昨收，从 close 差分计算
    for i, item in enumerate(items):
        if i > 0 and items[i - 1]["latest_price"] and item["latest_price"]:
            prev = items[i - 1]["latest_price"]
            item["change_pct"] = round((item["latest_price"] - prev) / prev * 100, 4)
            item["prev_close"] = prev
            item["change_amount"] = round(item["latest_price"] - prev, 4)
        else:
            item["change_pct"] = None
            item["prev_close"] = None
    return items


def _iso(d: str) -> str:
    """YYYYMMDD -> YYYY-MM-DD"""
    d = d.strip()
    return f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 and "-" not in d else d
