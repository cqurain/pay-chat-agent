---
phase: 01-backend-core
plan: 02
subsystem: agent-loop
tags: [fastapi, glm, streaming, vercel-protocol, sse, agent-loop, persona]
dependency_graph:
  requires:
    - cyber-god/backend/tools/savings.py
    - cyber-god/backend/tools/price.py
    - cyber-god/backend/config.py
    - cyber-god/backend/main.py
  provides:
    - cyber-god/backend/agent/prompt.py
    - cyber-god/backend/agent/loop.py
    - cyber-god/backend/api/routes.py
    - cyber-god/backend/main.py (updated)
  affects:
    - Plan 03 (frontend useChat depends on /api/chat SSE wire format)
tech_stack:
  added: []
  patterns:
    - Two-phase GLM calling: stream=False for tool resolution, stream=True for verdict streaming
    - Vercel Data Stream Protocol: f:/0:/2:/e:/d: lines with x-vercel-ai-data-stream:v1 header
    - Async generator as FastAPI StreamingResponse source with safe_stream() exception wrapper
    - Per-request AsyncOpenAI client (simplest for PoC, no shared state issues)
key_files:
  created:
    - cyber-god/backend/agent/prompt.py
    - cyber-god/backend/agent/loop.py
    - cyber-god/backend/api/routes.py
  modified:
    - cyber-god/backend/main.py
decisions:
  - "D-07 simplified: GLM errors caught in safe_stream() and emitted as 200+SSE rather than HTTP 500 (async generator cannot raise before first yield)"
  - "tool_choice=auto on Phase 2 call to avoid GLM infinite loop bug (not tool_choice=none)"
  - "Per-request AsyncOpenAI client creation — simplest for PoC, avoids any shared client state"
  - "assistant_msg content kept as None when GLM makes tool calls — valid in OpenAI API spec"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-18"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
---

# Phase 01 Plan 02: Agent Loop and Chat Route Summary

**One-liner:** Two-phase GLM agent loop with 毒舌财神 persona, tool execution, retry/fallback, and POST /api/chat StreamingResponse emitting Vercel Data Stream Protocol SSE.

## What Was Built

### agent/prompt.py

`SYSTEM_PROMPT` constant (413 characters) establishing the 毒舌财神 persona:
- Instructs mandatory two-tool workflow: `search_products` then `calculate_savings_impact`
- Requires verdict leading with 【批准】 or 【驳回】 on line 1
- Internet-roast style: `u1s1`, `真的假的`, `富婆`, deadpan disbelief, short punchy sentences
- 100-200 character response, all Chinese

### agent/loop.py

`run_agent_loop` async generator with full business logic:

| Phase | GLM call | stream | Purpose |
|-------|----------|--------|---------|
| 1 | `completions.create(stream=False)` | No | Resolve tool calls without GLM-4.6+ streaming parse bug |
| 2 | `completions.create(stream=True)` | Yes | Stream Chinese verdict text as 0: chunks |

**Retry logic (D-05):** If Phase 1 returns no tool_calls, reinject a system message in Chinese demanding tool usage and retry once.

**Fallback (D-06):** If retry also returns no tool_calls, yield in-character error message (`财神出岁了！天机不可泄露，稍后再来。`) with `finishReason: error` then return.

**Savings payload (D-13):** After Phase 2 streaming completes, compute `calculate_savings_impact` one final time with the `resolved_price` from `search_products` and yield:
```
2:[{"new_savings": float, "progress_pct": float, "delta": float}]
```

**Vercel SSE protocol emitted (D-11):**
```
f:{"id": "<uuid>"}
0:"<text chunk>"   (repeated)
2:[{"new_savings":..., "progress_pct":..., "delta":...}]
e:{"finishReason":"stop","usage":{...},"isContinued":false}
d:{"finishReason":"stop","usage":{...},"isContinued":false}
```

**GLM-4.6+ gotcha guarded:** `delta.content or ""` — prevents NoneType error on reasoning_content chunks.

