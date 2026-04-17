# Phase 1: Backend Core - Research

**Researched:** 2026-04-18
**Domain:** FastAPI + OpenAI-compatible GLM-5 streaming + MCP subprocess for local tool calls + Vercel Data Stream Protocol wire format
**Confidence:** HIGH (core patterns verified; MCP subprocess lifecycle MEDIUM confidence)

## Summary

Phase 1 backend must implement a streaming chat endpoint that:
1. Accepts a purchase impulse JSON, retrieves current savings from user
2. Makes a two-phase GLM call: first with `stream=False` to resolve tool calls (avoid streaming bug), then with `stream=True` for verdict text generation
3. Spawns a local MCP server subprocess for price lookups (no API keys, pure MCP protocol)
4. Executes tool calls and appends results to message history
5. Streams response back as Vercel Data Stream Protocol format (`f:`, `0:`, `2:`, `e:`, `d:` lines)
6. Includes x-vercel-ai-data-stream header and X-Accel-Buffering header for proper SSE delivery

**Primary recommendation:** Use `mcp>=1.0` Python SDK with `StdioServerParameters` + `ClientSession` for subprocess MCP communication. For streaming response, emit raw Vercel protocol lines (not JSON-RPC) with `StreamingResponse` + async generator. Use OpenAI SDK 1.102 with `AsyncOpenAI` for GLM calls, pinned exactly to avoid 2.x breakage.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Product price lookup served by local MCP server (`price_mcp/`) — no external APIs
- **D-02:** MCP server exposes `search_products(query: str) -> list[{name, price, currency}]` tool
- **D-03:** Unknown items return sensible default price (~500 RMB ± 30%)
- **D-16:** FastAPI backend is MCP client: spawns `price_mcp/server.py` subprocess using mcp SDK stdio transport; calls `search_products`
- **D-04:** Backend module structure:
  - `cyber-god/backend/config.py` — env var loading
  - `cyber-god/backend/price_mcp/server.py` — MCP server (search_products tool + catalog)
  - `cyber-god/backend/tools/price.py` — MCP client wrapper
  - `cyber-god/backend/tools/savings.py` — savings impact calculation
  - `cyber-god/backend/agent/loop.py` — two-phase GLM call + SSE formatting
  - `cyber-god/backend/agent/prompt.py` — system prompt (毒舌财神 persona)
  - `cyber-god/backend/api/routes.py` — POST /api/chat endpoint
  - `cyber-god/backend/main.py` — FastAPI app setup + CORS
- **D-05, D-06:** Stream error handling: retry once if no tool calls; emit in-character error then close normally (not 500)
- **D-07:** Network errors return HTTP 500 before stream opens
- **D-08, D-09, D-10:** 毒舌财神 persona — internet-roast style, leads with approve/reject, always calls both tools first, system prompt in `agent/prompt.py`
- **D-11:** SSE format: Vercel Data Stream Protocol — `f:`, `0:`, `2:`, `e:`, `d:` lines + headers
- **D-12:** Two-phase GLM: `stream=False` for tool resolution (`tool_choice="auto"`), `stream=True` for verdict
- **D-13:** Savings payload `{new_savings, progress_pct, delta}` in `2:` channel (array-wrapped JSON)
- **D-14, D-15:** CORS via `CORSMiddleware` + `ALLOWED_ORIGINS` env var; `GLM_MODEL` env var (glm-4-flash dev / glm-4-5 prod)

### Claude's Discretion (Research Findings)
- Exact RMB catalog prices and randomization strategy
- MCP server subprocess lifecycle and event loop integration
- uvicorn startup and dev script specifics
- Exact Vercel protocol line encoding
- Requirements.txt pinning strategy

