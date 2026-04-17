# Architecture Patterns

**Project:** Cyber God of Wealth (赛博财神爷)
**Domain:** Single-turn streaming AI agent — FastAPI backend + Next.js frontend
**Researched:** 2026-04-18
**Overall confidence:** HIGH (core patterns) / MEDIUM (AI SDK version specifics — rapidly evolving)

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser (Vercel)                                       │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Next.js App Router  (cyber-god/frontend)        │   │
│  │                                                  │   │
│  │  pages/page.tsx                                  │   │
│  │    └─ useChat({ api: NEXT_PUBLIC_API_URL })       │   │
│  │         ├─ messages[]  → typewriter text         │   │
│  │         └─ data[]      → progress bar update     │   │
│  └──────────────────────────┬──────────────────────┘   │
└─────────────────────────────┼───────────────────────────┘
                              │  POST /api/chat
                              │  (SSE, data stream protocol)
                              │
┌─────────────────────────────┼───────────────────────────┐
│  Railway / Render           ▼                           │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  FastAPI  (cyber-god/backend)                     │  │
│  │                                                   │  │
│  │  POST /api/chat                                   │  │
│  │    1. Parse messages from useChat                 │  │
│  │    2. Call GLM-5 with tools (stream=False)        │  │
│  │    3. If tool_calls → execute tools               │  │
│  │    4. Call GLM-5 again (stream=True)              │  │
│  │    5. Yield text chunks as SSE 0: format          │  │
│  │    6. Yield final JSON as SSE 2: format           │  │
│  │    7. Yield finish chunk                          │  │
│  │                                                   │  │
│  │  Tools (pure Python):                             │  │
│  │    get_mock_price(item_name)                      │  │
│  │    calculate_savings_impact(price, savings,       │  │
│  │                             target)               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `frontend/app/page.tsx` | Chat UI, progress bar, localStorage state | Backend via `useChat` POST |
| `frontend/components/ProgressBar.tsx` | Renders savings progress from stream data | Receives props from page |
| `frontend/components/SavingsEditor.tsx` | User-editable target + current savings | Writes to localStorage |
| `backend/main.py` | FastAPI app, CORS, registers router | — |
| `backend/routers/chat.py` | POST /api/chat — owns the agent loop | GLM-5 API, tools |
| `backend/tools/mock_price.py` | get_mock_price — pure function, ±30% random | Called by chat router |
| `backend/tools/savings_calc.py` | calculate_savings_impact — pure function | Called by chat router |
| `backend/prompts.py` | 毒舌财神 system prompt string | Imported by chat router |

No shared types package needed — project scope is too small.

---

## Data Flow: Streaming Pipeline

### Full Request Lifecycle

```
1. User submits form
   → useChat.handleSubmit fires
   → POST /api/chat  { messages: [...] }

2. FastAPI receives request
   → Parse body with Pydantic model
   → Build messages array with system prompt prepended

3. First LLM call (tool resolution)
   → openai.chat.completions.create(
       model="glm-4-5",
       messages=messages,
       tools=[get_mock_price_schema, calculate_savings_impact_schema],
       stream=False          # tool calls need complete JSON args
     )

4. Check finish_reason
   IF finish_reason == "tool_calls":
     → Extract tool_calls list
     → Execute each tool (synchronous, trivial latency)
     → Append assistant message with tool_calls
     → Append tool result messages (role="tool")

5. Second LLM call (final streamed verdict)
   → openai.chat.completions.create(
       model="glm-4-5",
       messages=messages + tool_results,
       stream=True
     )

6. FastAPI StreamingResponse yields SSE chunks
   → For each delta chunk: yield text token
   → After stream exhausted: yield structured payload
   → Yield finish marker

7. useChat receives SSE
   → text tokens → messages[n].content builds up (typewriter)
   → data chunks → useChat.data[] array updated
   → page reads data[last] for progress bar update
```

### Why First Call Uses stream=False

When `stream=True` and the model decides to call tools, the function arguments arrive as JSON fragments across many delta chunks and must be accumulated before you can parse and call the tool. For a two-tool single-turn PoC this adds code complexity for zero UX benefit. Use `stream=False` for the tool-resolution call, `stream=True` only for the final text response.

---

## SSE Wire Format (Vercel AI SDK Data Stream Protocol)

**Confidence:** MEDIUM — verified across multiple community sources and the official template. SDK v4/v5/v6 all use the same underlying wire format. SDK v6 is current as of April 2026.

### Required Response Headers

