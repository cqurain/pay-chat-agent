"""
FastAPI router — POST /api/chat endpoint.

Validates the request body with Pydantic, creates an AsyncOpenAI client,
and returns a StreamingResponse with Vercel Data Stream Protocol headers.

D-07 note: run_agent_loop is an async generator; Python generators do not execute
until iterated, so the try/except around `gen = run_agent_loop(...)` does NOT catch
GLM network/auth errors (they happen during iteration). Errors are instead caught in
safe_stream() and emitted as in-character SSE — response code is 200 with error text.
This is a documented deviation from the strict D-07 spec (HTTP 500 before stream opens).
See SUMMARY.md for rationale.
"""
import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

from agent.loop import run_agent_loop
from config import GLM_MODEL, ZHIPU_API_KEY

router = APIRouter()


@router.get("/test-stream")
async def test_stream():
    """Quick diagnostic: verifies FastAPI SSE streaming works at all."""
    async def gen():
        for i in range(5):
            yield f'0:{json.dumps(f"chunk {i}")}\n'
            await asyncio.sleep(0.3)
        yield 'e:{"finishReason":"stop"}\n'
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    savings: float = 0.0
    target: float = 10000.0


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    """
    POST /api/chat

    Request body: {messages: [{role, content}], savings: float, target: float}
    Response: text/event-stream with Vercel Data Stream Protocol
    Headers: x-vercel-ai-data-stream: v1, X-Accel-Buffering: no
    """
    mcp_session = request.app.state.mcp_session

    glm_client = AsyncOpenAI(
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key=ZHIPU_API_KEY,
    )

    messages = [m.model_dump() for m in body.messages]

    gen = run_agent_loop(
        messages=messages,
        savings=body.savings,
        target=body.target,
        mcp_session=mcp_session,
        glm_client=glm_client,
        model=GLM_MODEL,
    )

    async def safe_stream():
        """
        Wrap the agent generator to catch mid-stream exceptions.

        If an exception occurs after streaming has started, emit an in-character
        error message then close the stream cleanly (avoids broken SSE to the client).
        """
        try:
            async for line in gen:
                yield line
        except Exception:
            err_text = "财神系统故障，请稍后再试。"
            yield f'0:{json.dumps(err_text)}\n'
            finish_meta = json.dumps(
                {"finishReason": "error", "usage": {"promptTokens": 0, "completionTokens": 0}}
            )
            yield f'e:{finish_meta}\n'
            yield f'd:{finish_meta}\n'

    return StreamingResponse(
        safe_stream(),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-data-stream": "v1",  # Required for useChat hook to parse 2: channel
            "X-Accel-Buffering": "no",          # Prevents nginx from buffering SSE chunks
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
