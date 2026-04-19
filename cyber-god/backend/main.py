import os
import sys
from contextlib import asynccontextmanager, AsyncExitStack

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config import ALLOWED_ORIGINS

MCP_SERVER_PATH = os.path.join(os.path.dirname(__file__), "price_mcp", "server.py")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Spawn the price MCP server once at startup and share the session across
    all requests. To swap mock data for real data: update price_mcp/server.py.
    """
    exit_stack = AsyncExitStack()
    await exit_stack.__aenter__()

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[MCP_SERVER_PATH],
        env=dict(os.environ),  # stdio_client does not inherit os.environ when env=None
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

from api.routes import router  # noqa: E402
app.include_router(router, prefix="/api")
