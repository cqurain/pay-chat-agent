"""
Local MCP price server for Cyber God of Wealth.

Mock data lives here — to plug in real data, replace the call_tool handler
with an actual API call. The MCP interface stays the same.

Exposes: search_products(query) → [{name, price, currency}]

Run standalone: python price_mcp/server.py
"""
import asyncio
import json
import random
import re

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# Mock catalog — swap this dict or the lookup logic for real data
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

server = Server("price-mcp")


def _extract_explicit_price(query: str) -> float | None:
    """Pull a price the user wrote, e.g. '花800' '799元' '大概500块'."""
    m = re.search(
        r"(?:花|买|值|要|需要|大概|约|售价|只需)?\s*(\d{1,6}(?:\.\d{1,2})?)\s*(?:元|块|rmb|￥|¥)?",
        query,
        re.IGNORECASE,
    )
    if m:
        val = float(m.group(1))
        if 1 <= val <= 100_000:
            return val
    return None


def _lookup(query: str) -> dict:
    """Match query against catalog using longest-keyword wins."""
    explicit = _extract_explicit_price(query)

    best_key: str | None = None
    best_len = 0
    for key in CATALOG:
        if key in query and len(key) > best_len:
            best_key = key
            best_len = len(key)

    if best_key:
        price = explicit if explicit else round(CATALOG[best_key] * random.uniform(0.8, 1.2), 2)
        name = best_key
    else:
        price = explicit if explicit else round(DEFAULT_PRICE * random.uniform(0.7, 1.3), 2)
        name = query[:30].strip() or "该商品"

    return {"name": name, "price": price, "currency": "CNY"}


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_products",
            description=(
                "Search for product prices in RMB. "
                "Returns a list with price data for the queried item."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Product name or description (Chinese or English)",
                    }
                },
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "search_products":
        query = arguments.get("query", "")
        result = [_lookup(query)]
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
    raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
