#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻聚合抓取层
统一封装 16 个新闻源的抓取逻辑，返回标准化的 dict 列表。
每个 dict 包含：title / url / summary / content / source / source_name / author / raw_time
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Callable

import httpx

from database.utils.timezone import timezone

logger = logging.getLogger(__name__)

# 新闻抓取统一请求头
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


def parse_news_time(raw: str | None, now: datetime | None = None) -> datetime | None:
    """将各种相对/绝对时间字符串归一化为本地时区 datetime。

    支持格式：刚刚 / X分钟前 / X小时前 / 昨天 HH:MM / MM月DD日 HH:MM /
    YYYY-MM-DD HH:MM:SS / MM-DD HH:MM（自动补全年份）
    """
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    now = now or timezone.now()

    if raw == "刚刚":
        return now

    m = re.match(r"^(\d+)\s*分钟前$", raw)
    if m:
        return now - timedelta(minutes=int(m.group(1)))

    m = re.match(r"^(\d+)\s*小时前$", raw)
    if m:
        return now - timedelta(hours=int(m.group(1)))

    m = re.match(r"^昨天\s*(\d{1,2}):(\d{1,2})$", raw)
    if m:
        yesterday = now.date() - timedelta(days=1)
        return timezone.now().replace(
            year=yesterday.year, month=yesterday.month, day=yesterday.day,
            hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0,
        )

    # MM月DD日 HH:MM
    m = re.match(r"^(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{1,2})$", raw)
    if m:
        month, day, hour, minute = (int(m.group(i)) for i in range(1, 5))
        year = now.year
        try:
            dt = timezone.now().replace(
                year=year, month=month, day=day, hour=hour, minute=minute,
                second=0, microsecond=0,
            )
            if dt > now + timedelta(minutes=5):
                dt = dt.replace(year=year - 1)
            return dt
        except ValueError:
            return None

    # 标准格式 YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD HH:MM
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return timezone.from_str(raw, fmt)
        except ValueError:
            continue

    # 无年份 MM-DD HH:MM（自动补全年份）
    m = re.match(r"^(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2})$", raw)
    if m:
        month, day, hour, minute = (int(m.group(i)) for i in range(1, 5))
        year = now.year
        try:
            dt = timezone.now().replace(
                year=year, month=month, day=day, hour=hour, minute=minute,
                second=0, microsecond=0,
            )
            if dt > now + timedelta(minutes=5):
                dt = dt.replace(year=year - 1)
            return dt
        except ValueError:
            return None

    return None


def _strip_html(text: str | None) -> str | None:
    """去除 HTML 标签"""
    if not text:
        return text
    return re.sub(r"<[^>]+>", "", text).strip() or None


def _item(title, url, source, source_name, summary=None, content=None, author=None, raw_time=None) -> dict:
    """构造标准化新闻 dict"""
    if not title or not url:
        return {}
    return {
        "title": _strip_html(title) or title,
        "url": url,
        "summary": _strip_html(summary)[:1000] if summary else None,
        "content": content,
        "source": source,
        "source_name": source_name,
        "author": author,
        "raw_time": raw_time,
    }


# ================================================================
# 东方财富
# ================================================================
async def _fetch_eastmoney(client: httpx.AsyncClient, page_size: int) -> list[dict]:
    url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
    params = {"client": "web", "biz": "web_news_col", "column": "350", "page_size": page_size, "last_time": ""}
    resp = await client.get(url, params=params, timeout=10)
    data = resp.json().get("data", {}).get("list", [])
    items = []
    for row in data:
        art = row.get("Art_ShowTime") or row.get("Art_PublishTime")
        items.append(_item(
            title=row.get("Art_Title"),
            url=row.get("Art_UniqueUrl") or row.get("url"),
            source="eastmoney", source_name="东方财富",
            summary=row.get("Art_Summary") or row.get("Art_Description"),
            raw_time=str(art) if art else None,
        ))
    return items


async def _fetch_eastmoney_global(client: httpx.AsyncClient, page_size: int) -> list[dict]:
    url = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"
    params = {"client": "web", "biz": "web_724", "fastColumn": "102", "sortEnd": "", "pageSize": page_size}
    resp = await client.get(url, params=params, timeout=10)
    data = resp.json().get("data", {}).get("list", [])
    items = []
    for row in data:
        items.append(_item(
            title=row.get("title"),
            url=row.get("url_w") or row.get("url"),
            source="eastmoney_global", source_name="7x24全球",
            summary=row.get("digest"),
            raw_time=row.get("showtime"),
        ))
    return items


