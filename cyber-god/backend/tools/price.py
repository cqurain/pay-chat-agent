"""
MCP client wrapper for the local price server.

Provides get_price() — an async function that calls search_products on the
price MCP server (spawned as a subprocess managed by FastAPI lifespan) and
returns the first result as a structured dict.
"""
import json

from mcp import ClientSession


async def get_price(query: str, mcp_session: ClientSession) -> dict:
    """
    Call search_products on the MCP server and return the first result.

    Args:
        query: Product name or description (Chinese or English).
        mcp_session: Active MCP ClientSession from app.state.mcp_session.

    Returns:
        dict with keys: name (str), price (float), currency (str, always "CNY")
    """
    tool_result = await mcp_session.call_tool("search_products", {"query": query})
    # tool_result.content is a list of TextContent objects
    raw = tool_result.content[0].text
    items = json.loads(raw)
    return items[0]  # always returns a list with one item