### Deferred Ideas
- Persona selector (noted for v2 backlog)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TOOL-01 | `get_mock_price(item_name: str)` returns ±30% randomized price | MCP search_products tool in price_mcp/server.py; mcp SDK callable from FastAPI async code via ClientSession |
| TOOL-02 | `calculate_savings_impact(price, savings, target)` returns dict | Pure Python sync function; mcp SDK does NOT require async iteration for non-streaming tools |
| AGENT-01 | POST /api/chat accepts `{messages, savings, target}` JSON | FastAPI routing + Pydantic validation |
| AGENT-02 | Backend calls GLM with stream=False on first call | AsyncOpenAI 1.102 with stream=False + tool_choice="auto" |
| AGENT-03 | Execute tool calls, append role="tool" results | OpenAI SDK 1.x handles tool_calls list unpacking; mcp ClientSession.call_tool() returns tool result |
| AGENT-04 | Call GLM with stream=True on second call | AsyncOpenAI 1.102 with stream=True |
| AGENT-05 | Return FastAPI StreamingResponse in Vercel Data Stream Protocol format | Async generator yielding line-by-line SSE format + headers |
| AGENT-06 | Structured payload in `2:` data chunk | Vercel protocol encodes `2:[{json}]` format |
| AGENT-07 | CORS configured via CORSMiddleware | FastAPI stdlib middleware |
| PERSONA-01 | 毒舌财神 system prompt hardcoded | Prompt engineering (no external library required) |
| PERSONA-02 | LLM instructed to call both tools before replying | System prompt instruction + retry fallback |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 (PoC) / 3.11 (local) | Runtime | Stable production target 2025/2026; 3.13 adds overhead; CLAUDE.md specifies 3.12 for prod |
| FastAPI | >=0.115.0,<1.0 | HTTP server + routing + SSE | Pydantic v2 required from 0.115+; native StreamingResponse + SSE support |
| Pydantic | >=2.7.0,<3.0 | Request/response validation | v2 required by FastAPI 0.115+; 10x faster than v1; v3 experimental in early 2026 |
| uvicorn | >=0.30.0 with [standard] | ASGI server | [standard] includes uvloop + httptools for streaming without buffering |
| openai | ~=1.102 (NOT 2.x) | GLM-5 API client + streaming | 1.x AsyncOpenAI accepts base_url for Zhipu endpoint; 2.x breaks custom base_url |
| mcp | >=1.0 | Model Context Protocol SDK | stdio transport for subprocess; ClientSession for calling tools; official SDK |
| python-dotenv | >=1.0.0 | Env var loading (.env in dev) | Standard for ZHIPU_API_KEY + GLM_MODEL loading |

