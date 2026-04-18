"""
Local mock price catalog — no MCP subprocess needed.

get_price() is a plain sync function. It:
1. Extracts an explicit price if the user wrote "花800" or "800元"
2. Falls back to the catalog with ±20% variance for realism
3. Returns {name, price, currency} matching the old MCP schema
"""
import re
import random

CATALOG: dict[str, float] = {
    "盲盒": 599,
    "奶茶": 38,
    "耳机": 799,
    "口红": 289,
    "球鞋": 1299,
    "游戏皮肤": 128,
    "充值": 100,
    "手机壳": 59,
    "咖啡": 42,
    "键盘": 899,
    "外设": 599,
    "网红零食": 88,
    "香水": 498,
    "包包": 1599,
    "化妆品": 368,
    "手表": 2999,
    "平板": 3499,
    "相机": 4999,
    "电脑": 6999,
    "手机": 4999,
    "游戏机": 2499,
}

DEFAULT_PRICE: float = 500


def _extract_explicit_price(query: str) -> float | None:
    """Pull out a price the user wrote, e.g. '花800' '799元' '大概500块'."""
    match = re.search(
        r"(?:花|买|值|要|需要|大概|约|售价|卖|只需)?\s*(\d{1,6}(?:\.\d{1,2})?)\s*(?:元|块|rmb|￥|¥)?",
        query,
        re.IGNORECASE,
    )
    if match:
        val = float(match.group(1))
        if 1 <= val <= 100_000:
            return val
    return None


def get_price(query: str) -> dict:
    """
    Return mock price data for the queried item.

    Priority:
      1. Explicit price in query (e.g. "花800买盲盒" → 800)
      2. Catalog match with ±20% random variance
      3. Default 500 CNY
    """
    explicit = _extract_explicit_price(query)

    best_keyword: str | None = None
    best_len = 0
    for keyword in CATALOG:
        if keyword in query and len(keyword) > best_len:
            best_keyword = keyword
            best_len = len(keyword)

    if best_keyword:
        price = explicit if explicit else round(CATALOG[best_keyword] * random.uniform(0.8, 1.2), 2)
        name = best_keyword
    else:
        price = explicit if explicit else DEFAULT_PRICE
        name = query[:30].strip() or "该商品"

    return {"name": name, "price": price, "currency": "CNY"}
