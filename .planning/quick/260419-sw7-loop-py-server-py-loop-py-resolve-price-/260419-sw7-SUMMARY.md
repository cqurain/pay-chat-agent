---
phase: quick-260419-sw7
plan: 01
subsystem: backend/agent
tags: [refactor, loop, price-mcp, llm-extraction]
dependency_graph:
  requires: []
  provides: [_resolve_price, _build_price_context, _build_tool_context, _inject_tool_exchange, _build_savings_payload, _stream_verdict, _llm_extract_prices]
  affects: [cyber-god/backend/agent/loop.py, cyber-god/backend/price_mcp/server.py]
tech_stack:
  added: []
  patterns: [helper-function-extraction, llm-json-mode-extraction, raw-snippet-pipeline]
key_files:
  modified:
    - cyber-god/backend/agent/loop.py
    - cyber-god/backend/price_mcp/server.py
decisions:
  - "_build_no_intent_sentinel extracted as 8th helper (not in plan) to keep run_agent_loop under 40 lines while preserving inline sentinel dict logic"
  - "_resolve_price in loop.py is a separate function from _resolve_price in server.py — loop.py version handles user_stated shortcut; server.py version handles search+LLM extraction"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-19"
  tasks_completed: 2
  files_modified: 2
---

# Phase quick-260419-sw7 Plan 01: loop.py + server.py Refactor Summary

**One-liner:** Extracted seven named helpers from run_agent_loop and replaced regex price extraction in server.py with glm-4-flash JSON-mode LLM extraction.

---

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Extract helper functions in loop.py | d3626d5 | cyber-god/backend/agent/loop.py |
| 2 | Refactor server.py — raw snippets + LLM price extraction | 9a631a4 | cyber-god/backend/price_mcp/server.py |

---

## What Was Built

### Task 1 — loop.py helper extraction

Six helpers specified in the plan plus one deviation helper were added between `_extract_intent` and `run_agent_loop`:

- `_resolve_price(intent, mcp_session)` — user_stated shortcut or MCP delegation
- `_build_price_context(price_data)` — confidence-based context string for GLM
- `_build_tool_context(price_context, savings, target, impact, tx_analysis)` — tool result dict
- `_inject_tool_exchange(messages, tool_context, user_query)` — synthetic tool call pair (non-mutating)
- `_build_savings_payload(price_data, impact)` — 2: channel dict
- `_stream_verdict(glm_client, model, messages)` — async generator for streaming GLM + e:/d: finish
- `_build_no_intent_sentinel(savings, target)` — sentinel payload for non-purchase path (deviation, see below)

`run_agent_loop` reduced to 35 lines (pure orchestration skeleton, verification required <=40).

### Task 2 — server.py LLM price extraction

- Removed `_PRICE_RE` compiled regex and `re` import (no other usages)
- Moved `_TAVILY_API_KEY` after `server = Server(...)` and added `_glm_client` module-level instance
- `_ddgs_search_sync` and `_tavily_search_sync` now return `list[{text, url}]` raw snippets (no regex parsing)
- Added `_llm_extract_prices(snippets, client)` — async, glm-4-flash JSON mode, validates `10 <= price <= 100_000`, per-item try/except, full function wrapped in try/except returning `[]` on error
- `_resolve_price` collects raw snippets then calls `_llm_extract_prices`; dedup/filter/catalog guard logic unchanged

---

## Deviations from Plan

### Auto-added Helper

**1. [Rule 2 - Missing] Added `_build_no_intent_sentinel` helper**
- **Found during:** Task 1 verification (run_agent_loop was 53 lines, over the 40-line limit)
- **Issue:** The inline sentinel dict for the non-purchase path occupied 12 lines inside run_agent_loop, preventing the line-count requirement from being met after the docstring and signature were counted by `inspect.getsource`
- **Fix:** Extracted sentinel dict into `_build_no_intent_sentinel(savings, target)` helper; collapsed non-purchase block from 14 lines to 3 lines
- **Files modified:** cyber-god/backend/agent/loop.py
- **Commit:** d3626d5

---

## Verification Results

All four plan verification checks passed:

```
loop imports OK
server imports OK
PRICE_RE removed OK
run_agent_loop: 35 lines
```

---

## Known Stubs

None — all functions have real implementations wired to live data paths.

---

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. The `_glm_client` instance added to server.py uses the same Zhipu endpoint already used in loop.py — no new trust boundary.

Threat mitigations from plan implemented as specified:
- T-sw7-01: `10 <= price <= 100_000` range check with per-item try/except in `_llm_extract_prices`
- T-sw7-02: `s['text'][:300]` truncation before injecting into LLM prompt
- T-sw7-04: entire `_llm_extract_prices` wrapped in outer try/except returning `[]`

---

## Self-Check: PASSED

- cyber-god/backend/agent/loop.py: exists and imports OK
- cyber-god/backend/price_mcp/server.py: exists and imports OK
- Commit d3626d5: present in git log
- Commit 9a631a4: present in git log
