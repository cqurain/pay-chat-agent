# Stack Research: AI Streaming Agent Chat

**Project:** Cyber God of Wealth (赛博财神爷)
**Researched:** 2026-04-18
**Confidence:** MEDIUM — versions verified via PyPI/npm search results; GLM-5-specific gotchas from community bug reports (cannot fetch official Zhipu docs directly due to network policy)

---

## Backend

### Core Framework

| Technology | Version (pin) | Purpose | Why |
|------------|--------------|---------|-----|
| Python | 3.12 | Runtime | 3.12 is the stable production target for 2025/2026; 3.13 adds overhead without benefit for this PoC |
| FastAPI | `>=0.115.0,<1.0` (latest: 0.135.x) | HTTP server + routing | Pydantic v2 required from 0.115+; `StreamingResponse` and native SSE support built-in; `EventSourceResponse` added in 0.135 |
| Pydantic | `>=2.7.0,<3.0` | Request/response validation | v2 required by FastAPI; 10x faster than v1; Pydantic v3 is experimental as of early 2026, do not use |
| uvicorn | `>=0.30.0` with `uvicorn[standard]` | ASGI server | `[standard]` includes uvloop and httptools for high throughput; needed for streaming without buffering |
| openai | `>=1.50.0,<2.0` (recommended: pin to `~=1.102`) | GLM-5 API client | **Use 1.x, NOT 2.x** (see "What NOT to use"); `AsyncOpenAI` in 1.x accepts `base_url` to point at Zhipu endpoint; `stream=True` returns async iterator of chunks |
| python-dotenv | `>=1.0.0` | Env var loading | Standard for loading ZHIPU_API_KEY from .env in local dev |

### Install command

```bash
pip install "fastapi[standard]" "openai~=1.102" "pydantic>=2.7,<3" python-dotenv
# fastapi[standard] pulls in uvicorn[standard], httpx, email-validator, pydantic
```

### Python-level streaming pattern

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
import json

app = FastAPI()

# REQUIRED: CORS for Next.js dev server (localhost:3000) and Vercel domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-project.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GLM-5 client — identical to openai.AsyncOpenAI, just different base_url + api_key
client = AsyncOpenAI(
    api_key="YOUR_ZHIPU_API_KEY",          # from env: os.environ["ZHIPU_API_KEY"]
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

async def stream_agent(messages, tools):
    async def generator():
        # --- Phase 1: stream text tokens ---
        stream = await client.chat.completions.create(
            model="glm-4-5",               # see GLM-5 Specifics below
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=True,
        )
        tool_calls_buffer = []             # accumulate delta.tool_calls across chunks
        async for chunk in stream:
            delta = chunk.choices[0].delta
            # Text token
            if delta.content:
                yield f"data: {json.dumps({'type': 'text', 'content': delta.content})}\n\n"
            # Tool call delta — must accumulate; GLM-4.x delivers arguments piecemeal
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    while len(tool_calls_buffer) <= idx:
                        tool_calls_buffer.append({"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        tool_calls_buffer[idx]["id"] = tc.id
                    if tc.function.name:
                        tool_calls_buffer[idx]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls_buffer[idx]["arguments"] += tc.function.arguments
            if chunk.choices[0].finish_reason == "tool_calls":
                # Execute tools, then yield structured result chunk
                results = execute_tools(tool_calls_buffer)
                yield f"data: {json.dumps({'type': 'tool_result', 'data': results})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",     # prevents nginx buffering — critical for Railway/Render
            "Connection": "keep-alive",
        },
    )
```

---

## Frontend

### Core Framework

| Technology | Version (pin) | Purpose | Why |
|------------|--------------|---------|-----|
| Next.js | `16.x` (latest: 16.2.x as of Apr 2026) | React framework | App Router stable; Turbopack default (faster HMR); React Compiler stable in v16 — eliminates manual memo |
| React | `19.x` (pulled by Next 16) | UI library | Required by Next.js 16 |
| `ai` (Vercel AI SDK) | `^4.3` — **do NOT use v5 or v6** (see "What NOT to use") | useChat hook | v4 useChat works with custom FastAPI SSE backends directly; v5+ broke the custom-backend SSE contract |
| `@ai-sdk/openai` | `^1.x` (matches AI SDK 4.x) | Provider (unused for routing but needed) | If using Vercel's streamText in an API route; skip if routing all traffic to FastAPI |
| Tailwind CSS | `^4.2` (released Feb 2026) | Styling | v4 is CSS-first with zero config; `@import "tailwindcss"` replaces tailwind.config.js; webpack plugin added in 4.2 |
| TypeScript | `^5.x` | Type safety | Standard with Next.js 16 |

### Install command

```bash
npx create-next-app@16 frontend --typescript --tailwind --app
cd frontend
npm install ai@^4
```

### useChat wiring to FastAPI backend

The key insight: `useChat` accepts an `api` prop pointing at any URL that returns `text/event-stream`. You do NOT need Vercel's streamText format — you can use raw SSE with the `streamMode: "text"` option in AI SDK 4.x.

```tsx
// app/page.tsx
"use client";
import { useChat } from "ai/react";

export default function Chat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading, data } =
    useChat({
      api: process.env.NEXT_PUBLIC_BACKEND_URL + "/api/chat",
      // streamMode: "text" tells useChat to treat the stream as raw SSE text,
      // not Vercel's data-stream protocol. This is the bridge to FastAPI.
      streamMode: "text",
    });

  return (
    <div>
      {messages.map((m) => (
        <div key={m.id}>{m.content}</div>
      ))}
      <form onSubmit={handleSubmit}>
        <input value={input} onChange={handleInputChange} />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}
