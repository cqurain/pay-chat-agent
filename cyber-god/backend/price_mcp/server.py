"""
Local MCP price server for Cyber God of Wealth.

Price resolution strategy:
  1. Tavily search "{keyword} 价格"                → confidence: scraped
  2. DDGS search "{keyword} 价格" (Tavily fallback) → confidence: scraped
  3. Catalog fallback (60+ categories)             → confidence: reference
  4. No match                                      → confidence: unknown

Exposes: search_products(query) → [{name, price, price_min, price_max, source, confidence, currency, sources}]
"""
import asyncio
import json
import os
import random
import re
import statistics
from concurrent.futures import ThreadPoolExecutor

from ddgs import DDGS
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

_TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")

server = Server("price-mcp")

_PRICE_RE = re.compile(
    r"[¥￥]\s*(\d{1,6}(?:[.,]\d{1,2})?)"
    r"|(\d{1,6}(?:\.\d{1,2})?)\s*元"
)

# Market reference prices (CNY): (min, typical, max)
CATALOG: dict[str, tuple[float, float, float]] = {
    "手机": (999, 3499, 9999), "iPhone": (5999, 7999, 14999),
    "苹果": (999, 6999, 14999), "华为": (1999, 4999, 9999),
    "小米": (999, 2499, 5999), "平板": (1299, 2999, 7999),
    "iPad": (2499, 4999, 9999), "笔记本": (3499, 5999, 14999),
    "电脑": (2999, 5999, 14999), "显示器": (699, 1499, 4999),
    "耳机": (99, 599, 2999), "AirPods": (999, 1299, 1999),
    "键盘": (199, 499, 1999), "鼠标": (99, 299, 999),
    "外设": (199, 599, 1999), "相机": (2499, 4999, 14999),
    "游戏机": (1999, 2499, 3999), "Switch": (1999, 2099, 2399),
    "PS5": (3499, 3799, 4299), "手表": (299, 1999, 9999),
    "智能手表": (299, 999, 3999), "路由器": (99, 299, 999),
    "充电器": (39, 89, 299), "数据线": (19, 39, 99),
    "手机壳": (19, 49, 199), "钢化膜": (9, 19, 59),
    "球鞋": (299, 699, 3999), "运动鞋": (199, 499, 1999),
    "Nike": (499, 899, 2499), "Jordan": (899, 1599, 4999),
    "Adidas": (399, 799, 1999), "外套": (199, 499, 1999),
    "羽绒服": (499, 999, 3999), "卫衣": (99, 299, 999),
    "T恤": (49, 99, 499), "裙子": (99, 299, 999),
    "包包": (299, 999, 9999), "LV": (6999, 9999, 29999),
    "帽子": (49, 99, 399), "口红": (49, 199, 599),
    "粉底": (99, 299, 699), "香水": (199, 499, 1999),
    "护肤品": (99, 299, 999), "化妆品": (99, 399, 1999),
    "眼影": (99, 199, 599), "面膜": (49, 99, 299),
    "奶茶": (15, 28, 45), "星巴克": (28, 42, 68),
    "咖啡": (12, 28, 58), "瑞幸": (9, 15, 28),
    "网红零食": (29, 59, 129), "零食": (19, 39, 99),
    "外卖": (15, 35, 80), "盲盒": (59, 99, 299),
    "泡泡玛特": (59, 99, 299), "手办": (99, 299, 999),
    "玩具": (49, 199, 699), "游戏皮肤": (6, 68, 328),
    "充值": (30, 100, 648), "会员": (15, 30, 198),
    "演唱会": (380, 680, 1980), "电影票": (29, 49, 99),
    "空调": (1499, 2499, 5999), "冰箱": (1299, 2499, 6999),
    "洗衣机": (999, 1999, 4999), "电视": (1299, 2499, 7999),
    "沙发": (999, 2999, 9999), "床垫": (699, 1999, 6999),
    "跑步机": (999, 2499, 7999), "瑜伽垫": (39, 79, 199),
}

_PLATFORM_MAP = {
    "jd.com": "京东", "taobao.com": "淘宝", "tmall.com": "天猫",
    "pinduoduo.com": "拼多多", "xianyu": "闲鱼", "suning.com": "苏宁",
    "smzdm.com": "什么值得买", "amazon.cn": "亚马逊",
}


