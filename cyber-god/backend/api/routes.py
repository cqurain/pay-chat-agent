"""
FastAPI router — POST /api/chat endpoint.

Validates the request body, creates an AsyncOpenAI client, and returns a
StreamingResponse with Vercel Data Stream Protocol headers.

Error handling: exceptions inside run_agent_loop are caught by safe_stream()
and emitted as in-character SSE text so the client always receives a 200.
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


class TransactionRecord(BaseModel):
    type: str        # "deposit" | "withdraw"
    amount: float
    timestamp: str   # ISO 8601


class ChatRequest(BaseModel):
    messages: list[Message]
    savings: float = 0.0
    target: float = 10000.0
    transactions: list[TransactionRecord] = []
    persona: str = "snarky"


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    mcp_session = request.app.state.mcp_session

    glm_client = AsyncOpenAI(
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key=ZHIPU_API_KEY,
    )

    messages = [m.model_dump() for m in body.messages]
    transactions = [t.model_dump() for t in body.transactions]

    gen = run_agent_loop(
        messages=messages,
        savings=body.savings,
        target=body.target,
        mcp_session=mcp_session,
        glm_client=glm_client,
        model=GLM_MODEL,
        transactions=transactions,
        persona=body.persona,
    )

    async def safe_stream():
        try:
            async for line in gen:
                if await request.is_disconnected():
                    break
                yield line
        except Exception:
            err_text = "财神系统故障，请稍后再试。"
            yield f'0:{json.dumps(err_text)}\n'
            finish_meta = json.dumps(
                {"finishReason": "stop", "usage": {"promptTokens": 0, "completionTokens": 0}}
            )
            yield f'e:{finish_meta}\n'
            yield f'd:{finish_meta}\n'

    return StreamingResponse(
        safe_stream(),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-data-stream": "v1",
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