[VERIFIED: pip index versions openai, mcp >= 1.0 available on PyPI]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | (via openai) | Async HTTP client | Pulled in by openai 1.x for custom base_url requests |
| anyio | (via mcp) | Async utilities | Pulled in by mcp SDK for event loop management |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mcp SDK subprocess | LangGraph agents | LangGraph adds 50KB+ overhead; this PoC uses single agent loop — LangGraph justified only in v2 multi-agent |
| openai 1.x | openai 2.x | 2.x breaks custom base_url (Zhipu endpoint); 1.x is mature final release (1.102.0) |
| FastAPI StreamingResponse | aiohttp StreamResponse | FastAPI is standard in Python web; aiohttp not required |
| Pydantic v2 | jsonschema | Pydantic v2 is required by FastAPI 0.115+ (can't downgrade) |

**Installation:**
```bash
# Option A: requirements.txt with pip
pip install fastapi[standard]>=0.115.0,<1.0 \
  pydantic>=2.7.0,<3.0 \
  uvicorn[standard]>=0.30.0 \
  openai~=1.102 \
  mcp>=1.0 \
  python-dotenv>=1.0.0

# Option B: pyproject.toml with uv/poetry
# [dependencies]
# fastapi = {version = ">=0.115.0,<1.0", extras = ["standard"]}
# pydantic = ">=2.7.0,<3.0"
# uvicorn = {version = ">=0.30.0", extras = ["standard"]}
# openai = "~=1.102"
# mcp = ">=1.0"
# python-dotenv = ">=1.0.0"
```

**Version verification:** [VERIFIED: PyPI] openai 1.102.0 final (1.x branch), mcp latest >=1.0 with stdio transport, FastAPI >=0.115.0 available. All pinned versions are current as of 2026-04.

## Architecture Patterns

### Recommended Project Structure
```
cyber-god/
├── backend/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app + CORS
│   ├── config.py                  # env var loading
│   ├── price_mcp/
│   │   ├── __init__.py
│   │   └── server.py              # MCP server: search_products tool
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── price.py               # MCP client wrapper
│   │   └── savings.py             # savings calculation
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── loop.py                # two-phase GLM + SSE formatting
│   │   └── prompt.py              # system prompt constant
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # POST /api/chat endpoint
│   └── requirements.txt or pyproject.toml
└── frontend/                      # Next.js (Phase 2)
```

### Pattern 1: MCP Subprocess Client (Async FastAPI Context)
**What:** Spawn MCP server as subprocess via stdio transport, call tools within async FastAPI route handler without blocking event loop.

**When to use:** Local tool calls from within async request handler; single subprocess per FastAPI app (reuse connection across requests).

**Implementation:** 
- Create `StdioServerParameters(command="python", args=["path/to/price_mcp/server.py"])`
- Wrap in `AsyncExitStack` for lifecycle management (startup in FastAPI lifespan event, cleanup on shutdown)
- Inside route: `await session.call_tool("search_products", {"query": item_name})`
- Tool result is dict with `content` list; extract text or JSON as needed

**Source:** [CITED: modelcontextprotocol.io/docs/develop/build-client] stdio_client pattern; [CITED: github.com/modelcontextprotocol/python-sdk] ClientSession async API

```python
# Pseudocode pattern
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

# In FastAPI lifespan
async def lifespan(app):
    # startup
    exit_stack = AsyncExitStack()
    server_params = StdioServerParameters(
        command="python",
        args=["price_mcp/server.py"],
        env=None
    )
    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
    stdio, write = stdio_transport
    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
    await session.initialize()
    app.mcp_session = session
    app.exit_stack = exit_stack
    yield
    # cleanup
    await exit_stack.aclose()

@app.post("/api/chat")
async def chat(body: ChatRequest):
    result = await app.mcp_session.call_tool("search_products", {"query": body.item_name})
    # result["content"][0]["text"] contains tool output
```

### Pattern 2: Two-Phase GLM Call (stream=False then stream=True)
**What:** First call with `stream=False` + `tool_choice="auto"` to resolve tool calls completely (avoiding GLM-4.6+ streaming tool_calls bug). Second call with `stream=True` to stream the verdict text.

**Why:** GLM-4.6/4.7 streaming tool_calls drops argument parts or returns incomplete JSON when streamed. `stream=False` on call 1 ensures complete tool definitions before execution. [CITED: github.com/sgl-project/sglang/issues/11888] (official bug report)

**Implementation:**
```python
# Call 1: resolve tools (non-streaming)
client = AsyncOpenAI(base_url="https://open.bigmodel.cn/api/paas/v4", api_key=ZHIPU_API_KEY)
messages = [{"role": "user", "content": "..."}]
tools = [{"type": "function", "function": {"name": "search_products", "parameters": {...}}}]

response1 = await client.chat.completions.create(
    model=GLM_MODEL,  # glm-4-flash or glm-4-5
    messages=messages,
    tools=tools,
    tool_choice="auto",
    stream=False  # KEY: non-streaming for complete tool calls
)

# Extract tool_calls from response1
# Execute via MCP session
# Append tool results to messages

# Call 2: stream verdict (streaming)
messages.append({"role": "assistant", "content": ..., "tool_calls": [...]})
# Append tool results as role="tool" messages
response2 = await client.chat.completions.create(
    model=GLM_MODEL,
    messages=messages,
    tools=tools,
    tool_choice="auto",
    stream=True  # KEY: now stream for text output
)

# Stream response2 chunks as Vercel protocol
```

**Source:** [CITED: CLAUDE.md D-12] confirmed; [CITED: github.com/sgl-project/sglang/issues/11888] GLM-4.6 bug; [CITED: openai-python/github] stream=True vs stream=False patterns

### Pattern 3: Vercel Data Stream Protocol Encoding (SSE)
**What:** Emit lines with format `{type}:{json_data}` where type is single char. Required types: `f:` (frame), `0:` (text), `2:` (custom data), `e:` (error/metadata), `d:` (finish).

**When to use:** When response must integrate with Vercel AI SDK `useChat` hook on frontend (Phase 2).

**Format specification:**
- `f:{"id": "message-123"}` — Frame initialization (optional, sent once at start)
- `0:"text chunk"` — Text content (streamed in chunks; quote escaping required for JSON strings)
- `2:[{"new_savings": 5000, "progress_pct": 50, "delta": -800}]` — Custom data (array-wrapped JSON object)
- `e:{"finishReason": "stop", "usage": {"promptTokens": 100, "completionTokens": 50}}` — End metadata
- `d:{"finishReason": "stop", "usage": {"promptTokens": 100, "completionTokens": 50}}` — Final data

**Headers required:**
- `x-vercel-ai-data-stream: v1` — Signals protocol version to useChat hook
- `X-Accel-Buffering: no` — Prevents nginx/reverse-proxy buffering (critical for low-latency SSE)

**Source:** [VERIFIED: ai-sdk.dev/docs/ai-sdk-ui/stream-protocol] official spec; [CITED: github.com/elementary-data/py-ai-datastream] Python implementation reference

```python
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse

@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def generate():
        # Initial frame
        yield f'f:{{"id": "msg-{uuid.uuid4()}"}}\n'
        
        # Stream text chunks from GLM
        async for chunk in response2:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                # Escape quotes in JSON string
                escaped = text.replace('"', '\\"')
                yield f'0:"{escaped}"\n'
        
        # Send structured data (savings payload)
        yield f'2:[{{"new_savings": 5000, "progress_pct": 50, "delta": -800}}]\n'
        
        # End stream with metadata
        usage = response2.usage if hasattr(response2, 'usage') else {...}
        yield f'e:{{"finishReason": "stop", "usage": {{"promptTokens": usage.prompt_tokens, "completionTokens": usage.completion_tokens}}}}\n'
        yield f'd:{{"finishReason": "stop", "usage": {{"promptTokens": usage.prompt_tokens, "completionTokens": usage.completion_tokens}}}}\n'
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-data-stream": "v1",
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        }
    )
```

### Anti-Patterns to Avoid
- **Hand-rolling JSON chunking:** Don't manually split JSON strings across chunks — use Vercel protocol format which handles escaping
- **Buffering chunks before sending:** Never collect all chunks then send — stream immediately via async generator for low latency
- **stream=True with tool_choice="required":** Causes confirmed GLM infinite loop; use `tool_choice="auto"` only
- **Storing price logic in FastAPI code:** MCP subprocess is the abstraction — FastAPI should NOT know about prices or catalog
- **Blocking event loop in tool execution:** Use `await app.mcp_session.call_tool(...)` (async) — never sync MCP calls in async handler
- **Omitting x-vercel-ai-data-stream header:** Frontend useChat hook ignores stream without this header — no data.onData callback fires

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP tool execution | Custom subprocess popen + stdin/stdout parsing | mcp SDK ClientSession | MCP spec is complex; SDK handles transport layer, message framing, async event loop integration |
| OpenAI-compatible API calls | Direct HTTP requests with openai-python protocol | AsyncOpenAI from openai SDK 1.x | SDK handles auth, retries, streaming chunks, tool_calls unpacking, custom base_url config |
| SSE stream formatting | String concatenation + manual escaping | Vercel Data Stream Protocol format | JSON escaping has edge cases; protocol version may change; use reference implementation |
| Savings calculation | Custom math in route handler | Separate tools/savings.py module | Easier to test, reuse, change discount logic later without touching routing |
| System prompt construction | Inline string in route | agent/prompt.py constant | Easier to iterate on persona, track versions, A/B test without code deployment |
| Session management for MCP | New subprocess per request | Single subprocess + AsyncExitStack in FastAPI lifespan | Subprocess spawn/teardown per request is expensive; single shared session per app instance is standard |

**Key insight:** MCP SDK is the abstraction boundary — it encapsulates all subprocess lifecycle, stdio framing, and async iteration. Reimplementing would duplicate dozens of edge cases (e.g., handling partial JSON in chunks, socket EOF during shutdown, task cancellation).

## Common Pitfalls

### Pitfall 1: GLM-4.6+ Streaming Tool Calls Incomplete
**What goes wrong:** When calling GLM with `stream=True` and `tools=[...]`, tool call arguments are returned in chunks but often incomplete or malformed. Long delays before first chunk. Some tool_calls appear with `null` for arguments field.

**Why it happens:** GLM-4.6/4.7 backend has a bug in streaming tool_calls—the server sends argument chunks before the full JSON is ready, and the streaming serializer doesn't properly reassemble them. [CITED: github.com/sgl-project/sglang/issues/11888]

**How to avoid:** Use `stream=False` for the first call (tool resolution). This returns complete `tool_calls` list with all arguments populated. Execute tools, then use `stream=True` for verdict text generation.

**Warning signs:** 
- Tool call appears with `arguments: null` or empty string
- Long delay (>2s) before first streaming chunk on tool call
- Tool execution fails because JSON can't parse incomplete argument

### Pitfall 2: Vercel Protocol Line Escaping
**What goes wrong:** Sending `0:"{"nested": "json"}"` breaks the parser because inner quotes conflict with outer quotes. Frontend receives garbage or stream halts.

**Why it happens:** Vercel protocol `0:` prefix requires JSON string escaping. A text chunk containing `"` must be sent as `0:"he said \"hello\""` not `0:"he said "hello""`.

**How to avoid:** Always escape quotes: `chunk.replace('"', '\\"')` before wrapping in `0:"..."\n`. Use reference implementation (py-ai-datastream) as guide.

**Warning signs:**
- Frontend useChat receives partial text then stream closes
- Browser DevTools shows SyntaxError parsing `0:` lines
- Python json.loads() fails on Vercel protocol line

### Pitfall 3: Subprocess MCP Session Lifecycle in Async Context
**What goes wrong:** If MCP subprocess is created fresh per request (e.g., in route handler), spawning fails after first few requests. Event loop crashes with "cannot create new event loop". Subprocess becomes zombie process.

**Why it happens:** subprocess.Popen is synchronous; multiple concurrent requests create popen race. StdioServerParameters expects a single long-lived event loop for the entire app. Spawning in every route creates loop conflicts.

**How to avoid:** Create MCP session once in FastAPI `@app.lifespan()` async context manager. Store in `app.state` or app instance variable. Reuse `ClientSession` across all requests.

**Warning signs:**
- "Event loop is closed" error after 5-10 requests
- Subprocess.py processes accumulate (visible in `ps aux`)
- stderr from subprocess appears sporadically

**Code pattern:**
```python
@app.lifespan
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        server_params = StdioServerParameters(...)
        stdio_transport = await stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        app.mcp_session = await stack.enter_async_context(
            ClientSession(stdio, write)
        )
        await app.mcp_session.initialize()
        yield
        # Cleanup happens automatically in __aexit__
```

### Pitfall 4: Missing X-Accel-Buffering Header
**What goes wrong:** Stream works in local dev (direct FastAPI) but stalls when deployed behind nginx reverse proxy. Frontend receives all text at once (100+ seconds later) instead of streaming.

**Why it happens:** nginx by default buffers StreamingResponse until close. `X-Accel-Buffering: no` tells nginx to disable buffering for this response.

**How to avoid:** Always include `X-Accel-Buffering: no` in StreamingResponse headers. Does not affect direct FastAPI connections but enables proxies to stream immediately.

**Warning signs:**
- Works in localhost:8000 but not behind proxy
- Frontend receives zero chunks then entire response at once
- Response takes 60+ seconds

### Pitfall 5: tool_choice="required" Infinite Loop
**What goes wrong:** GLM call with `tool_choice="required"` never completes. Server keeps asking for tool calls even after you execute them and append results.

**Why it happens:** GLM interprets `tool_choice="required"` as "must always return tool_calls". After execution, subsequent message with `role="tool"` result still triggers another tool call, which triggers another, etc. [CITED: CLAUDE.md D-12] confirms this is confirmed GLM bug.

**How to avoid:** Always use `tool_choice="auto"`. Let GLM decide whether to call tools. After tools execute, set `tool_choice="auto"` on the second call (verdict generation), not "required".

**Warning signs:**
- Response never returns (timeout after 30s)
- Each tool_call in response has `type: "tool_call"` even though you executed the previous ones

### Pitfall 6: OpenAI SDK v2.x Breaking Custom base_url
**What goes wrong:** Installed openai 2.30.0. Initialize `client = OpenAI(base_url="https://open.bigmodel.cn/api/paas/v4", api_key=KEY)`. Request fails with auth error or 404 not found.

**Why it happens:** openai 2.x refactored the API client to validate base_url against OpenAI domains. Custom base_url support (for Zhipu or other OpenAI-compatible providers) was removed. [CITED: CLAUDE.md] warns to use 1.x only.

**How to avoid:** Pin `openai~=1.102` in requirements.txt. 1.102.0 is the final release of 1.x and is stable/mature. Never allow `pip install openai` to default to 2.x.

**Warning signs:**
- "Unsupported base_url" error or validation error on client init
- 404 or 403 on API call (because 2.x hits OpenAI domain, not Zhipu)
- Installation log shows `openai-2.x.x`

## Code Examples

### Vercel Data Stream Protocol Example (Complete)
```python
# Source: Vercel AI SDK documentation + py-ai-datastream reference
import json
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from uuid import uuid4

@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def generate():
        # 1. Frame initialization
        message_id = str(uuid4())
        frame = {"id": message_id}
        yield f'f:{json.dumps(frame)}\n'
        
        # 2. Text chunks (streaming from GLM)
        text_buffer = ""
        async for chunk in glm_response:
            if chunk.choices[0].delta.content:
                text_buffer += chunk.choices[0].delta.content
                # Send each delta as-is (Vercel SDK handles buffering)
                yield f'0:{json.dumps(chunk.choices[0].delta.content)}\n'
        
        # 3. Custom structured data (savings impact)
        savings_data = {
            "new_savings": 5000,
            "progress_pct": 50,
            "delta": -800
        }
        yield f'2:{json.dumps([savings_data])}\n'  # array-wrapped
        
        # 4. Error/finish metadata
        finish_reason = "stop"
        usage = {"promptTokens": 100, "completionTokens": 50}
        metadata = {
            "finishReason": finish_reason,
            "usage": usage,
            "isContinued": False
        }
        yield f'e:{json.dumps(metadata)}\n'
        
        # 5. Final data (duplicate for compatibility)
        yield f'd:{json.dumps(metadata)}\n'
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-data-stream": "v1",
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

### MCP Client Call Pattern (Async FastAPI)
```python
# Source: modelcontextprotocol.io build-client tutorial (adapted for FastAPI)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

# In app startup
async def setup_mcp(app):
    app.mcp_exit_stack = AsyncExitStack()
    await app.mcp_exit_stack.__aenter__()
    
    server_params = StdioServerParameters(
        command="python",
        args=["/path/to/price_mcp/server.py"],
        env=None
    )
    
    stdio_transport = await app.mcp_exit_stack.enter_async_context(
        stdio_client(server_params)
    )
    stdio, write = stdio_transport
    
    app.mcp_session = await app.mcp_exit_stack.enter_async_context(
        ClientSession(stdio, write)
    )
    
    await app.mcp_session.initialize()
    tools = await app.mcp_session.list_tools()
    print(f"Connected with tools: {[t.name for t in tools.tools]}")

# In route handler
@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Call MCP tool
    tool_result = await app.mcp_session.call_tool(
        "search_products",
        {"query": "盲盒"}
    )
    # tool_result is CallToolResult with content list
    price_text = tool_result.content[0].text  # Extract text response
    
    # Use price_text in messages for GLM
    messages.append({
        "role": "tool",
        "tool_call_id": tool_calls[0].id,
        "content": price_text
    })
```

### OpenAI SDK 1.102 Async Streaming with GLM
```python
# Source: openai-python 1.x AsyncOpenAI docs
from openai import AsyncOpenAI
import os

client = AsyncOpenAI(
    base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key=os.getenv("ZHIPU_API_KEY")
)

# First call: stream=False for tool resolution
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search for product prices",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    }
]

