"""
MCP client wrapper for the price server.

Calls search_products on the MCP server (price_mcp/server.py) and returns
the first result. To swap mock data for real data: update price_mcp/server.py
only — this file and everything above it stays the same.
"""
import json

from mcp import ClientSession


async def get_price(query: str, mcp_session: ClientSession) -> dict:
    """
    Query the price MCP server and return the first result.

    Returns:
        dict with keys: name (str), price (float), currency (str, always "CNY")
    """
    tool_result = await mcp_session.call_tool("search_products", {"query": query})
    raw = tool_result.content[0].text
    items = json.loads(raw)
    return items[0]
