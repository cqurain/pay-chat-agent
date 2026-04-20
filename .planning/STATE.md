---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: complete
last_updated: "2026-04-19T00:00:00.000Z"
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 8
  completed_plans: 8
  percent: 100
---

# Project State: Cyber God of Wealth（赛博财神爷）

*This file is the single source of truth for project position. Update at every phase transition and plan completion.*

---

## Project Reference

**Core Value**: The Agent must call tools, make a data-backed approve/reject decision, and stream it in character — with the progress bar updating in real time.

**Current Focus**: Phase 1 — Backend Core

**Repo root**: `e:\cs\towk\pay-chat-agent`
**Monorepo layout**: `cyber-god/frontend` + `cyber-god/backend`

---

## Current Position

Phase: 03 (deployment) — COMPLETE
Plan: 2 of 2
**Current Phase**: 3 — Deployment
**Status**: All phases complete

**Progress**:

```
Phase 1 [██████████] 100%  Backend Core
Phase 2 [██████████] 100%  Frontend
Phase 3 [██████████] 100%  Deployment
```

**Overall**: 3/3 phases complete

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases defined | 3 |
| Requirements mapped | 28/28 |
| Plans complete | 8 |
| Phases complete | 3 |

---

## Accumulated Context

### Key Decisions Locked In

| Decision | Outcome |
|----------|---------|
| SSE wire format | Vercel Data Stream Protocol only (f:, 0:, 2:, e:, d: lines + x-vercel-ai-data-stream: v1 header) |
| Agent loop pattern | Two calls: stream=False for tool resolution, stream=True for verdict generation |
| tool_choice | Always `auto` — `required` triggers confirmed GLM infinite loop bug |
| Frontend routing | useChat api prop points directly at backend URL — NO Next.js proxy route |
| Backend deployment | Docker (Dockerfile + docker-compose.yml) on any Linux server — NOT Railway/Render PaaS |
| openai SDK | Pin to ~=1.x — 2.x breaks custom base_url for Zhipu endpoint |
| Vercel AI SDK | Pin to ai@^4 — v5/v6 dropped plain-SSE backend support |
| GLM_MODEL env var | glm-4-flash for dev (free/fast), glm-4-5 for prod; never hard-coded |
| Progress bar payload | Rides 2: channel (array-wrapped JSON); read via onData callback, not onFinish |

### Phase 1 Gate (must be TRUE before Phase 2 starts)

- [ ] GLM model string confirmed working in Zhipu console
- [ ] SSE wire format validated end-to-end with `curl -N`

### Open Questions (from research)

1. Does `glm-4-5` resolve correctly on open.bigmodel.cn as of April 2026?
2. Does `stream=False` on Call 1 always deliver complete tool args on Zhipu cloud?
3. Does useChat require `x-vercel-ai-data-stream: v1` header for the `2:` channel to populate `useChat.data[]`?
4. Exact `onData` callback signature in ai@^4 for intercepting `2:` data parts?
5. Does GLM-4-flash reliably call both tools on a purchase impulse, or does it need fallback handling?

### Pitfalls to Watch

1. Wrong SSE format causes silent empty chat bubble — validate with curl before touching frontend
2. `delta.content` can be `None` on some GLM-4.6+ chunks (reasoning_content field) — always use `delta.content or ""`
3. FastAPI may buffer StreamingResponse — use `async def` generator + `await anyio.sleep(0)` per chunk + `X-Accel-Buffering: no`
4. CORS wildcard is fine for dev; must use explicit `ALLOWED_ORIGINS` env var in production Docker deployment

### Todos

- (none yet — project just initialized)

### Blockers

- (none)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260419-nlk | 实现全部5项改动：LLM意图提取、知识截止修复、价格渠道来源、人设切换、Tavily优先 | 2026-04-19 | db88194 | [260419-nlk-5-llm-tavily](.planning/quick/260419-nlk-5-llm-tavily/) |
| 260419-sw7 | 重构 loop.py 和 server.py：按职责拆函数，LLM 价格提取替换正则 | 2026-04-19 | 9a631a4 | [260419-sw7-loop-py-server-py-loop-py-resolve-price-](.planning/quick/260419-sw7-loop-py-server-py-loop-py-resolve-price-/) |
| 260420-v98 | Refactor cyber-god backend agent to ReAct-lite with real GLM-5 function calling | 2026-04-20 | 436aa3e | [260420-v98-refactor-cyber-god-backend-agent-to-reac](.planning/quick/260420-v98-refactor-cyber-god-backend-agent-to-reac/) |

---

## Session Continuity

**Last session**: 2026-04-20 — Quick task 260420-v98 complete: ReAct-lite refactor — real GLM-5 function calling, multi-item support, robustness fixes
**Next action**: v1.0 milestone complete — run `/gsd-complete-milestone` to archive

---

*State initialized: 2026-04-18*
*Last updated: 2026-04-19 — Quick task 260419-nlk: 5 agent improvements*
