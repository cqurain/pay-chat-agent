# Research Summary: Cyber God of Wealth PoC

**Synthesized:** 2026-04-18
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

---

## Executive Summary

This PoC is a single-turn streaming AI agent chat: the user describes a purchase impulse, the FastAPI backend calls GLM-5 with two mock tools, and the model streams a snarky approve/reject verdict to a Next.js frontend while a savings progress bar updates in real time. The critical technical challenge is the SSE wire format: Vercel AI SDK useChat requires the Vercel Data Stream Protocol (f:, 0:, 2:, e:, d: lines with x-vercel-ai-data-stream: v1 header), not plain SSE. Getting this wrong causes silent failure — the chat bubble stays empty even though bytes arrive in the network tab.

The recommended approach is a two-call agent loop: a non-streaming first call (stream=False) resolves tool calls without delta accumulation boilerplate, then a streaming second call yields the text verdict. This sidesteps the GLM-4.x streaming tool_calls delta fragmentation bug. The stack is minimal: FastAPI + openai 1.x (not 2.x) + Vercel AI SDK 4.x (not 5.x or 6.x). Both version pins are non-negotiable because the newer major versions broke the custom-backend SSE contract.

The biggest risks are: (1) wrong SSE format causing silent frontend failure, (2) tool_choice=required triggering a confirmed GLM infinite loop, and (3) routing the stream through a Next.js proxy route instead of calling FastAPI directly, which hits Vercel 10-second function timeout. All three are avoidable by design decisions made before writing the first line of code.

---

## Stack Recommendation

- **FastAPI >=0.115.0 + uvicorn[standard]** — native StreamingResponse with X-Accel-Buffering: no support; no third-party SSE library needed
- **openai ~=1.102 (Python SDK, NOT 2.x)** — AsyncOpenAI(base_url, api_key) is the confirmed pattern for Zhipu endpoint; 2.x breaks custom base_url support
- **Vercel AI SDK ai@^4 (NOT v5 or v6)** — v4 useChat works against any SSE backend using the data stream protocol; v5+ requires Vercel own backend transport
- **Next.js 16.x + React 19** — App Router stable; Turbopack default; React Compiler eliminates manual memo
- **Tailwind CSS ^4.2** — CSS-first zero config; progress bar animation needs no external library
- **GLM model env var:** use glm-4-flash for dev (free, fast), glm-4-5 or glm-4-plus for production; store as GLM_MODEL in .env, never hard-code

---

## Critical Architecture Points

### SSE Wire Format (Vercel AI SDK Data Stream Protocol)

useChat does NOT parse standard SSE (data: text lines). Every line must follow the data stream protocol:

  f:{"messageId":"<uuid>"}
  0:"token string"
  2:[{"new_savings":4200,"progress_pct":84,"delta":-800}]
  e:{"finishReason":"stop","usage":{"promptTokens":120,"completionTokens":35},"isContinued":false}
  d:{"finishReason":"stop","usage":{"promptTokens":120,"completionTokens":35}}

Required headers: Content-Type: text/event-stream, Cache-Control: no-cache, X-Accel-Buffering: no, x-vercel-ai-data-stream: v1

Token values MUST use json.dumps(delta.content) — never raw string interpolation. A quote in a Chinese token silently corrupts the stream.

The progress bar payload rides the 2: channel (array-wrapped JSON), never the 0: text channel. Frontend reads via onData callback, not onFinish.

### Two-Call Function Calling Loop

  Call 1: stream=False, tools=TOOL_SCHEMAS, tool_choice=auto
    -> finish_reason == tool_calls: extract args, execute tools, append tool messages
  Call 2: stream=True, no tools
    -> yield 0: text chunks -> yield 2: progress payload -> yield e:/d: finish

stream=False on Call 1 eliminates delta accumulation complexity; 100-300ms latency cost is invisible to users.
Never use tool_choice=required — confirmed GLM-4.x bug causes infinite generation.

### Monorepo Structure

  pay-chat-agent/
    cyber-god/
      frontend/   <- Next.js App Router (Vercel)
      backend/    <- FastAPI (Railway/Render)
    .planning/

No Turborepo, no shared packages. useChat api prop points directly at Railway/Render URL — no Next.js proxy route, ever.