messages = [{"role": "user", "content": "我想买一个盲盒，花 800 块"}]

response1 = await client.chat.completions.create(
    model=os.getenv("GLM_MODEL", "glm-4-flash"),
    messages=messages,
    tools=tools,
    tool_choice="auto",
    stream=False  # Complete tool calls
)

# Handle tool calls
if response1.choices[0].message.tool_calls:
    for tool_call in response1.choices[0].message.tool_calls:
        if tool_call.function.name == "search_products":
            # Execute via MCP
            tool_result = await app.mcp_session.call_tool(
                "search_products",
                json.loads(tool_call.function.arguments)
            )
            # Append results
            messages.append({"role": "assistant", "content": None, "tool_calls": response1.choices[0].message.tool_calls})
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result.content[0].text
            })

# Second call: stream=True for verdict
response2 = await client.chat.completions.create(
    model=os.getenv("GLM_MODEL", "glm-4-flash"),
    messages=messages,
    tools=tools,
    tool_choice="auto",
    stream=True  # Stream verdict text
)

# Iterate streaming chunks
async for chunk in response2:
    if chunk.choices[0].delta.content:
        yield chunk.choices[0].delta.content
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct HTTP requests to MCP server | MCP SDK with stdio transport | MCP v1.0 (2024) | SDK abstracts transport complexity; subprocess lifecycle automatic |
| LangChain agent loops | Raw two-phase GLM calls | 2025+ | Lighter weight for PoC; LangChain justified only when multi-agent |
| openai 0.27 SDK | openai 1.x SDK | 2023 | SDK now handles streaming, tool_calls, custom base_url natively |
| Vercel AI v2 protocol | Vercel AI v4 Data Stream Protocol | 2024 | v4 simplified line format; useChat requires explicit x-vercel-ai-data-stream header |
| Hard-coded env vars | env var + .env loading | Standard | python-dotenv is convention for local dev without deployment config files |

