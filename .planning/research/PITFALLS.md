# Domain Pitfalls

**Domain:** AI agent chat — GLM-5 (Zhipu AI) + FastAPI StreamingResponse + Vercel AI SDK useChat
**Project:** 赛博财神爷 (Cyber God of Wealth)
**Researched:** 2026-04-18
**Confidence:** MEDIUM — Zhipu cloud API behavior verified against multiple community sources; Vercel AI SDK protocol verified from official docs

---

## Critical Pitfalls

Mistakes that cause rewrites or the entire streaming pipeline to silently fail.

---

### Pitfall 1: Wrong SSE format for Vercel AI SDK useChat

**What goes wrong:** The backend streams raw text or a non-standard SSE format. useChat receives the stream but renders nothing — the message stays empty, or the text appears all at once after the stream ends.

**Why it happens:** useChat does not parse arbitrary SSE or raw text streams. It expects the **Vercel AI SDK Data Stream Protocol** — a specific line-based format where each line is `{type_code}:{json_value}\n`. Sending `data: Hello\n\n` (standard SSE) or plain `Hello` bytes will cause silent failure or garbled output.

**Required format (Data Stream Protocol):**
```
f:{"messageId":"abc-123"}\n
0:"Hello"\n
0:", world"\n
e:{"finishReason":"stop","usage":{"promptTokens":20,"completionTokens":10},"isContinued":false}\n
d:{"finishReason":"stop","usage":{"promptTokens":20,"completionTokens":10}}\n
```

Key type codes:
- `f:` — message start (messageId)
- `0:` — text delta (quoted JSON string)
- `2:` — data part (arbitrary JSON, used for structured payload like progress bar data)
- `9:` — tool call
- `a:` — tool result
- `e:` — step finish
- `d:` — stream done

**Required headers from FastAPI:**
```python
headers = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "x-vercel-ai-data-stream": "v1",
}
return StreamingResponse(generator(), headers=headers, media_type="text/event-stream")
```

**Warning signs:**
- useChat `messages` array has an empty assistant message after streaming
- Text appears only after stream fully completes (not token by token)
- Browser DevTools shows streamed bytes but React state never updates

**Prevention:** Use the Data Stream Protocol format exactly. Test with `curl -N http://localhost:8000/api/chat` and verify each yielded line matches the format above before wiring up the frontend.

**Phase:** Phase 1 (backend streaming endpoint)

---

### Pitfall 2: FastAPI StreamingResponse buffers entire response before sending

**What goes wrong:** The generator function runs to completion before the first byte reaches the client. The user sees no streaming; the response arrives all at once after a multi-second delay.

**Why it happens:** Three causes:

