---
phase: quick
plan: 260419-nlk
subsystem: backend+frontend
tags: [llm-intent, tavily, persona, price-sources, ux]
dependency_graph:
  requires: []
  provides:
    - LLM intent extraction before MCP (glm-4-flash JSON mode)
    - Tavily-first price search with structured sources list
    - Dual persona system (snarky/gentle) with localStorage persistence
    - Platform badges in PriceResearchCard for scraped results
  affects:
    - cyber-god/backend/price_mcp/server.py
    - cyber-god/backend/agent/prompt.py
    - cyber-god/backend/agent/loop.py
    - cyber-god/backend/api/routes.py
    - cyber-god/frontend/lib/types.ts
    - cyber-god/frontend/lib/storage.ts
    - cyber-god/frontend/app/page.tsx
    - cyber-god/frontend/components/Header.tsx
    - cyber-god/frontend/components/PriceResearchCard.tsx
tech_stack:
  added: []
  patterns:
    - LLM JSON mode for intent extraction (glm-4-flash, response_format=json_object)
    - Tavily-first with DDGS fallback; dedup by platform, lowest-price-wins, top 3
    - Persona-parameterized system prompts via build_system_prompt(persona)
    - sources list propagated end-to-end: server.py -> loop.py 2: channel -> PriceResearchCard
key_files:
  created: []
  modified:
    - cyber-god/backend/price_mcp/server.py
    - cyber-god/backend/agent/prompt.py
    - cyber-god/backend/agent/loop.py
    - cyber-god/backend/api/routes.py
    - cyber-god/frontend/lib/types.ts
    - cyber-god/frontend/lib/storage.ts
    - cyber-god/frontend/app/page.tsx
    - cyber-god/frontend/components/Header.tsx
    - cyber-god/frontend/components/PriceResearchCard.tsx
decisions:
  - "Removed _extract_explicit_price/_extract_keyword from server.py — LLM handles this in loop.py Phase 0"
  - "Tavily-first order in _resolve_price: better CN coverage; DDGS as fallback"
  - "Per-platform dedup (lowest price wins) + top-3 cap on sources list"
  - "build_system_prompt keeps SYSTEM_PROMPT shim for backward compat"
  - "Double cast (unknown as SavingsPayload[]) needed for useChat.data after adding PriceSource to SavingsPayload"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-19T09:18:29Z"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 9
---

# Quick Plan 260419-nlk: LLM Intent Extraction + Tavily-First + Dual Persona + Platform Badges

**One-liner:** LLM (glm-4-flash JSON mode) extracts clean product keyword before MCP; Tavily-first search with per-platform dedup surfaces top-3 source badges to frontend; dual snarky/gentle persona persists in localStorage with Header toggle.

---

## Tasks Completed

| # | Name | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Tavily-first + structured sources in server.py | `1e786b6` | `price_mcp/server.py` |
| 2 | Dual persona, LLM intent extraction, sources in payload | `5301f6a` | `agent/prompt.py`, `agent/loop.py`, `api/routes.py` |
| 3 | Frontend persona toggle, PriceSource types, platform badges | `db88194` | `lib/types.ts`, `lib/storage.ts`, `app/page.tsx`, `Header.tsx`, `PriceResearchCard.tsx` |

---

## What Was Built

### Task 1 — server.py refactor

- Removed `_EXTRA_PRICE_RE`, `_extract_explicit_price`, `_extract_keyword`, `_extract_prices_from_texts` (LLM now handles extraction in loop.py Phase 0)
- Added `_PLATFORM_MAP` and `_infer_platform(url)` — returns CN platform name for major e-commerce domains (京东, 淘宝, 天猫, 拼多多, 闲鱼, 苏宁, 什么值得买, 亚马逊)
- Rewrote `_ddgs_search_sync` and `_tavily_search_sync` to return `list[dict]` with `{price, platform, url}` — one entry per search result, first matching price only
- Rewrote `_resolve_price(keyword)`: Tavily first, DDGS fallback; dedup by platform (lowest price per platform); sort by price; top 3; all return paths include `"sources"` key

### Task 2 — backend agent