def _infer_platform(url: str) -> str:
    for domain, name in _PLATFORM_MAP.items():
        if domain in url:
            return name
    return "网络"


def _catalog_lookup(query: str) -> tuple[str, tuple[float, float, float]] | None:
    best_key, best_len = None, 0
    for key in CATALOG:
        if key in query and len(key) > best_len:
            best_key, best_len = key, len(key)
    return (best_key, CATALOG[best_key]) if best_key else None



def _ddgs_search_sync(keyword: str) -> list[dict]:
    try:
        with DDGS() as d:
            results = list(d.text(f"{keyword} 价格", region="cn-zh", max_results=6))
        out: list[dict] = []
        for r in results:
            text = r.get("body", "") + " " + r.get("title", "")
            url = r.get("href", "")
            platform = _infer_platform(url)
            for m in _PRICE_RE.finditer(text):
                raw = (m.group(1) or m.group(2) or "").replace(",", "")
                try:
                    price = float(raw)
                    if 10 <= price <= 100_000:
                        out.append({"price": price, "platform": platform, "url": url})
                        break  # one price per result
                except ValueError:
                    pass
        return out
    except Exception:
        return []


def _tavily_search_sync(keyword: str) -> list[dict]:
    if not _TAVILY_API_KEY:
        return []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=_TAVILY_API_KEY)
        resp = client.search(f"{keyword} 价格", max_results=5)
        out: list[dict] = []
        for r in resp.get("results", []):
            text = r.get("content", "") + " " + r.get("title", "")
            url = r.get("url", "")
            platform = _infer_platform(url)
            for m in _PRICE_RE.finditer(text):
                raw = (m.group(1) or m.group(2) or "").replace(",", "")
                try:
                    price = float(raw)
                    if 10 <= price <= 100_000:
                        out.append({"price": price, "platform": platform, "url": url})
                        break
                except ValueError:
                    pass
        return out
    except Exception:
        return []


async def _ddgs_search(keyword: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, _ddgs_search_sync, keyword)


async def _tavily_search(keyword: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, _tavily_search_sync, keyword)


async def _resolve_price(keyword: str) -> dict:
    # 1. Tavily first, DDGS second
    sources: list[dict] = await _tavily_search(keyword)
    if not sources:
        sources = await _ddgs_search(keyword)

    if sources:
        # Dedup: per platform keep lowest price
        best: dict[str, dict] = {}
        for s in sources:
            p = s["platform"]
            if p not in best or s["price"] < best[p]["price"]:
                best[p] = s
        deduped = sorted(best.values(), key=lambda x: x["price"])[:3]
        prices = [s["price"] for s in deduped]

        # Guard with catalog if available
        cat = _catalog_lookup(keyword)
        if cat:
            _, (lo, _, hi) = cat
            filtered = [p for p in prices if lo * 0.3 <= p <= hi * 3]
            if filtered:
                prices = filtered
                deduped = [s for s in deduped if lo * 0.3 <= s["price"] <= hi * 3]

        if prices:
            return {
                "name": keyword,
                "price": round(statistics.median(prices), 2),
                "price_min": round(min(prices), 2),
                "price_max": round(max(prices), 2),
                "source": "网络搜索",
                "confidence": "scraped",
                "currency": "CNY",
                "sources": deduped,
            }

    # Catalog fallback
    cat = _catalog_lookup(keyword)
    if cat:
        key, (low, mid, high) = cat
        price = round(mid * random.uniform(0.92, 1.08), 0)
        return {
            "name": key, "price": price,
            "price_min": low, "price_max": high,
            "source": "市场参考价", "confidence": "reference", "currency": "CNY",
            "sources": [],
        }

    # Unknown
    return {
        "name": keyword,
        "price": 0.0, "price_min": 0.0, "price_max": 0.0,
        "source": "", "confidence": "unknown", "currency": "CNY",
        "sources": [],
    }


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_products",
            description=(
                "Resolve product price via Tavily/DDGS search then catalog fallback. "
                "Returns confidence: scraped | reference | unknown, plus sources list."
            ),
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "search_products":
        result = await _resolve_price(arguments.get("query", ""))
        return [types.TextContent(type="text", text=json.dumps([result], ensure_ascii=False))]
    raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