**Deprecated/outdated:**
- **sse-starlette library:** FastAPI 0.115+ has native SSE support; third-party library not needed
- **openai 2.x for Zhipu:** Breaks custom base_url; use 1.x only
- **Vercel AI SDK v5/v6:** Dropped plain-SSE backend support; pin to v4
- **Pydantic v1:** FastAPI 0.115+ requires v2; can't use v1

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | mcp SDK 1.0+ subprocess lifecycle is production-safe in async FastAPI context | Architecture: MCP Subprocess Client, Pitfall 3 | If wrong: subprocess orphaning, event loop crashes under load; mitigate by load-testing before Phase 2 |
| A2 | `stream=False` call 1 + `stream=True` call 2 completely avoids GLM tool_calls streaming bugs | Pattern 2 | If wrong: incomplete tool arguments still possible; mitigate by adding explicit validation of tool_calls before execution |
| A3 | Vercel Data Stream Protocol `2:[{json}]` format is correctly parsed by useChat onData callback | Pattern 3, Code Examples | If wrong: frontend doesn't receive savings data; mitigate by curl-testing phase gate before Phase 2 |
| A4 | `X-Accel-Buffering: no` header is sufficient for nginx proxies to stream SSE correctly | Pitfall 4 | If wrong: nginx still buffers in some configs; mitigate by explicit nginx config directive testing |
| A5 | GLM-4-flash (free tier) reliably calls both search_products + calculate_savings_impact tools on typical purchase impulse | D-02, TOOL-02 | If wrong: retry fallback (D-05) is insufficient; mitigate by testing multiple purchase scenarios in integration tests |