### api/routes.py

`POST /api/chat` endpoint:
- `ChatRequest` Pydantic model: `messages: list[Message]`, `savings: float = 0.0`, `target: float = 10000.0`
- Validates input types (non-numeric savings/target rejected with 422)
- Creates `AsyncOpenAI(base_url="https://open.bigmodel.cn/api/paas/v4", api_key=ZHIPU_API_KEY)` per request
- Returns `StreamingResponse(safe_stream(), media_type="text/event-stream", headers={...})`
- `safe_stream()` wrapper catches mid-stream exceptions and emits in-character SSE error

Response headers:
```
x-vercel-ai-data-stream: v1
X-Accel-Buffering: no
Cache-Control: no-cache
Connection: keep-alive
```

### main.py (updated)

Added at end of file:
```python
from api.routes import router
app.include_router(router, prefix="/api")
```

Route `/api/chat` is now registered and reachable at `localhost:8000/api/chat`.

## Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | System prompt + agent loop | c438c5e | agent/prompt.py, agent/loop.py |
| 2 | Chat route + router registration | 451636f | api/routes.py, main.py |

## Verification Results

1. `from agent.prompt import SYSTEM_PROMPT; assert len(SYSTEM_PROMPT) > 200` — PASS (413 chars)
2. `from agent.loop import run_agent_loop, TOOLS_SCHEMA; assert len(TOOLS_SCHEMA) == 2` — PASS
3. `from main import app; assert '/api/chat' in [r.path for r in app.routes]` — PASS
4. Grep checks:
   - `grep "stream=False" agent/loop.py` — PASS
   - `grep "stream=True" agent/loop.py` — PASS
   - `grep 'tool_choice.*auto' agent/loop.py` — PASS (3 matches, never "required")
   - `grep "x-vercel-ai-data-stream" api/routes.py` — PASS
   - `grep "X-Accel-Buffering" api/routes.py` — PASS

## Deviations from Plan

### Accepted Simplification

**1. [D-07 simplified] GLM hard failure returns 200+SSE error instead of HTTP 500**
- **Found during:** Task 2 implementation
- **Issue:** Python async generators do not execute until iterated — `gen = run_agent_loop(...)` does not invoke any GLM calls. The `try/except` around that line catches nothing. GLM network/auth exceptions first surface during `async for line in gen` inside `safe_stream()`, at which point the StreamingResponse headers are already sent (HTTP 200).
- **Fix:** `safe_stream()` catches exceptions mid-stream and emits `0:` error text + `e:` + `d:` close lines, keeping the SSE stream well-formed for the client.
- **Deviation from D-07:** HTTP status is 200 with in-character error text, not 500 with JSON error body. The plan explicitly notes this as "acceptable" for PoC.
- **Impact:** Frontend receives a graceful SSE error; the chat bubble shows the in-character error message. No broken stream or silent failure.
- **Files modified:** `api/routes.py`

## Known Stubs

None — all modules implement full planned functionality. The `/api/chat` endpoint is curl-testable end-to-end (requires a valid `ZHIPU_API_KEY` in `.env`).

## Threat Flags

None — all security mitigations from the threat model are implemented:
- T-02-01: Pydantic `ChatRequest` validates types; non-numeric `savings`/`target` → 422
- T-02-02: `safe_stream()` catches exceptions without exposing stack traces; only in-character message emitted
- T-02-06: `ZHIPU_API_KEY` loaded from `config.py` (env var only), never logged or returned

## Self-Check: PASSED

Files exist:
- FOUND: cyber-god/backend/agent/prompt.py
- FOUND: cyber-god/backend/agent/loop.py
- FOUND: cyber-god/backend/api/routes.py
- FOUND: cyber-god/backend/main.py (updated)

Commits exist:
- FOUND: c438c5e (Task 1 — agent prompt + loop)
- FOUND: 451636f (Task 2 — chat route + main.py)
