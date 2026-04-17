# Requirements: Cyber God of Wealth（赛博财神爷）

**Defined:** 2026-04-18
**Core Value:** The Agent must call tools, make a data-backed approve/reject decision, and stream it in character — with the progress bar updating in real time.

## v1 Requirements

### Backend — Tools

- [ ] **TOOL-01**: `get_mock_price(item_name: str) -> float` returns a ±30% randomized price around a base value
- [ ] **TOOL-02**: `calculate_savings_impact(price, savings, target) -> dict` returns `{new_savings, progress, delta, comment_hint}`

### Backend — Agent Loop

- [ ] **AGENT-01**: POST /api/chat accepts `{messages, savings, target}` JSON body
- [ ] **AGENT-02**: Backend calls GLM-5 with `stream=False` on first call (tool resolution) using `tool_choice="auto"`
- [ ] **AGENT-03**: Backend executes tool calls, appends `role="tool"` results to message history
- [ ] **AGENT-04**: Backend calls GLM-5 with `stream=True` on second call (text verdict generation)
- [ ] **AGENT-05**: Backend returns FastAPI `StreamingResponse` with Vercel Data Stream Protocol format (`f:`, `0:`, `2:`, `e:`, `d:` lines) and required headers (`x-vercel-ai-data-stream: v1`, `X-Accel-Buffering: no`)
- [ ] **AGENT-06**: Structured savings payload `{new_savings, progress_pct, delta}` sent as `2:` data chunk (not in text stream)
- [ ] **AGENT-07**: CORS configured via `CORSMiddleware` with `ALLOWED_ORIGINS` env var

### Backend — Persona

- [ ] **PERSONA-01**: System prompt hardcodes 毒舌财神 persona — data-driven, 劝退-first, sarcastic but not attacking, always leads with approve/reject verdict
- [ ] **PERSONA-02**: System prompt instructs LLM to always call both tools before replying

### Frontend — Chat UI

- [ ] **CHAT-01**: Chat UI uses Vercel AI SDK `useChat` pointing directly at Docker backend URL (no Next.js proxy)
- [ ] **CHAT-02**: Messages render with typewriter streaming effect (token by token)
- [ ] **CHAT-03**: Input disabled and stop button shown during streaming
- [ ] **CHAT-04**: Tool-call transparency: show "正在查询价格..." / "正在计算影响..." status during tool resolution phase
- [ ] **CHAT-05**: Approve/reject verdict visually distinguished (e.g., green/red banner or border on message bubble)
- [ ] **CHAT-06**: Empty state with example prompt ("试试：我想花 800 买个盲盒")
- [ ] **CHAT-07**: Error state with retry option

### Frontend — Savings Context

- [ ] **SAVINGS-01**: User can input and edit savings target (存款目标) and current savings (已存金额)
- [ ] **SAVINGS-02**: Savings context persisted in `localStorage` (keys: `target`, `savings`)
- [ ] **SAVINGS-03**: Savings context sent with every chat request so Agent has real numbers

### Frontend — Progress Bar

- [ ] **PROGRESS-01**: Progress bar shows current savings / target as a percentage
- [ ] **PROGRESS-02**: Progress bar animates/updates when Agent response contains `2:` savings payload
- [ ] **PROGRESS-03**: Progress bar flashes red if new savings would decrease (purchase approved but delta negative)

### Deployment

- [ ] **DEPLOY-01**: Frontend deployable to Vercel with `NEXT_PUBLIC_API_URL` env var pointing at backend
- [ ] **DEPLOY-02**: Backend packaged as Docker image (`Dockerfile` + `docker-compose.yml`) deployable to any remote Linux server via `docker compose up -d`
- [ ] **DEPLOY-03**: Docker image exposes port 8000, reads `ZHIPU_API_KEY`, `GLM_MODEL`, `ALLOWED_ORIGINS` from env / `.env` file
- [ ] **DEPLOY-04**: README documents local dev setup (Windows/PowerShell), Docker build + push steps, and Vercel frontend deployment

## v2 Requirements

### Future Enhancements

- **V2-01**: Multi-turn conversation memory (track purchase history across messages)
- **V2-02**: Real price lookup API (Taobao / JD scraping)
- **V2-03**: Auth / user accounts to persist savings goal server-side
- **V2-04**: Notification: "你还差 X 元就到目标了！"
- **V2-05**: Mobile-responsive layout polish

## Out of Scope

| Feature | Reason |
|---------|--------|
| MCP / LangGraph | PoC scope — single LLM loop only |
| Database (MySQL / Redis) | localStorage sufficient for PoC |
| OAuth / user accounts | No auth for PoC |
| Real price APIs | Mock data sufficient for demo |
| Multi-agent | Complexity not justified for PoC |
| Next.js API proxy route | Vercel 10s timeout kills streaming |
| tool_choice=required | Confirmed GLM infinite loop bug |
| Vercel AI SDK v5/v6 | Dropped plain-SSE backend support |
| openai Python SDK v2.x | Breaks custom base_url (Zhipu endpoint) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TOOL-01 | Phase 1 | Pending |
| TOOL-02 | Phase 1 | Pending |
| AGENT-01 | Phase 1 | Pending |
| AGENT-02 | Phase 1 | Pending |
| AGENT-03 | Phase 1 | Pending |
| AGENT-04 | Phase 1 | Pending |
| AGENT-05 | Phase 1 | Pending |
| AGENT-06 | Phase 1 | Pending |
| AGENT-07 | Phase 1 | Pending |
| PERSONA-01 | Phase 1 | Pending |
| PERSONA-02 | Phase 1 | Pending |
| CHAT-01 | Phase 2 | Pending |
| CHAT-02 | Phase 2 | Pending |
| CHAT-03 | Phase 2 | Pending |
| CHAT-04 | Phase 2 | Pending |
| CHAT-05 | Phase 2 | Pending |
| CHAT-06 | Phase 2 | Pending |
| CHAT-07 | Phase 2 | Pending |
| SAVINGS-01 | Phase 2 | Pending |
| SAVINGS-02 | Phase 2 | Pending |
| SAVINGS-03 | Phase 2 | Pending |
| PROGRESS-01 | Phase 2 | Pending |
| PROGRESS-02 | Phase 2 | Pending |
| PROGRESS-03 | Phase 2 | Pending |
| DEPLOY-01 | Phase 3 | Pending |
| DEPLOY-02 | Phase 3 | Pending |
| DEPLOY-03 | Phase 3 | Pending |
| DEPLOY-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-18*
*Last updated: 2026-04-18 after initial definition*