**If any of these are wrong**, the planner must add explicit validation tasks (curl testing, integration tests, load tests) before Phase 2 starts.

## Open Questions

1. **Zhipu model string confirmation:** Does `glm-4-5` resolve correctly on open.bigmodel.cn as of April 2026, or has Zhipu renamed/deprecated it?
   - What we know: CLAUDE.md D-15 states "glm-4-5" is prod model
   - What's unclear: Zhipu may have renamed to glm-4-5-turbo or glm-5 by now
   - Recommendation: Add to Phase 1 gate: confirm model string with Zhipu console before phase complete

2. **stream=False call guarantees complete tool_calls:**  Does GLM guarantee that `stream=False` on call 1 returns complete tool_calls with all arguments populated as single response, or can it still be partial?
   - What we know: CLAUDE.md D-12 says "stream=False for tool resolution"
   - What's unclear: No official Zhipu documentation verifies this assumption
   - Recommendation: Test with actual Zhipu endpoint in Phase 1 implementation; if incomplete, add validation loop

3. **MCP stdio subprocess event loop integration:** When AsyncExitStack wraps stdio_client, does the MCP ClientSession properly integrate with the FastAPI event loop, or does it create a separate event loop that causes conflicts?
   - What we know: MCP SDK documentation shows this pattern
   - What's unclear: No async/await gotchas documented for production async apps with concurrent requests
   - Recommendation: Load test with 10+ concurrent requests per second during Phase 1; monitor for event loop errors

