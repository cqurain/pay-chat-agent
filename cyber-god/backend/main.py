import os
from contextlib import asynccontextmanager, AsyncExitStack

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config import ALLOWED_ORIGINS

# Absolute path to the MCP price server script (relative to this file)
MCP_SERVER_PATH = os.path.join(os.path.dirname(__file__), "price_mcp", "server.py")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the MCP subprocess lifecycle for the entire FastAPI app.

    Spawns price_mcp/server.py once at startup and keeps a single ClientSession
    shared across all requests (stored in app.state.mcp_session). Cleans up
    the subprocess on shutdown via AsyncExitStack.aclose().

    See RESEARCH.md Pattern 1 / Pitfall 3: single subprocess per app, NOT per request.
    """
    exit_stack = AsyncExitStack()
    await exit_stack.__aenter__()

    server_params = StdioServerParameters(
        command="python",
        args=[MCP_SERVER_PATH],
        env=None,
    )
    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
    stdio, write = stdio_transport
    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
    await session.initialize()

    app.state.mcp_session = session

    yield

    await exit_stack.aclose()


app = FastAPI(title="Cyber God of Wealth API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