```
Content-Type: text/event-stream
Cache-Control: no-cache
x-vercel-ai-data-stream: v1
```

The `x-vercel-ai-data-stream: v1` header is what tells `useChat` to parse this as a data stream rather than a plain text stream.

### Chunk Format

Every chunk is one line: `{type_code}:{json_value}\n`

| Code | Name | Payload | Purpose |
|------|------|---------|---------|
| `f:` | message-start | `{"messageId":"<uuid>"}` | Opens the message. Send once at the top. |
| `0:` | text-delta | `"token string"` | A streamed text token. Repeat for every token. |
| `2:` | data | `[{...}]` | Custom JSON array. Lands in `useChat.data[]`. |
| `e:` | step-finish | `{"finishReason":"stop","usage":{"promptTokens":N,"completionTokens":M},"isContinued":false}` | Marks end of one LLM step. Required for multi-step. |
| `d:` | stream-finish | `{"finishReason":"stop","usage":{"promptTokens":N,"completionTokens":M}}` | Closes the stream. Send once at the end. |

### Minimal Complete Stream Example

```
f:{"messageId":"msg-001"}\n
0:"批准！"\n
0:"你的"\n
0:"存款"\n
0:"还够"\n
0:"花。"\n
2:[{"new_savings":4200,"progress":84,"delta":-800,"approved":true}]\n
e:{"finishReason":"stop","usage":{"promptTokens":120,"completionTokens":35},"isContinued":false}\n
d:{"finishReason":"stop","usage":{"promptTokens":120,"completionTokens":35}}\n
```

### FastAPI Implementation Skeleton

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import json, uuid

async def generate_stream(messages, tool_results):
    msg_id = str(uuid.uuid4())
    prompt_tokens = 0
    completion_tokens = 0

    # Open message
    yield f'f:{json.dumps({"messageId": msg_id})}\n'

    # Stream final LLM response
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=True
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            # Escape the string as JSON value (handles quotes, newlines)
            yield f'0:{json.dumps(delta.content)}\n'
        if chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens

    # Send structured payload for progress bar
    # tool_results contains the output of calculate_savings_impact
    payload = extract_progress_payload(tool_results)
    yield f'2:{json.dumps([payload])}\n'

    # Finish
    usage = {"promptTokens": prompt_tokens, "completionTokens": completion_tokens}
    yield f'e:{json.dumps({"finishReason": "stop", "usage": usage, "isContinued": False})}\n'
    yield f'd:{json.dumps({"finishReason": "stop", "usage": usage})}\n'


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    # ... agent loop (see below) ...
    return StreamingResponse(
        generate_stream(messages, tool_results),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "x-vercel-ai-data-stream": "v1",
        }
    )
```

**Critical detail:** `json.dumps(delta.content)` — always pass the token through `json.dumps`, not raw string interpolation. A token containing a quote character like `"好的"` would break the protocol if not escaped. Do not write `f'0:"{delta.content}"\n'`.

### Frontend: Reading the Data Chunks

```typescript
// app/page.tsx
import { useChat } from "ai/react";

const { messages, data, handleSubmit, input, setInput } = useChat({
  api: process.env.NEXT_PUBLIC_API_URL + "/api/chat",
});

// data[] accumulates all 2: chunks. The last item is the latest result.
const latestResult = data && data.length > 0
  ? data[data.length - 1] as ProgressPayload
  : null;
```

---

## Function Calling Loop (Annotated)

```python
# backend/routers/chat.py

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_mock_price",
            "description": "Returns a mock price for an item with ±30% randomization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Name of the item"}
                },
                "required": ["item_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_savings_impact",
            "description": "Calculates new savings, progress %, delta, and comment hint after a purchase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "price":          {"type": "number"},
                    "current_savings": {"type": "number"},
                    "savings_target": {"type": "number"}
                },
                "required": ["price", "current_savings", "savings_target"]
            }
        }
    }
]

async def run_agent(messages: list[dict]) -> tuple[list[dict], dict]:
    """
    Returns (updated_messages, tool_results_dict).
    tool_results_dict contains the output of calculate_savings_impact
    for use in the progress bar payload.
    """

    # Step 1: Tool resolution call (no streaming)
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
        stream=False
    )

    choice = response.choices[0]
    tool_results = {}

    if choice.finish_reason == "tool_calls":
        # Append the assistant's tool-call message
        messages.append(choice.message.model_dump())

        # Execute each tool
        for tc in choice.message.tool_calls:
            args = json.loads(tc.function.arguments)
            if tc.function.name == "get_mock_price":
                result = get_mock_price(**args)
            elif tc.function.name == "calculate_savings_impact":
                result = calculate_savings_impact(**args)
                tool_results = result        # capture for progress bar
            else:
                result = {"error": "unknown tool"}

            # Append tool result message
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result)
            })

    # messages is now ready for the final streaming call
    return messages, tool_results
