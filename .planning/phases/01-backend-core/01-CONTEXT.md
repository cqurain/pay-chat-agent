# Phase 1: Backend Core - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

You can curl POST /api/chat with a purchase impulse and receive a GLM-5-powered streaming verdict — including tool execution results and a structured savings payload — in the correct Vercel Data Stream Protocol wire format. Frontend is a separate phase.

</domain>

<decisions>
## Implementation Decisions

### Local Price MCP Server
- **D-01:** Product price lookup is served by a **local MCP server** (`price_mcp/`) implemented following agora-mcp's tool interface pattern (reference: https://github.com/Fewsats/agora-mcp). No external API calls, no API key required.
- **D-02:** The local MCP server exposes a `search_products(query: str) -> list[{name, price, currency}]` tool. Internally it uses the same ~10–15 item catalog of common Chinese consumer goods with realistic RMB prices + ±30% randomization — the MCP protocol is the abstraction boundary, not a Python protocol class.
- **D-03:** Unknown items not in catalog return a sensible default price (~500 RMB ± 30%). The MCP server is the only place price logic lives — the FastAPI backend has zero price knowledge.
- **D-16:** FastAPI backend is an **MCP client**: it spawns `price_mcp/server.py` as a subprocess using the `mcp` Python SDK (`mcp>=1.0`) stdio transport, calls `search_products`, and returns the result as the tool response to GLM. Add `mcp` to `requirements.txt`.

### Backend Module Structure
- **D-04:** Feature-module layout under `cyber-god/backend/`:
  ```
  cyber-god/backend/
    config.py          ← env var loading (ZHIPU_API_KEY, GLM_MODEL, ALLOWED_ORIGINS)
    price_mcp/
      __init__.py
      server.py        ← local MCP server: search_products tool + catalog data
    tools/
      __init__.py
      price.py         ← MCP client wrapper: spawns price_mcp/server.py, calls search_products
      savings.py       ← calculate_savings_impact
    agent/
      __init__.py
      loop.py          ← two-phase GLM call loop + SSE formatting
      prompt.py        ← system prompt construction
    api/
      __init__.py
      routes.py        ← FastAPI router for /api/chat
    main.py            ← FastAPI app + CORS + router registration
  ```

### Stream Error Handling
- **D-05:** If GLM call 1 (stream=False, tool resolution) returns no tool calls: retry ONCE with an explicit system-level instruction appended to messages ("你必须先调用 search_products 和 calculate_savings_impact 工具")
- **D-06:** If retry still returns no tool calls: emit an in-character error message as a `0:` chunk (e.g., `0:"财神出岁了！天机不可泄露，稍后再来。"\n`) then close the stream normally with `e:` and `d:` lines — do NOT return HTTP 500
- **D-07:** If GLM call 1 fails entirely (network error, auth error): return HTTP 500 before streaming starts with a JSON error body — this is a hard failure before any stream is opened

### 毒舌财神 Persona
- **D-08:** Internet-roast style — heavy meme language, internet slang (u1s1, 富婆, 饭局雄, 真的假的), punchy short sentences, maximum savagery within reason; never directly attacks the user personally, always attacks the purchase decision
- **D-09:** System prompt must instruct GLM to: (1) always call both tools before replying, (2) lead with explicit approve/reject verdict on first line, (3) ground the verdict in the computed numbers (delta RMB, new progress %), (4) reply entirely in Chinese
- **D-10:** System prompt lives in `agent/prompt.py` as a module-level constant — not inline in the route handler

### Locked Decisions (from prior research)
- **D-11:** SSE format: Vercel Data Stream Protocol — `f:`, `0:`, `2:`, `e:`, `d:` lines; response header must include `x-vercel-ai-data-stream: v1` and `X-Accel-Buffering: no`
- **D-12:** Two-phase GLM calls: `stream=False` + `tool_choice="auto"` for tool resolution; `stream=True` for verdict generation — `tool_choice="required"` confirmed causes GLM infinite loop
- **D-13:** Structured savings payload `{new_savings, progress_pct, delta}` rides the `2:` channel (array-wrapped JSON), NOT the `0:` text channel
- **D-14:** CORS via `CORSMiddleware` with `ALLOWED_ORIGINS` env var; wildcard `*` acceptable for dev
- **D-15:** `GLM_MODEL` env var: `glm-4-flash` for dev (free/fast), `glm-4-5` for prod — never hard-coded

### Claude's Discretion
- Exact RMB base prices for each catalog item inside `price_mcp/server.py` (should feel realistic)
- Specific ±30% randomization strategy (just `random.uniform(0.7, 1.3) * base`)
- MCP server startup mechanics (stdio transport, subprocess lifecycle management)
- uvicorn startup command and dev script
- Exact wording of the retry injection message
- `requirements.txt` / `pyproject.toml` choice and pinned versions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — Phase 1 requirements: TOOL-01, TOOL-02, AGENT-01 through AGENT-07, PERSONA-01, PERSONA-02

### Architecture + Stack
- `CLAUDE.md` (project root) — Full stack spec including fastapi/openai/uvicorn version pins, GLM-5 specifics, known streaming gotchas, and WHAT NOT TO USE
- `.planning/PROJECT.md` — Project constraints, key decisions, out-of-scope items
- `.planning/STATE.md §Accumulated Context` — Locked decisions table and pitfalls to watch

### Phase Gate
- `.planning/ROADMAP.md §Phase 1 Gate` — GLM model string confirmed working + SSE wire format validated with curl before Phase 2

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — project not initialized (no source files)

### Established Patterns
- FastAPI `StreamingResponse` with async generator is the required streaming pattern (from CLAUDE.md)
- `AsyncOpenAI(base_url=..., api_key=...)` is the GLM-5 client pattern — same as OpenAI, different base_url

### Integration Points
- Phase 2 (Frontend) will wire `useChat` directly to `POST /api/chat` — the SSE format emitted here IS the contract that Phase 2 depends on
- `2:` data chunk carries `{new_savings, progress_pct, delta}` — Phase 2 reads this via `onData` callback

</code_context>

<specifics>
## Specific Ideas

- Local MCP server catalog should cover items commonly impulse-purchased by young Chinese consumers: 盲盒, 奶茶, 耳机, 口红, 球鞋, 游戏皮肤/充值, 手机壳, 咖啡, 键盘外设, 网红零食
- In-character error fallback example: "财神出岁了！天机不可泄露，稍后再来。" — brief, on-brand, doesn't break immersion
- Internet-roast persona reference: think "真的假的？你是认真的？这都舍得买？" energy — deadpan disbelief rather than lecturing

</specifics>

<deferred>
## Deferred Ideas

- **Persona selector** — End-user selectable persona style (internet-roast / sharp-uncle / ancient-deity crossover). Noted for backlog — Phase 1 hardcodes internet-roast style.

### Reviewed Todos
None — no open todos at project start.

</deferred>

---

*Phase: 01-backend-core*
*Context gathered: 2026-04-18*