4. **useChat data callback 2: parsing:** What is the exact useChat onData callback signature in ai@^4 for intercepting `2:` data chunks? Does useChat expose this directly or is it merged into another callback?
   - What we know: CLAUDE.md D-13 says payload rides `2:` channel
   - What's unclear: Exact API and where in useChat lifecycle it fires
   - Recommendation: Phase 2 research must verify before frontend implementation

5. **GLM-4-flash tool calling reliability:** Does GLM-4-flash reliably invoke both search_products AND calculate_savings_impact on a purchase impulse, or must we force it with fallback?
   - What we know: CLAUDE.md D-05/D-06 says retry once if no tool calls
   - What's unclear: What is the baseline success rate for two-tool calling on typical impulses?
   - Recommendation: Test 20+ diverse purchase impulses in Phase 1; track success rate; if <90%, strengthen retry message

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.11.5 (local; 3.12 for prod) | None — phase requires Python |
| pip / uv | Package management | ✓ | pip 25.3 | uv available as alternative |
| openai SDK 1.102 | GLM API calls | ✓ | 1.102.0 available on PyPI | None — must pin 1.x |
| mcp SDK | MCP subprocess | ✓ | >=1.0 available on PyPI | None — required for D-16 |
| FastAPI 0.115+ | HTTP server | ✓ | >=0.115.0 available on PyPI | None — hard requirement |
| Pydantic 2.7+ | Validation | ✓ | >=2.7.0 available on PyPI | None — required by FastAPI 0.115+ |
| uvicorn[standard] | ASGI server + uvloop | ✓ | >=0.30.0 available on PyPI | Use base uvicorn, no uvloop (slower but works) |

**Missing dependencies with no fallback:**
- None — all required packages available

**Missing dependencies with fallback:**
- uvloop (part of uvicorn[standard]): If unavailable, install base `uvicorn` without [standard] (loses optimization but works)