1. **Sync generator in async route** — using a regular `def` generator inside an `async def` route blocks the event loop.
2. **Missing `await anyio.sleep(0)`** — the async generator never yields control back to the event loop between chunks.
3. **Middleware buffering** — an intermediary (Nginx, Railway's proxy, or a development proxy) buffers the response.

**Prevention:**
```python
import anyio

async def stream_generator():
    async for chunk in openai_stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield f'0:{json.dumps(delta.content)}\n'
            await anyio.sleep(0)  # yield control to event loop
```

Always use `async def` + `async for` with the AsyncOpenAI client. Never accumulate chunks before yielding.

**For Nginx / Railway / Render proxies:** The `X-Accel-Buffering: no` header (included above) disables Nginx buffering. On Railway and Render, no additional config is required — they honour this header.

**Warning signs:**
- curl receives all bytes in a single burst
- Network tab shows a single large response chunk
- No tokens appear during streaming; text appears complete

**Phase:** Phase 1 (backend streaming endpoint)

---

### Pitfall 3: GLM-5 / GLM-4 streaming tool_calls require manual delta accumulation

**What goes wrong:** The backend tries to read `chunk.choices[0].delta.tool_calls[0].function.arguments` as a complete JSON string on a single chunk. It receives partial JSON fragments (e.g., `{"item_n`) and crashes with a `json.JSONDecodeError`, or silently discards the tool call.

**Why it happens:** When streaming is enabled (`stream=True`) and the model emits a tool call, the `function.arguments` field arrives as incremental string fragments across multiple chunks — identical to how OpenAI streaming works. Each chunk has a `tool_calls[0].index` and `tool_calls[0].function.arguments` that must be concatenated before parsing.

**Note on GLM cloud API (bigmodel.cn):** The Zhipu cloud API is genuinely OpenAI-compatible for streaming tool calls. The `finish_reason` will be `"tool_calls"` when a tool call is complete. However, `tool_stream` defaults to `false` — if not explicitly set, tool call arguments may arrive as a single chunk at end-of-stream rather than being streamed token-by-token. This is safer for this project but must be understood.

**Prevention — accumulation pattern:**
```python
tool_calls_accumulator = {}

async for chunk in stream:
    delta = chunk.choices[0].delta
    
    # Accumulate tool call argument fragments
    if delta.tool_calls:
        for tc_delta in delta.tool_calls:
            idx = tc_delta.index
            if idx not in tool_calls_accumulator:
                tool_calls_accumulator[idx] = {
                    "id": tc_delta.id or "",
                    "type": "function",
                    "function": {"name": tc_delta.function.name or "", "arguments": ""}
                }
            if tc_delta.function.arguments:
                tool_calls_accumulator[idx]["function"]["arguments"] += tc_delta.function.arguments
    
    # Text delta
    if delta.content:
        yield f'0:{json.dumps(delta.content)}\n'
        await anyio.sleep(0)
    
    # Tool call complete
    if chunk.choices[0].finish_reason == "tool_calls":
        for tc in tool_calls_accumulator.values():
            args = json.loads(tc["function"]["arguments"])
            result = dispatch_tool(tc["function"]["name"], args)
            # Continue second LLM call with tool results...
```

**Recommendation for this project:** Set `tool_stream=False` (or omit it, as it defaults to False) on the Zhipu API call. This causes the complete tool call to arrive in a single chunk, eliminating argument accumulation complexity. The trade-off is slightly higher latency before tool execution, which is acceptable for a PoC.

**Warning signs:**
- `json.JSONDecodeError: Unterminated string` when parsing tool arguments
- Tool function never executes despite model emitting `finish_reason: "tool_calls"`
- `AttributeError: 'NoneType' object has no attribute 'arguments'` on early chunks

**Phase:** Phase 1 (backend tool calling loop)

---

### Pitfall 4: tool_choice="required" causes infinite generation loop on GLM

**What goes wrong:** Setting `tool_choice="required"` causes GLM-4.x models to enter an infinite generation loop — tokens stream forever and `finish_reason` never becomes `"tool_calls"` or `"stop"`.

**Why it happens:** This is a confirmed bug across GLM-4.5, GLM-4.6, and GLM-4.7 when hosted via SGLang and some other inference backends. The root cause is that frameworks enforce JSON tool call format on a model that natively uses a different internal format, putting it out of distribution. The Zhipu cloud API (bigmodel.cn) may behave differently but the risk exists.

**Prevention:** Never use `tool_choice="required"`. Rely on the system prompt to instruct the model to call the tools. For this project, the 财神 system prompt should clearly instruct the model to call `get_mock_price` and `calculate_savings_impact` before responding. Use `tool_choice="auto"` (the default).

Add a generation safeguard:
```python
MAX_TOKENS = 1024  # or use max_tokens parameter

response = await client.chat.completions.create(
    model=settings.model,
    messages=messages,
    tools=tools,
    tool_choice="auto",  # NEVER "required"
    max_tokens=MAX_TOKENS,
    stream=True,
)
```

**Warning signs:**
- Streaming never terminates; connection stays open indefinitely
- Token count climbs past 2000 with no `finish_reason`
- Model repeats the same tool call arguments in a loop

**Phase:** Phase 1 (backend tool calling loop) — embed safeguard from day one

---

### Pitfall 5: Structured data payload (progress bar) never reaches the frontend

**What goes wrong:** The progress bar stays at its pre-stream value. The final JSON payload (new savings, progress %) is sent but the frontend never reads it or updates state.

**Why it happens:** The project design sends structured data "at end of stream" as a `2:` data part. There are three failure modes:

**Failure mode A — Wrong delivery mechanism.** The structured JSON is appended as plain text in the `0:` text stream. useChat renders it literally in the chat bubble instead of routing it to a data handler.

**Failure mode B — Reading data in wrong callback.** The developer reads structured data in `onFinish` instead of `onData`. In the Vercel AI SDK, `message.data` is not reliably accessible inside `onFinish` — this is a documented gap. The `onData` callback fires for each `2:` data part as it arrives.

**Failure mode C — State update timing.** The progress bar state is updated only inside `onFinish`, which fires after the stream closes. If the final `2:` part arrives at the same time as `d:` (done), React batches the update and the bar may not animate — it just jumps.

**Prevention:**

Backend — emit structured data as a `2:` part, not inside the text:
```python
# At end of stream, after text generation:
progress_payload = {
    "new_savings": new_savings,
    "progress_pct": progress_pct,
    "delta": delta,
    "verdict": "reject"
}
yield f'2:{json.dumps([progress_payload])}\n'  # note: array-wrapped
```

Frontend — use `onData` to capture and apply the payload:
```typescript
const { messages } = useChat({
  api: "/api/chat",
  onData: (dataParts) => {
    // dataParts is the array value from 2: parts
    for (const part of dataParts) {
      if (part.new_savings !== undefined) {
        setSavings(part.new_savings);
        setProgressPct(part.progress_pct);
      }
    }
  },
});
```

**Warning signs:**
- Progress bar never changes after a chat turn
- Structured JSON visible as raw text inside the chat bubble
- `onFinish` fires but `message.data` is undefined

**Phase:** Phase 2 (frontend progress bar integration)

---

## Moderate Pitfalls

---

### Pitfall 6: CORS blocks the frontend from reaching the FastAPI backend

**What goes wrong:** Browser console shows `Access-Control-Allow-Origin` error. The chat submit sends no request (or OPTIONS preflight is rejected), and useChat enters an error state silently.

**Why it happens:** FastAPI does not add CORS headers by default. The frontend (localhost:3000 in dev, Vercel domain in prod) is a different origin than the FastAPI backend (localhost:8000 / Railway URL).

**Prevention:**
```python
from fastapi.middleware.cors import CORSMiddleware
import os

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)
```

Set `ALLOWED_ORIGINS` in the Railway/Render environment to the production Vercel domain, e.g., `https://pay-chat-agent.vercel.app`. Do not use `allow_origins=["*"]` in production alongside `allow_credentials=True` — this combination is rejected by browsers.

**Warning signs:**
- Browser console: `CORS policy: No 'Access-Control-Allow-Origin' header`
- OPTIONS preflight returns 405 Method Not Allowed
- useChat `error` state is set but no network request appears in DevTools

**Phase:** Phase 1 (backend setup)

---

### Pitfall 7: Vercel function timeout kills long-running streams

**What goes wrong:** The streaming response is cut off mid-sentence after exactly 10 seconds (Hobby plan) or 60 seconds (Pro plan) when the Next.js frontend is deployed on Vercel.

**Why it happens:** Vercel Serverless Functions have hard execution timeouts. If useChat is calling a Next.js API route that proxies to the FastAPI backend, the Next.js function times out even if the FastAPI server is still streaming.

**Prevention for this project:** This project uses a direct frontend-to-FastAPI connection (useChat `api` prop points directly to the Railway/Render backend URL). A Next.js proxy route is NOT needed and should NOT be added — it introduces the timeout problem unnecessarily.

Configure useChat to call the backend directly:
```typescript
const { messages, input, handleInputChange, handleSubmit } = useChat({
  api: process.env.NEXT_PUBLIC_API_URL + "/api/chat",
});
```

Set `NEXT_PUBLIC_API_URL` in Vercel environment variables to the Railway/Render backend URL.

**Warning signs:**
- Chat responses truncated at a consistent length
- useChat `error` state fires after exactly 10/60 seconds
- Works fine in local development but breaks on Vercel

**Phase:** Phase 3 (deployment)

---

### Pitfall 8: Next.js App Router SSE route handler buffers before streaming

**What goes wrong:** If a Next.js API route (`app/api/chat/route.ts`) is added as a proxy, the route handler buffers the entire response before sending it to the browser.

**Why it happens:** Next.js waits for the route handler async function to resolve its `return` statement. If the handler `await`s the entire upstream response before returning `new Response(stream)`, nothing streams.

**Prevention:** If a proxy route is ever needed, return the `ReadableStream` immediately and pipe asynchronously. Also add:
```typescript
export const dynamic = "force-dynamic";
export const runtime = "nodejs"; // or "edge" — edge has lower timeout on free tier
```

Without `dynamic = "force-dynamic"`, Next.js may cache or statically optimize the route.

**Best practice for this project:** Skip the proxy entirely. Have useChat hit the FastAPI backend URL directly.

**Phase:** Phase 3 (deployment) — avoid by design

---

### Pitfall 9: Windows venv activation blocked by PowerShell execution policy

**What goes wrong:** Running `.\.venv\Scripts\Activate.ps1` in PowerShell throws: `cannot be loaded because running scripts is disabled on this system`.

**Why it happens:** Windows PowerShell defaults to `Restricted` execution policy, blocking `.ps1` scripts.

**Prevention — one-time fix (run as Administrator):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Alternative — bypass per-session (no admin required):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\Activate.ps1
```

**Alternative — bypass uvicorn PATH issue entirely:**
```powershell
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Using `python -m uvicorn` bypasses the PATH issue because it invokes uvicorn as a Python module rather than looking for a binary in `Scripts/`.

**Additional Windows gotcha — uvicorn `--reload` instability:**
uvicorn 0.29.x has known reload issues on Windows. Pin to `uvicorn==0.28.1` in requirements.txt until this is resolved upstream, or use `fastapi-cli` (`fastapi dev main.py`) which handles reload more reliably.

**Warning signs:**
- PowerShell: `running scripts is disabled on this system`
- `'uvicorn' is not recognized as an internal or external command`
- Reload causes repeated `Error in sys.excepthook` on Windows

**Phase:** Phase 0 (local dev setup)

---

### Pitfall 10: CRLF line endings break uvicorn startup on Windows Git checkouts

**What goes wrong:** `uvicorn main:app` starts but immediately crashes with a syntax error, or the `main.py` file appears valid but cannot be imported.

**Why it happens:** Git on Windows may convert LF to CRLF on checkout. Python is tolerant of CRLF in most cases, but shell scripts (`.sh` files, Docker entrypoints) or files with shebang lines will fail. More commonly, the issue surfaces in `requirements.txt` where CRLF causes `pip install` to misread package names.

**Prevention:** Add a `.gitattributes` file to the repo root:
```
* text=auto
*.py text eol=lf
*.sh text eol=lf
requirements*.txt text eol=lf
```

**Phase:** Phase 0 (project setup)

---

## Minor Pitfalls

---

### Pitfall 11: GLM reasoning_content field breaks naive delta parsing

**What goes wrong:** GLM-4.6+ streaming responses include a `reasoning_content` field in the delta alongside `content`. Code that assumes `delta.content` is always a string crashes with `TypeError` when `reasoning_content` is present and `content` is `None`.

**Prevention:**
```python
content = chunk.choices[0].delta.content or ""
# Explicitly ignore reasoning_content — it is internal chain-of-thought
# and should not be streamed to the user
```

**Phase:** Phase 1 (backend streaming)

---

### Pitfall 12: localStorage savings state goes out of sync with server-sent progress

**What goes wrong:** The user edits their savings target in one tab. The progress bar in another tab shows stale data. Or: the user refreshes mid-stream and the progress bar resets to the localStorage value before the Agent response re-hydrates it.

**Why it happens:** localStorage is tab-local and synchronous. The Agent's structured data payload is the authoritative source of truth for progress, but localStorage is loaded first on mount.

**Prevention:** On component mount, read localStorage. After every successful agent response that includes a `2:` data part, write the new values back to localStorage. Treat the agent response as the write-through, not localStorage as the source of truth.

```typescript
// On mount: hydrate from localStorage
const [savings, setSavings] = useState(() => {
  return Number(localStorage.getItem("current_savings") ?? "5000");
});

// In onData: update state AND write through to localStorage
onData: (parts) => {
  for (const part of parts) {
    if (part.new_savings !== undefined) {
      setSavings(part.new_savings);
      localStorage.setItem("current_savings", String(part.new_savings));
    }
  }
}
```

**Phase:** Phase 2 (frontend state management)

---

### Pitfall 13: FastAPI endpoint returns 422 on useChat message format

**What goes wrong:** useChat sends a POST body of `{"messages": [...], "id": "..."}`. The FastAPI endpoint uses a Pydantic model that only expects `{"messages": [...]}` and returns HTTP 422 Unprocessable Entity. useChat swallows this silently and the chat freezes.

**Why it happens:** useChat adds extra fields (`id`, and optionally `data`) to the request body. If the Pydantic model uses strict validation or does not accept extra fields, it rejects the request.

**Prevention:**
```python
from pydantic import BaseModel
from typing import Any

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    id: str | None = None  # useChat sends this
    data: dict[str, Any] | None = None  # optional, useChat may send

    model_config = {"extra": "ignore"}  # silently drop unknown fields
```

**Phase:** Phase 1 (backend endpoint definition)

---

### Pitfall 14: Progress bar animation blocked by React state update coalescing

**What goes wrong:** The progress bar jumps from old value to new value instantly instead of animating, because the state update happens in a synchronous event handler callback at the end of stream.

**Why it happens:** React 18 batches state updates in event handlers. The `onData` callback may fire synchronously at stream end, coalescing with the `messages` state update.

**Prevention:** Wrap the progress update in `startTransition` to mark it as a non-urgent update, letting React render the streaming text first:
```typescript
import { startTransition } from "react";

onData: (parts) => {
  for (const part of parts) {
    if (part.progress_pct !== undefined) {
      startTransition(() => {
        setProgressPct(part.progress_pct);
      });
    }
  }
}
```

**Phase:** Phase 2 (frontend polish)

---

## Phase-Specific Warning Summary

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|---------------|------------|
| 0 | Windows dev setup | PowerShell execution policy blocks venv | Use `python -m uvicorn`; set RemoteSigned policy |
| 0 | Git checkout | CRLF line endings break scripts | Add `.gitattributes` |
| 1 | Backend streaming | Wrong SSE format for useChat | Implement Data Stream Protocol exactly |
| 1 | Backend streaming | StreamingResponse buffers | Use async generator + `anyio.sleep(0)` |
| 1 | Tool calling | Delta accumulation crashes | Accumulate args across chunks; prefer `tool_stream=False` |
| 1 | Tool calling | Infinite loop | Never use `tool_choice="required"` |
| 1 | Backend endpoint | 422 on Pydantic model | Use `extra="ignore"` on ChatRequest model |
| 1 | GLM quirks | `reasoning_content` breaks delta parsing | Always use `delta.content or ""` |
| 1 | Networking | CORS blocks frontend | Add CORSMiddleware with explicit origins from env |
| 2 | Progress bar | Structured data never updates bar | Use `onData` callback, not `onFinish` |
| 2 | Progress bar | localStorage desync | Write-through on every agent response |
| 2 | Progress bar | Animation blocked by batching | Wrap state update in `startTransition` |
| 3 | Deployment | Vercel function timeout | Call FastAPI directly from useChat, no Next.js proxy |
| 3 | Deployment | Next.js proxy buffers stream | Use `dynamic = "force-dynamic"`, or skip proxy |

---

## Sources

- Vercel AI SDK Stream Protocols: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
- Vercel AI SDK Streaming Custom Data: https://ai-sdk.dev/docs/ai-sdk-ui/streaming-data
- FastAPI GitHub Discussion #10701 (StreamingResponse all at once): https://github.com/fastapi/fastapi/discussions/10701
- SGLang Issue #11888 (GLM-4.6 tool_calls streaming arguments): https://github.com/sgl-project/sglang/issues/11888
- SGLang Issue #13514 (GLM tool_choice required infinite loop): https://github.com/sgl-project/sglang/issues/13514
- GLM-4.6 model infinite loop issue: https://github.com/anomalyco/opencode/issues/3444
- Vercel AI SDK GitHub Issue #7496 (FastAPI V5 data protocol broken): https://github.com/vercel/ai/issues/7496
- Vercel Community Python AI Response Streaming: https://community.vercel.com/t/python-ai-response-streaming/9218
- Next.js Discussion #48427 (SSE don't work in API routes): https://github.com/vercel/next.js/discussions/48427
- Fixing Slow SSE in Next.js and Vercel: https://medium.com/@oyetoketoby80/fixing-slow-sse-server-sent-events-streaming-in-next-js-and-vercel-99f42fbdb996
- FastAPI CORS docs: https://fastapi.tiangolo.com/tutorial/cors/
- FastAPI SSE docs: https://fastapi.tiangolo.com/tutorial/server-sent-events/
- PowerShell execution policy fix: https://www.stanleyulili.com/powershell/solution-to-running-scripts-is-disabled-on-this-system-error-on-powershell
- Uvicorn Windows venv CommandNotFoundException: https://github.com/fastapi/fastapi/discussions/7842
- py-ai-datastream Python implementation: https://github.com/elementary-data/py-ai-datastream
- Zhipu AI GLM-4.6 tool calling analysis: https://cirra.ai/articles/glm-4-6-tool-calling-mcp-analysis
- Zhipu AI provider for Vercel AI SDK: https://github.com/Xiang-CH/zhipu-ai-provider