```

### Progress bar (Tailwind v4, no extra library)

```tsx
// components/SavingsProgress.tsx
interface Props {
  current: number;
  target: number;
}
export function SavingsProgress({ current, target }: Props) {
  const pct = Math.min(100, Math.round((current / target) * 100));
  return (
    <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
      <div
        className="h-4 rounded-full bg-gradient-to-r from-yellow-400 to-amber-500 transition-all duration-700"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
```

No external progress-bar library needed. Tailwind v4 `transition-all duration-700` gives the live animation.

---

## GLM-5 Specifics

### Model name and endpoint

The project's `PROJECT.md` uses `glm-4-5`. Zhipu AI's current production model names as of April 2026:

| Model string | Notes |
|---|---|
| `glm-4-5` | Stated in PROJECT.md — verify with Zhipu console that this is the exact string |
| `glm-4-flash` | Free-tier fast model; supports function calling |
| `glm-4` | Full capability model |
| `glm-4-plus` | Most capable in GLM-4 line |
| `glm-5` | 744B MoE flagship, released Feb 2026 |

**Recommendation:** use `GLM_MODEL=glm-4-flash` for local dev (free, fast) and `glm-4-5` or `glm-4-plus` for production. Store in `.env` as `GLM_MODEL`, never hard-code.

### OpenAI client configuration

```python
from openai import AsyncOpenAI
import os

client = AsyncOpenAI(
    api_key=os.environ["ZHIPU_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    # Do NOT set organization or project — Zhipu ignores them but they can
    # cause 400 errors on some SDK versions if the header is forwarded unexpectedly
)
```

The Zhipu endpoint is fully OpenAI chat completions compatible: same request body shape, same response delta shape, same `finish_reason` values (`"stop"`, `"tool_calls"`, `"length"`).

### Tool call format (identical to OpenAI)

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_mock_price",
            "description": "Returns a mocked price for any item name with ±30% randomization",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Item name in Chinese or English"}
                },
                "required": ["item_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_savings_impact",
            "description": "Calculates the impact of a purchase on savings goal",
            "parameters": {
                "type": "object",
                "properties": {
                    "price": {"type": "number"},
                    "current_savings": {"type": "number"},
                    "savings_target": {"type": "number"},
                },
                "required": ["price", "current_savings", "savings_target"],
            },
        },
    },
]
```

### Known GLM-4.x streaming tool_calls gotchas (MEDIUM confidence — from community bug reports)

**Gotcha 1: Arguments arrive in fragments across multiple chunks.**
This is standard OpenAI streaming behavior, but GLM models are observed to sometimes deliver tool call arguments as a single chunk at the end rather than incrementally. Your aggregation buffer (accumulate `delta.function.arguments` until `finish_reason == "tool_calls"`) handles both cases correctly.

**Gotcha 2: `delta.tool_calls` may be `None` for most chunks, then populated in 1-2 chunks at the end.**
Do not assume tool call content is spread across many chunks. Check `if delta.tool_calls` before accessing fields.

**Gotcha 3: `finish_reason: "tool_calls"` signals tool execution needed.**
GLM-4.x correctly sets `finish_reason` to `"tool_calls"` when a function call is invoked. Do not look for a `stop` reason to decide whether to call tools.

**Gotcha 4: Streaming + tool_calls in the same request.**
GLM-4.6/4.7 and vLLM-hosted versions have a documented bug where streaming mode returns `tool_calls` in the delta but doesn't stream argument tokens — the full JSON arrives in one chunk. For the Zhipu-hosted API (`open.bigmodel.cn`), this is less likely but **do not build UX that depends on character-by-character argument streaming**. Always buffer the full arguments string before calling the function.

**Gotcha 5: `<tool_call>` tags in raw output.**
Older GLM-4.x self-hosted versions (not Zhipu API) wrap tool calls in `<tool_call>...</tool_call>` XML tags instead of the OpenAI `tool_calls` JSON field. The Zhipu-hosted API (`open.bigmodel.cn`) uses standard OpenAI JSON format. This only matters if you later switch to self-hosting.

**Gotcha 6: nginx/proxy buffering eats SSE.**
When deployed to Railway or Render, ensure your FastAPI response sets `X-Accel-Buffering: no`. Without this, nginx will buffer the entire response before forwarding, completely breaking streaming. The header is included in the streaming pattern above.

### Two-phase streaming strategy for this project

Because the progress bar update requires final computed values (new_savings, progress%), but the character verdict streams token-by-token, use this two-phase pattern:

1. **Phase 1 (stream):** Text tokens stream to frontend via SSE — frontend renders typewriter effect.
2. **Phase 2 (end-of-stream structured chunk):** After all tool calls are resolved and the final assistant message is complete, append one final SSE chunk with the structured data payload:

```python
final_payload = {
    "type": "savings_update",
    "data": {
        "new_savings": 3200,
        "progress_pct": 64,
        "delta": -800,
        "verdict": "reject"
    }
}
yield f"data: {json.dumps(final_payload)}\n\n"
yield "data: [DONE]\n\n"
```

The frontend checks `message.type === "savings_update"` in the SSE stream and updates the progress bar React state. The `useChat` `onFinish` callback or custom `onData` handler intercepts this.

---

## What NOT to use

### Do NOT use: openai Python SDK 2.x

**Reason:** openai 2.x (released late 2025) is a breaking rewrite. It changes the async API surface, removes several 1.x compatibility shims, and introduces a new `Responses` API that does not map cleanly to GLM-5's chat completions interface. The 1.x `AsyncOpenAI(base_url=..., api_key=...)` pattern for custom endpoints is battle-tested and well-documented. The 2.x `base_url` behavior for custom endpoints has not yet been confirmed compatible with Zhipu's endpoint. Stay on `~=1.102` until Zhipu explicitly confirms 2.x compatibility.

### Do NOT use: Vercel AI SDK v5 or v6 (`ai@^5` or `ai@^6`)

**Reason:** AI SDK 5 (released late 2025) redesigned `useChat` around a "transport-based architecture" that removed direct `streamMode: "text"` support. The new transport system requires backend responses to follow Vercel's data stream protocol format (`0:`, `f:`, `e:` prefixed SSE lines), not plain `data: {...}` SSE. Implementing the Vercel data-stream protocol in FastAPI adds significant complexity and fragility. AI SDK 4.x `useChat` with `streamMode: "text"` connects directly to any SSE endpoint emitting `data: {...}` lines — which is exactly what FastAPI StreamingResponse produces. Stay on `ai@^4`.

### Do NOT use: LangChain or LangGraph

**Reason:** PROJECT.md explicitly excludes these. They add latency, abstraction overhead, and debugging complexity. For a 2-tool single-LLM-loop PoC, raw OpenAI SDK is faster to write, easier to debug, and has zero additional dependency surface.

### Do NOT use: WebSockets

**Reason:** SSE (Server-Sent Events) is simpler, HTTP-native, and sufficient for one-directional streaming (server → client). WebSockets require a stateful connection, don't work through standard CDN/proxy setups (Railway, Render default tiers), and add reconnect logic complexity.

### Do NOT use: Pydantic v3

**Reason:** As of April 2026, Pydantic v3 is not stable. FastAPI has not declared support. Stay on Pydantic `>=2.7,<3`.

### Do NOT use: Redis or any database

**Reason:** PROJECT.md explicitly scopes this as localStorage + in-memory only. A database would be over-engineering a PoC and is out of scope.

### Do NOT use: sse-starlette (the third-party library)

**Reason:** FastAPI 0.115+ has a native `EventSourceResponse` that handles `X-Accel-Buffering: no`, `Cache-Control: no-cache`, and W3C SSE compliance. Using the external `sse-starlette` package adds a dependency that is now redundant. Use FastAPI's native `StreamingResponse` with manual headers, or its built-in `EventSourceResponse` — no third-party SSE library needed.

---

## Environment Variables

```bash
# backend/.env
ZHIPU_API_KEY=your_key_here
GLM_MODEL=glm-4-flash          # change to glm-4-5 or glm-4-plus for production
```

```bash
# frontend/.env.local
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000   # prod: https://your-backend.railway.app
```

---

## Sources

- FastAPI PyPI / release notes: https://pypi.org/project/fastapi/ — MEDIUM confidence
- OpenAI Python 1.x branch final version (1.102.0): https://medium.com/h7w/openai-python-library-version-1-102-0-released-on-pypi-6e88ba6ba47c — MEDIUM confidence
- OpenAI Python 2.x breaking changes: https://github.com/openai/openai-python/discussions/742 — MEDIUM confidence
- Zhipu AI OpenAI-compatible base URL: https://open.bigmodel.cn/dev/api (official Zhipu platform, unreachable for direct fetch) — HIGH confidence via multiple corroborating sources
- GLM-5 release and capabilities: https://glm-5.org/ and https://lushbinary.com/blog/glm-5-developer-guide-zhipu-ai-huawei-ascend-open-weight/ — MEDIUM confidence
- GLM-4.6 streaming tool_calls bug: https://github.com/sgl-project/sglang/issues/11888 — HIGH confidence (official bug report)
- GLM-4.7 streaming tool_calls parsing bug: https://github.com/vllm-project/vllm/issues/32829 — HIGH confidence (official bug report)
- Vercel AI SDK 4.2: https://vercel.com/blog/ai-sdk-4-2 — HIGH confidence
- Vercel AI SDK 5 transport redesign: https://vercel.com/blog/ai-sdk-5 — HIGH confidence
- ai npm package latest (6.0.162): https://www.npmjs.com/package/ai — HIGH confidence
- Next.js 16.2.3 LTS (Apr 2026): https://nextjs.org/blog/next-16 and https://eosl.date/eol/product/nextjs/ — HIGH confidence
- Tailwind CSS v4.2 (Feb 2026): https://www.infoq.com/news/2026/04/tailwind-css-4-2-webpack/ — HIGH confidence
- FastAPI SSE CORS and X-Accel-Buffering: https://fastapi.tiangolo.com/tutorial/server-sent-events/ — HIGH confidence
- FastAPI + Next.js streaming guide: https://sahansera.dev/streaming-apis-python-nextjs-part1/ — MEDIUM confidence
