# Roadmap: Cyber God of Wealth（赛博财神爷）

**Project:** Cyber God of Wealth PoC
**Milestone:** M1 — Working PoC
**Granularity:** Coarse
**Coverage:** 28/28 v1 requirements mapped

---

## Phases

- [ ] **Phase 1: Backend Core** — Demo-able backend: curl a purchase impulse, get a streaming snarky verdict with tool calls and a savings payload
- [ ] **Phase 2: Frontend** — Full in-browser demo: chat UI streams the verdict in real time, progress bar animates, savings context is editable
- [ ] **Phase 3: Deployment** — Ship it: Docker-packaged backend + Vercel-deployed frontend, one-command startup

---

## Phase Details

### Phase 1: Backend Core
**Goal**: You can curl POST /api/chat with a purchase impulse and receive a GLM-5-powered streaming verdict — including tool execution results and a structured savings payload — in the correct Vercel Data Stream Protocol wire format.
**Depends on**: Nothing (first phase)
**Requirements**: TOOL-01, TOOL-02, AGENT-01, AGENT-02, AGENT-03, AGENT-04, AGENT-05, AGENT-06, AGENT-07, PERSONA-01, PERSONA-02
**Success Criteria** (what must be TRUE):
  1. `curl -N -X POST /api/chat` with a purchase JSON body returns a stream of lines beginning with `f:`, `0:`, `2:`, `e:`, `d:` and the response header contains `x-vercel-ai-data-stream: v1`
  2. The `2:` chunk in the stream contains a valid JSON array with `new_savings`, `progress_pct`, and `delta` keys computed from the actual tool calls
  3. The streamed text (0: lines) is in character — 毒舌财神 style, leads with approve or reject, written in Chinese
  4. A preflight OPTIONS request to /api/chat from a different origin returns a 200 with correct CORS headers
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffold + tools foundation (config, requirements, MCP server, savings calc, MCP client wrapper)
- [x] 01-02-PLAN.md — Agent loop + API route (system prompt, two-phase GLM, Vercel SSE, route handler)
- [x] 01-03-PLAN.md — End-to-end validation (install deps, start server, curl Phase 1 gate checkpoint)

**Gate before Phase 2**: GLM model string confirmed working in Zhipu console; SSE wire format validated end-to-end with curl before any frontend code is written.

---

### Phase 2: Frontend
**Goal**: A browser user can type a spending impulse into the chat UI, watch the 财神's verdict stream in token by token, and see the savings progress bar animate to reflect the tool-computed outcome.
**Depends on**: Phase 1 (backend must be running locally or at a known URL before frontend is wired)
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, SAVINGS-01, SAVINGS-02, SAVINGS-03, PROGRESS-01, PROGRESS-02, PROGRESS-03
**Success Criteria** (what must be TRUE):
  1. Typing "我想花 800 买个盲盒" and submitting shows a tool-status indicator ("正在查询价格..." / "正在计算影响...") during tool resolution, then streams the verdict token by token with a typewriter effect
  2. The savings progress bar updates its fill percentage and triggers a red flash animation when the `2:` data chunk arrives (purchase approved but delta is negative)
  3. Editing the 存款目标 or 已存金额 inputs and refreshing the page restores the same values (localStorage persistence); the values are included in every chat request body
  4. During streaming the input is disabled and a stop button is visible; after streaming completes the input re-enables
**Plans**: TBD
**UI hint**: yes

---

### Phase 3: Deployment
**Goal**: Anyone can clone the repo, run `docker compose up -d` for the backend, deploy the frontend to Vercel with one env var, and have a fully working demo accessible from a public URL.
**Depends on**: Phase 2 (full local demo must work before packaging for deployment)
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):
  1. `docker compose up -d` in `cyber-god/backend/` builds and starts the FastAPI container on port 8000, reading `ZHIPU_API_KEY`, `GLM_MODEL`, and `ALLOWED_ORIGINS` from the `.env` file — no other setup required
  2. Setting `NEXT_PUBLIC_API_URL` to the Docker host URL and deploying the frontend to Vercel results in a working public demo (chat streams, progress bar updates, no CORS errors in browser console)
  3. The README covers Windows/PowerShell local dev setup, Docker build + push steps, and Vercel frontend deployment in a single linear walkthrough
**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Backend Core | 0/3 | Not started | - |
| 2. Frontend | 0/? | Not started | - |
| 3. Deployment | 0/? | Not started | - |

---

*Roadmap created: 2026-04-18*
*Last updated: 2026-04-18 — Phase 1 plans created (3 plans, 3 waves)*