**Skip condition:** Phase 1 is backend-only; frontend dependencies (Node.js, npm, Next.js) not needed until Phase 2.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No user auth in PoC (all state in frontend localStorage) |
| V3 Session Management | No | No sessions (stateless request-response) |
| V4 Access Control | Yes | CORS whitelist via ALLOWED_ORIGINS env var; validate origin header |
| V5 Input Validation | Yes | Pydantic request validation; reject invalid JSON/types |
| V6 Cryptography | No | No sensitive data encryption (PoC only); ZHIPU_API_KEY in .env (not in git) |
| V7 Error Handling | Yes | Don't leak stack traces; emit in-character error messages (D-06) before streaming |
| V8 Data Protection | No | No persistent user data; localStorage only |
| V14 Configuration | Yes | Environment variables (ZHIPU_API_KEY, GLM_MODEL, ALLOWED_ORIGINS); validate all on startup |

### Known Threat Patterns for (FastAPI + OpenAI API + MCP Subprocess + SSE)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leak in subprocess args | Disclosure | Never log subprocess command; mask ZHIPU_API_KEY in logs; load from env only |
| CORS misconfiguration allows cross-origin requests | Tampering | Validate ALLOWED_ORIGINS from env var; default to empty (deny all) if not set |
| Subprocess injection via tool parameters | Tampering/Execution | MCP SDK sanitizes all tool input via ClientSession; tool args are JSON-parsed, not shell-executed |
| SSE stream contains user data | Disclosure | This PoC streams only agent verdicts (no user savings details in stream); validate before sending |
| Unbounded streaming memory | Denial of Service | StreamingResponse is async generator (no buffering); each chunk sent immediately; test timeout on long-running responses |
| GLM API calls with invalid auth | Disclosure | Validate ZHIPU_API_KEY on startup; fail fast if missing; return 500 before streaming begins |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: PyPI] openai 1.102.0, mcp >=1.0, FastAPI >=0.115.0 versions available and current as of 2026-04
- [CITED: modelcontextprotocol.io/docs/develop/build-client] Official MCP Python SDK documentation; stdio_client pattern, ClientSession async API
- [CITED: github.com/modelcontextprotocol/python-sdk] Official MCP Python SDK repository; StdioServerParameters, AsyncExitStack pattern
- [CITED: CLAUDE.md] Project-defined stack constraints; D-12 two-phase streaming strategy; D-16 MCP subprocess requirement
- [CITED: github.com/sgl-project/sglang/issues/11888] Official bug report: GLM-4.6 streaming tool_calls incomplete; confirmed mitigation is stream=False
- [CITED: ai-sdk.dev/docs/ai-sdk-ui/stream-protocol] Official Vercel AI SDK documentation; stream protocol specification (f:, 0:, 2:, e:, d: format)
- [CITED: github.com/elementary-data/py-ai-datastream] Python reference implementation of Vercel Data Stream Protocol
- [CITED: openai-python/github] Official OpenAI Python SDK repository; AsyncOpenAI streaming patterns

### Secondary (MEDIUM confidence)
- [CITED: sahansera.dev/streaming-apis-python-nextjs-part1/] FastAPI + Next.js streaming architecture guide; validated patterns
- [CITED: github.com/vercel/ai Discussion #2840] Community discussion: Handling JSON Data Stream with FastAPI; x-vercel-ai-data-stream header requirement confirmed
- [CITED: medium.com/h7w openai-python-library-version-1-102-0] Medium article: OpenAI Python SDK 1.102.0 final release announcement
- [CITED: docs.vllm.ai GLM/GLM5] vLLM documentation; GLM-5 function calling support confirmation

### Tertiary (LOW confidence)
- Documentation URLs from CLAUDE.md (Zhipu, Vercel) — unreachable in some regions, marked MEDIUM by CLAUDE.md already
- Community forum posts about GLM tool calling — individual experiences, not official

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — All library versions verified on PyPI; CLAUDE.md pinned versions match available releases
- Architecture patterns: **HIGH** — MCP SDK pattern from official docs; Vercel protocol from official spec; two-phase GLM strategy confirmed in bug reports
- Pitfalls: **MEDIUM-HIGH** — Most from official bug reports or documented issues; subprocess lifecycle assumption (A1) is MEDIUM confidence (no production-scale FastAPI + MCP case study found)
- Open questions: **LOW** — Require user confirmation or integration testing before locked decisions

**Research date:** 2026-04-18
**Valid until:** 2026-05-18 (30 days; stack is stable but MCP/GLM tooling evolves; recommend refresh if Zhipu rolls out new models or FastAPI releases 0.140+)
**Dependencies:** CONTEXT.md decisions locked in; CLAUDE.md constraints must be honored; REQUIREMENTS.md maps to phase tasks