# ================================================================
# 财联社（含签名，同一端点不同分类）
# ================================================================
_CLS_URL = "https://www.cls.cn/v1/roll/get_roll_list"


def _cls_sign(app_name: str = "cls") -> dict:
    """财联社请求所需签名/请求头。这里复用公开的固定签名参数。"""
    return {
        "Referer": "https://www.cls.cn/telegraph",
        "Par-Id": "",
        "Psp-Status": "1",
        "Psp-Time": str(int(datetime.now().timestamp() * 1000)),
        "App-info": "Cl5627477/9.5.6",
    }


async def _fetch_cls(client: httpx.AsyncClient, page_size: int, key: str, name: str, cat: str) -> list[dict]:
    params = {"app": "CailianpressWeb", "category": cat, "os": "web", "sv": "8.4.6", "rn": page_size, "last_time": ""}
    resp = await client.get(_CLS_URL, params=params, headers=_cls_sign(), timeout=10)
    data = resp.json().get("data", {}).get("roll_data", [])
    items = []
    for row in data:
        ctime = row.get("ctime")
        raw_time = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S") if ctime else None
        items.append(_item(
            title=row.get("title") or _strip_html(row.get("content", ""))[:80],
            url=f"https://www.cls.cn/detail/{row.get('id')}",
            source=key, source_name=name,
            summary=_strip_html(row.get("content")),
            content=row.get("content"),
            author=row.get("sharedata", {}).get("weibo") if isinstance(row.get("sharedata"), dict) else None,
            raw_time=raw_time,
        ))
    return items


def _make_cls_fetcher(key: str, name: str, cat: str) -> Callable:
    async def _fetcher(client: httpx.AsyncClient, page_size: int) -> list[dict]:
        return await _fetch_cls(client, page_size, key, name, cat)
    return _fetcher


# ================================================================
# 华尔街见闻
# ================================================================
async def _fetch_wallstreetcn(client: httpx.AsyncClient, page_size: int) -> list[dict]:
    url = "https://api-one-wscn.awtmt.com/apiv1/content/lives?channel=global-channel&limit={}".format(page_size)
    resp = await client.get(url, timeout=10)
    data = resp.json().get("data", {}).get("items") or resp.json().get("data", {}).get("results", [])
    items = []
    for row in data:
        items.append(_item(
            title=row.get("title") or row.get("description", "")[:80],
            url=row.get("uri") or f"https://wallstreetcn.com/news/global/{row.get('id')}",
            source="wallstreetcn", source_name="华尔街见闻",
            summary=row.get("description"),
            content=row.get("content"),
            raw_time=row.get("display_time") and datetime.fromtimestamp(row["display_time"]).strftime("%Y-%m-%d %H:%M:%S"),
        ))
    return items


# ================================================================
# 第一财经
# ================================================================
async def _fetch_yicai(client: httpx.AsyncClient, page_size: int) -> list[dict]:
    url = "https://www.yicai.com/api/ajax/getlatest"
    params = {"page": 1, "size": page_size or 20}
    resp = await client.get(url, params=params, timeout=10)
    rows = resp.json() or []
    items = []
    for row in rows:
        items.append(_item(
            title=row.get("title"),
            url=row.get("url") or f"https://www.yicai.com/news/{row.get('newsid')}.html",
            source="yicai", source_name="第一财经",
            summary=row.get("summary") or row.get("description"),
            raw_time=row.get("ctime") or row.get("time"),
        ))
    return items


# ================================================================
# 金融界（HTTP POST）
# ================================================================
async def _fetch_jrj(client: httpx.AsyncClient, page_size: int) -> list[dict]:
    url = "https://gateway.jrj.com.cn/news/getNewsList"
    payload = {"channel": "finance", "pageNum": 1, "pageSize": page_size or 20}
    resp = await client.post(url, json=payload, timeout=10)
    data = resp.json().get("data", {}).get("list", [])
    items = []
    for row in data:
        items.append(_item(
            title=row.get("title"),
            url=row.get("url"),
            source="jrj", source_name="金融界",
            summary=row.get("summary"),
            raw_time=row.get("pubtime") or row.get("publishTime"),
        ))
    return items


