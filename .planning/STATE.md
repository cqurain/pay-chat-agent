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

**Current Phase**: 1 — Backend Core
**Current Plan**: None started
**Status**: Not started

**Progress**:
```
Phase 1 [          ] 0%   Backend Core
Phase 2 [          ] 0%   Frontend
Phase 3 [          ] 0%   Deployment
```

**Overall**: 0/3 phases complete

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases defined | 3 |
| Requirements mapped | 28/28 |
| Plans complete | 0 |
| Phases complete | 0 |

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

---

## Session Continuity

**Last session**: 2026-04-18 — Project initialized, requirements defined, roadmap created
**Next action**: Start Phase 1 — run `/gsd-plan-phase 1`

---

*State initialized: 2026-04-18*
*Last updated: 2026-04-18 after roadmap creation*
