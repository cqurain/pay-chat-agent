<!-- GSD:project-start source:PROJECT.md -->
## Project

**Cyber God of Wealth（赛博财神爷）**

A PoC AI finance companion Agent with a "毒舌财神" (snarky wealth god) persona. Users input a spending impulse (e.g., "我想花 800 买个盲盒"), and the Agent queries mock price data, calculates impact on their savings goal, then delivers a streaming verdict — approve or reject — while updating a live savings progress bar in the frontend.

**Core Value:** The Agent must make a data-backed decision (approve or reject the purchase) and stream it in character, with the progress bar updating in real time. Everything else is secondary.

### Constraints

- **Tech stack**: FastAPI + Pydantic + Next.js App Router + Tailwind CSS + Vercel AI SDK — no deviations
- **Function calling**: must use OpenAI-compatible tool_calls pattern (works with GLM-5)
- **Streaming**: backend must use FastAPI StreamingResponse; frontend must use useChat
- **No DB**: all state in React state + localStorage
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
# fastapi[standard] pulls in uvicorn[standard], httpx, email-validator, pydantic
### Python-level streaming pattern
# REQUIRED: CORS for Next.js dev server (localhost:3000) and Vercel domain
# GLM-5 client — identical to openai.AsyncOpenAI, just different base_url + api_key
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
### useChat wiring to FastAPI backend
### Progress bar (Tailwind v4, no extra library)
## GLM-5 Specifics
### Model name and endpoint
| Model string | Notes |
|---|---|
| `glm-4-5` | Stated in PROJECT.md — verify with Zhipu console that this is the exact string |
| `glm-4-flash` | Free-tier fast model; supports function calling |
| `glm-4` | Full capability model |
| `glm-4-plus` | Most capable in GLM-4 line |
| `glm-5` | 744B MoE flagship, released Feb 2026 |
### OpenAI client configuration
### Tool call format (identical to OpenAI)
### Known GLM-4.x streaming tool_calls gotchas (MEDIUM confidence — from community bug reports)
### Two-phase streaming strategy for this project
## What NOT to use
### Do NOT use: openai Python SDK 2.x
### Do NOT use: Vercel AI SDK v5 or v6 (`ai@^5` or `ai@^6`)
### Do NOT use: LangChain or LangGraph
### Do NOT use: WebSockets
### Do NOT use: Pydantic v3
### Do NOT use: Redis or any database
### Do NOT use: sse-starlette (the third-party library)
## Environment Variables
# backend/.env
# frontend/.env.local
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