**prompt.py:** Replaced monolithic `SYSTEM_PROMPT` string with `PERSONAS` dict + `build_system_prompt(persona)`. `_DATA_RULES` contains all existing rules plus updated scraped-confidence note ("优先级高于你的训练知识"). `SYSTEM_PROMPT` shim preserved for backward compat.

**loop.py:** Added `_extract_intent(user_query, glm_client)` — calls glm-4-flash with `response_format={"type":"json_object"}` to extract `{product, stated_price}` before any MCP call. If `stated_price` is not None, MCP is skipped and `confidence="user_stated"` is set directly. Scraped `price_context` includes UTC timestamp and platform source list. `savings_payload` gains `"sources"` key. `run_agent_loop` gains `persona` parameter.

**routes.py:** `ChatRequest` gains `persona: str = "snarky"`. `run_agent_loop` call passes `persona=body.persona`.

### Task 3 — frontend

**types.ts:** Added `Persona` type, `PriceSource` interface, `sources?: PriceSource[]` on `SavingsPayload`, `persona: Persona` on `ChatRequestBody`.

**storage.ts:** Added `PERSONA: 'gsd_persona'` to `STORAGE_KEYS`. Added `getPersona()` (returns 'snarky' default) and `setPersona(p)`.

**page.tsx:** `persona` state initialized from `getPersona()` in `useEffect`. `handlePersonaChange` calls both `setPersonaState` and `setPersona`. `useChat` body includes `persona`. `<Header>` receives `persona` and `onPersonaChange` props.

**Header.tsx:** Full rewrite — sidebar toggle moved into `<div className="flex items-center gap-2">` alongside new persona toggle button. Toggle shows 😈毒舌 or 🌸温柔 based on current persona.

**PriceResearchCard.tsx:** Destructures `sources` from payload. Renders green badge `<a>` links (platform + price) below the source tag when `confidence === 'scraped'` and `sources.length > 0`.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `_extract_prices_from_texts` function**
- **Found during:** Task 1
- **Issue:** After rewriting `_ddgs_search_sync` and `_tavily_search_sync` to inline their own price parsing, `_extract_prices_from_texts` became unreferenced. IDE flagged it as a hint.
- **Fix:** Removed the function entirely — it was only used by the old sync implementations.
- **Files modified:** `cyber-god/backend/price_mcp/server.py`
- **Commit:** `1e786b6`

**2. [Rule 1 - Bug] Double cast for `useChat.data` type narrowing**
- **Found during:** Task 3 — TypeScript check
- **Issue:** Adding `PriceSource[]` to `SavingsPayload.sources` made the existing `(chatData ?? []) as SavingsPayload[]` cast fail TS2352 (JSONValue[] has insufficient overlap).
- **Fix:** Changed to `(chatData ?? []) as unknown as SavingsPayload[]` — standard pattern for Vercel AI SDK data channel typing.
- **Files modified:** `cyber-god/frontend/app/page.tsx`
- **Commit:** `db88194`

---

## Known Stubs

None — all data paths are wired end-to-end. `sources` may be `[]` at runtime if Tavily key is absent and DDGS finds no prices (catalog/unknown paths), which is correct behavior documented in the plan.

---

## Threat Flags

No new trust boundaries introduced beyond what the plan's threat model covers:
- `persona` string is safely gated by `PERSONAS.get(persona, PERSONAS["snarky"])` — unknown values fall back (T-nlk-01)
- Platform badge `href` values originate from search engine result URLs rendered with `rel="noopener noreferrer"` (T-nlk-04)

---

## Self-Check: PASSED

Files verified present:
- `cyber-god/backend/price_mcp/server.py` — FOUND
- `cyber-god/backend/agent/prompt.py` — FOUND
- `cyber-god/backend/agent/loop.py` — FOUND
- `cyber-god/backend/api/routes.py` — FOUND
- `cyber-god/frontend/lib/types.ts` — FOUND
- `cyber-god/frontend/lib/storage.ts` — FOUND
- `cyber-god/frontend/app/page.tsx` — FOUND
- `cyber-god/frontend/components/Header.tsx` — FOUND
- `cyber-god/frontend/components/PriceResearchCard.tsx` — FOUND

Commits verified:
- `1e786b6` — server.py Task 1
- `5301f6a` — backend agent Task 2
- `db88194` — frontend Task 3

TypeScript: `npx tsc --noEmit` — 0 errors
