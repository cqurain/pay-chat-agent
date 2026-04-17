"""
Local MCP price server for Cyber God of Wealth.

Exposes the search_products tool that returns randomized RMB prices
for common Chinese consumer goods. Unknown items fall back to a sensible
default price (500 RMB +/-30%).

Run standalone via: python price_mcp/server.py
"""
import asyncio
import json
import random

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# Catalog of common Chinese consumer goods with realistic 2025 RMB base prices
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
}

DEFAULT_PRICE: float = 500  # for unknown items

server = Server("price-mcp")


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
                        "description": "Product name or description in Chinese or English",
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

        # Find first catalog key that appears in query (substring match)
        matched_key = None
        for key in CATALOG:
            if key in query:
                matched_key = key
                break

        if matched_key is not None:
            base_price = CATALOG[matched_key]
            item_name = matched_key
        else:
            base_price = DEFAULT_PRICE
            item_name = query if query else "商品"

        # Apply +/-30% randomization
        randomized_price = base_price * random.uniform(0.7, 1.3)
        result = [
            {
                "name": item_name,
                "price": round(randomized_price, 2),
                "currency": "CNY",
            }
        ]
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    """Run the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