```

**Why `tool_choice="auto"`:** GLM-5 with the OpenAI-compatible endpoint respects `tool_choice`. Setting it to `"auto"` lets the model decide whether to call tools. The model will always call both tools for this use case because both are needed to produce a data-backed verdict.

**GLM-5 compatibility note:** GLM-4/GLM-5 on Zhipu AI's OpenAI-compatible endpoint (`https://open.bigmodel.cn/api/paas/v4/`) supports `tool_calls` with the standard OpenAI format. The `openai` Python SDK works without modification — just set `base_url` and `api_key`. Confidence: MEDIUM (verified via community sources and Zhipu documentation; test on first phase).

---

## CORS Configuration

```python
# backend/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Load allowed origins from env; falls back to localhost for dev
_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,    # never "*" in production
    allow_credentials=False,           # no cookies needed
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
```

### Environment Variables by Environment

| Env | `ALLOWED_ORIGINS` value |
|-----|------------------------|
| Local dev | `http://localhost:3000` (default) |
| Railway/Render staging | `https://your-preview.vercel.app` |
| Production | `https://cyber-god.vercel.app` (your actual domain) |

Set `ALLOWED_ORIGINS` in Railway/Render's environment variables UI. On Vercel, set `NEXT_PUBLIC_API_URL=https://your-backend.railway.app` as an environment variable for the frontend build.

**Why not `"*"`:** The `2:` data chunks carry savings figures. While there's no auth in this PoC, it is bad practice to allow any origin to call your agent backend with arbitrary tool invocations. Enumerate your Vercel domain.

---

## Monorepo Structure

```
pay-chat-agent/                     ← git root
├── cyber-god/
│   ├── frontend/                   ← Next.js App Router
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            ← main chat + progress bar UI
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── ChatInput.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── SavingsEditor.tsx
│   │   ├── lib/
│   │   │   └── storage.ts          ← localStorage helpers
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   └── tsconfig.json
│   │
│   └── backend/                    ← FastAPI
│       ├── main.py                 ← app init, CORS, router mount
│       ├── routers/
│       │   └── chat.py             ← POST /api/chat, agent loop
│       ├── tools/
│       │   ├── mock_price.py       ← get_mock_price()
│       │   └── savings_calc.py     ← calculate_savings_impact()
│       ├── prompts.py              ← 毒舌财神 system prompt
│       ├── requirements.txt
│       └── .env.example
│
├── .planning/
│   ├── PROJECT.md
│   └── research/
└── .gitignore
```

**No Turborepo or workspace tooling.** This is a PoC with two independent apps that share no code. Running them is two separate commands (`npm run dev` and `uvicorn main:app`). Turborepo would add config overhead with zero benefit here.

**No shared types package.** The only cross-boundary contract is the JSON payload in the `2:` SSE chunk. Define it as a TypeScript interface inline in `page.tsx` and as a Pydantic model in `savings_calc.py`. If the schema changes, update both by hand — it's one object.

### Local Dev Commands

```bash
# Terminal 1 — backend
cd cyber-god/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd cyber-god/frontend
npm install
npm run dev          # starts on :3000
```

### Vercel Deployment Configuration

In `cyber-god/frontend/vercel.json` (or Vercel project settings), set the root directory to `cyber-god/frontend`. This is the only configuration needed — Vercel auto-detects Next.js.

In Railway/Render, set the root directory to `cyber-god/backend`, start command `uvicorn main:app --host 0.0.0.0 --port $PORT`.

---

## Suggested Build Order

Build in this order to unlock each layer before the next:

| Phase | What to Build | Why First |
|-------|--------------|-----------|
| 1 | Backend: tool functions + unit tests | Pure Python, no network, instantly testable |
| 2 | Backend: agent loop (stream=False, no streaming yet) | Validate GLM-5 tool calling works end-to-end before adding streaming complexity |
| 3 | Backend: StreamingResponse + SSE format | Add streaming once you know the tools work |
| 4 | Backend: CORS + deploy to Railway/Render | Get a stable URL before touching frontend |
| 5 | Frontend: useChat hook connected to live backend | Build against real streaming, not mocks |
| 6 | Frontend: progress bar wired to data[] stream | `2:` chunks visible once useChat is working |
| 7 | Frontend: SavingsEditor + localStorage | Pure UI, no blockers |
| 8 | Frontend: deploy to Vercel | Last step, everything else confirmed working |