# ================================================================
# 雪球（带 Session）
# ================================================================
async def _fetch_xueqiu(client: httpx.AsyncClient, page_size: int) -> list[dict]:
    url = "https://xueqiu.com/statuses/public_timeline_by_category.json"
    params = {"category": "6", "count": page_size, "source": "all"}
    # 先访问首页拿 cookie
    try:
        await client.get("https://xueqiu.com/", timeout=10)
    except Exception:  # noqa: BLE001
        pass
    resp = await client.get(url, params=params, timeout=10)
    data = resp.json().get("list", [])
    items = []
    for row in data:
        desc = row.get("description") or row.get("text", "")
        target = row.get("target")
        if isinstance(target, dict):
            title = target.get("title") or _strip_html(desc)[:80]
            link = target.get("url") or f"https://xueqiu.com{row.get('target', {}).get('url', '')}"
        else:
            title = _strip_html(desc)[:80]
            link = f"https://xueqiu.com/{row.get('user', {}).get('screen_name', '')}/{row.get('id')}"
        items.append(_item(
            title=title,
            url=link,
            source="xueqiu", source_name="雪球",
            summary=_strip_html(desc),
            author=row.get("user", {}).get("screen_name") if isinstance(row.get("user"), dict) else None,
            raw_time=row.get("created_at") and datetime.fromtimestamp(row["created_at"] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
        ))
    return items


# ================================================================
# akshare 源（同花顺 / 新浪 / 富途）
# ================================================================
def _fetch_via_akshare(func_name: str, key: str, name: str) -> Callable:
    async def _fetcher(client: httpx.AsyncClient, page_size: int) -> list[dict]:
        import akshare as ak  # 延迟导入，避免无依赖时报错

        def _call():
            return getattr(ak, func_name)()

        df = await asyncio.to_thread(_call)
        items = []
        for _, row in df.iterrows():
            title = row.get("标题") or row.get("title") or ""
            t = str(title)
            content = row.get("内容") or row.get("content") or ""
            raw_time = str(row.get("时间") or row.get("datetime") or row.get("date") or "")
            items.append(_item(
                title=t,
                url=str(row.get("链接") or row.get("url") or f"https://example.com/news/{key}/{abs(hash(t))}"),
                source=key, source_name=name,
                summary=_strip_html(str(content))[:1000] if content else None,
                content=str(content) if content else None,
                raw_time=raw_time or None,
            ))
        return items
    return _fetcher


# ================================================================
# 源注册表
# ================================================================
NEWS_SOURCES: list[dict] = [
    {"key": "eastmoney", "name": "东方财富", "page_size": 30, "fetch": _fetch_eastmoney},
    {"key": "eastmoney_global", "name": "7x24全球", "page_size": 50, "fetch": _fetch_eastmoney_global},
    {"key": "cls", "name": "财联社综合", "page_size": 20, "fetch": _make_cls_fetcher("cls", "财联社综合", "all")},
    {"key": "cls_red", "name": "财联社加红", "page_size": 20, "fetch": _make_cls_fetcher("cls_red", "财联社加红", "important")},
    {"key": "cls_announcement", "name": "财联社公告", "page_size": 20, "fetch": _make_cls_fetcher("cls_announcement", "财联社公告", "announce")},
    {"key": "cls_watch", "name": "财联社看盘", "page_size": 20, "fetch": _make_cls_fetcher("cls_watch", "财联社看盘", "watch")},
    {"key": "cls_hk_us", "name": "财联社港美股", "page_size": 20, "fetch": _make_cls_fetcher("cls_hk_us", "财联社港美股", "hk_us")},
    {"key": "cls_fund", "name": "财联社基金", "page_size": 20, "fetch": _make_cls_fetcher("cls_fund", "财联社基金", "fund")},
    {"key": "cls_remind", "name": "财联社提醒", "page_size": 20, "fetch": _make_cls_fetcher("cls_remind", "财联社提醒", "remind")},
    {"key": "tonghuashun", "name": "同花顺", "page_size": 0, "fetch": _fetch_via_akshare("stock_info_global_ths", "tonghuashun", "同花顺")},
    {"key": "sina", "name": "新浪财经", "page_size": 0, "fetch": _fetch_via_akshare("stock_info_global_sina", "sina", "新浪财经")},
    {"key": "wallstreetcn", "name": "华尔街见闻", "page_size": 50, "fetch": _fetch_wallstreetcn},
    {"key": "yicai", "name": "第一财经", "page_size": 20, "fetch": _fetch_yicai},
    {"key": "futu", "name": "富途快讯", "page_size": 0, "fetch": _fetch_via_akshare("stock_info_global_futu", "futu", "富途快讯")},
    {"key": "xueqiu", "name": "雪球", "page_size": 15, "fetch": _fetch_xueqiu},
    {"key": "jrj", "name": "金融界", "page_size": 20, "fetch": _fetch_jrj},
]