### Build Order (Dependency Chain)

Tools -> Agent loop no-stream -> Agent loop stream -> Backend deployed -> Frontend useChat -> Progress bar -> SavingsEditor -> Frontend deployed

Validate the SSE wire format with curl -N before touching the frontend.

---

## Table Stakes Features

| Feature | Why Non-Negotiable |
|---------|-------------------|
| Token-by-token typewriter streaming | Baseline expectation; waiting for full response feels broken |
| Live savings progress bar (animates at stream end) | The core visual payoff — the demo reason for existing |
| Tool-call transparency (zhengzai chaxun jiage...) | Fills the 2-3s tool execution gap; without it the pause feels like a hang |
| Editable savings context (current + target) | Agent needs real numbers; verdict against invisible numbers feels arbitrary |
| Approve/reject verdict styling (red/amber banner) | Decision must be instantly legible; burying verdict in paragraph 2 is anti-UX |
| Input disabled + stop button during stream | Universal expectation; absence signals UI is broken |
| Empty state with example prompt | Reduces first-use friction |
| Error state with retry | Silent failure on network error / LLM timeout is worse than no error |

Explicitly out of scope: chat history DB, message editing, multi-turn tracking, auth, real price APIs, voice, settings panel, feedback UI, mobile polish.

---

## Top Pitfalls to Avoid

| # | Pitfall | One-Line Prevention |
|---|---------|-------------------|
| 1 | Wrong SSE format — useChat silently renders empty messages | Implement Vercel Data Stream Protocol exactly; validate with curl -N before touching the frontend |
| 2 | tool_choice=required triggers confirmed GLM infinite loop | Always use tool_choice=auto; add max_tokens=1024 as a hard safeguard |
| 3 | Structured progress payload sent as 0: text instead of 2: data | Send 2:[{...}] as separate chunk; read with onData callback, not onFinish |
| 4 | FastAPI StreamingResponse buffers entire response | Use async def generator + AsyncOpenAI + await anyio.sleep(0) per chunk; add X-Accel-Buffering: no |
| 5 | Routing stream through a Next.js API proxy route | Point useChat api prop directly at Railway/Render URL; no proxy — Vercel 10s timeout kills it |
| 6 | CORS not configured — browser silently blocks preflight | Add CORSMiddleware with explicit origins from ALLOWED_ORIGINS env var; never wildcard in production |
| 7 | delta.content accessed without null check | Always use delta.content or empty string — GLM-4.6+ reasoning_content field makes content None on some chunks |

---

## Open Questions

Items requiring empirical verification during Phase 1:

1. **GLM model string:** Does glm-4-5 resolve correctly on open.bigmodel.cn as of April 2026? Verify in Zhipu console before writing the agent loop.
2. **tool_stream default on Zhipu cloud API:** Confirm stream=False on Call 1 causes tool args to always arrive complete — MEDIUM confidence only.
3. **x-vercel-ai-data-stream: v1 header:** Verify whether useChat requires this header for the 2: channel to populate useChat.data[].
4. **onData callback API in ai@^4:** Confirm exact callback signature for intercepting 2: data parts — API differs between SDK versions.
5. **System prompt reliability for tool invocation:** Verify GLM-4-flash always calls both get_mock_price and calculate_savings_impact on a purchase impulse, or add fallback handling.

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Stack version pins | MEDIUM | PyPI/npm verified; GLM-specific pins via community bug reports |
| SSE wire format | MEDIUM | Multiple community sources + official Vercel template; ai-sdk.dev unreachable for direct verification |
| GLM function calling behavior | MEDIUM | Confirmed via SGLang/vLLM bug reports; Zhipu cloud API may differ from self-hosted |
| Feature prioritization | HIGH | Universal chat UI patterns confirmed across major products |
| Architecture patterns | HIGH | Two-call loop, StreamingResponse, CORS are stable and well-documented |
| Pitfall severity ratings | MEDIUM-HIGH | SSE format and tool_choice pitfalls backed by official bug reports |

**Overall: MEDIUM-HIGH** — Architecture is sound and version pins are defensible. Two areas needing empirical validation: GLM cloud API behavior specifics (model string, tool_stream default) and exact useChat 4.x onData callback API.