**Critical dependency chain:** Tools → Agent loop (no stream) → Agent loop (stream) → Backend deployed → Frontend useChat → Frontend progress bar.

Do not build frontend and backend in parallel. The SSE wire format must be confirmed working in isolation (curl/httpie) before hooking up useChat.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: String-Interpolating Tokens into SSE Chunks
**What:** `yield f'0:"{delta.content}"\n'`
**Why bad:** Any token containing `"`, `\n`, or `\` corrupts the JSON and causes `useChat` to silently drop the message.
**Instead:** Always `yield f'0:{json.dumps(delta.content)}\n'`

### Anti-Pattern 2: Streaming the Tool-Resolution Call
**What:** Setting `stream=True` on the first LLM call (the one that produces `tool_calls`).
**Why bad:** Tool call arguments arrive fragmented across delta chunks and must be accumulated with index-tracking boilerplate before you can call the tool.
**Instead:** `stream=False` for the tool-resolution call. The latency is negligible (100-300ms extra) for two fast mock tools.

### Anti-Pattern 3: Sending the Structured Payload as Part of the Text Stream
**What:** Appending `\n\n---JSON---\n{...}` to the LLM's text output, then parsing it on the frontend.
**Why bad:** The LLM might re-format it; hallucinate extra text after it; or the text parser on the frontend becomes fragile.
**Instead:** Use the `2:` data chunk. It is a separate channel, never mixed with `messages[n].content`, and lands cleanly in `useChat.data[]`.

### Anti-Pattern 4: Wildcard CORS in Production
**What:** `allow_origins=["*"]`
**Why bad:** Any web page can POST to your backend and trigger LLM calls under your API key.
**Instead:** Enumerate exact Vercel domains via environment variable.

### Anti-Pattern 5: Using Turborepo/pnpm Workspaces for a PoC
**What:** Adding a workspace config file, shared `tsconfig`, etc.
**Why bad:** Python and Node do not share a package manager. Turborepo adds a complex layer that brings zero benefit when there is nothing to share.
**Instead:** Two independent folders, two independent dev commands.

---

## Scalability Considerations (PoC Scope)

This architecture is intentionally local-state-only. The PoC is not designed to scale.

| Concern | PoC approach | If scaling later |
|---------|-------------|-----------------|
| User state | localStorage | JWT + DB |
| Concurrent requests | Uvicorn async, fine for demo | Worker pool + async client |
| API key exposure | Backend env var | Secret manager |
| Rate limiting | None | Token bucket in middleware |

---

## Sources

- [Vercel AI SDK — Stream Protocols (ai-sdk.dev)](https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol) — MEDIUM confidence (domain unreachable from this environment; content verified via search result snippets)
- [Vercel AI SDK — Streaming Custom Data (ai-sdk.dev)](https://ai-sdk.dev/docs/ai-sdk-ui/streaming-data) — MEDIUM confidence
- [GitHub: elementary-data/py-ai-datastream](https://github.com/elementary-data/py-ai-datastream) — Python reference implementation of the data stream protocol
- [GitHub: vercel-labs/ai-sdk-preview-python-streaming](https://github.com/vercel-labs/ai-sdk-preview-python-streaming) — Official Vercel FastAPI example
- [FastAPI CORS Middleware (fastapi.tiangolo.com)](https://fastapi.tiangolo.com/tutorial/cors/) — HIGH confidence
- [Handling JSON Data in Data Stream responses with FastAPI · vercel/ai Discussion #2840](https://github.com/vercel/ai/discussions/2840) — MEDIUM confidence
- [GLM-5 API Guide — Apiyi.com](https://help.apiyi.com/en/glm-5-api-guide-744b-moe-agent-tutorial-en.html) — MEDIUM confidence (GLM-5 OpenAI compatibility)
- [Building a Python-Native Backend for AI Chat Streaming — Elementary Data](https://www.elementary-data.com/post/building-a-python-native-backend-for-ai-chat-streaming) — MEDIUM confidence (unreachable; verified via search snippet)
- [AI SDK 6 release (vercel.com/blog/ai-sdk-6)](https://vercel.com/blog/ai-sdk-6) — confirms v6 is current as of April 2026
