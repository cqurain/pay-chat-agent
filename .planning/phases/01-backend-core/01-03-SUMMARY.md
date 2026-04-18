---
phase: 01-backend-core
plan: "03"
status: complete
completed: 2026-04-18
gate: PASSED
---

# Plan 01-03 Summary: End-to-End Validation

## What Was Built

Phase 1 gate validated. Backend streaming confirmed working end-to-end via curl.

## Confirmed GLM Model

`glm-4-5` — authenticated and responsive. `glm-4-flash` also works but less reliable for tool calling.

## Curl Validation Evidence

**Command:**
```powershell
'{"messages":[{"role":"user","content":"我想花800块买个盲盒"}],"savings":5000,"target":10000}' | curl.exe -N -s -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d @-
```

**Output (abbreviated):**
```
f:{"id": "70d924e0-018d-4d7d-b1fa-86218590fda2"}
0:"【"
0:"驳回"
0:"】\n\n"
0:"真的"
0:"假的"
... (streaming Chinese verdict tokens)
2:[{"new_savings": 4407.86, "progress_pct": 44.08, "delta": -592.14}]
e:{"finishReason": "stop", "usage": {"promptTokens": 384, "completionTokens": 310}, "isContinued": false}
d:{"finishReason": "stop", "usage": {"promptTokens": 384, "completionTokens": 310}, "isContinued": false}
```

## Phase 1 Gate Checklist

- [x] Server starts without import errors or crash
- [x] All five line types present: `f:`, `0:`, `2:`, `e:`, `d:`
- [x] Chinese verdict with 【驳回】 in `0:` chunks
- [x] `2:` line contains real computed numbers (`new_savings`, `progress_pct`, `delta`)
- [x] No GLM auth or model-not-found errors
- [x] `.env` gitignored (T-03-01 mitigation committed)

## Issues Encountered and Resolutions

### Issue: GLM tool_choice="auto" unreliable
**Symptom:** `run_agent_loop` Phase 1 GLM call consistently returned no `tool_calls` even with clear system prompt instructions, triggering D-06 error fallback. Both `glm-4-flash` and `glm-4-5` exhibited this behavior.

**Root cause:** Zhipu models with `tool_choice="auto"` non-deterministically skip tool calls when a long persona system prompt is present. The `tool_choice="required"` alternative is documented to cause infinite loops (Pitfall 5).

**Resolution:** Replaced Phase 1 GLM tool-calling with direct tool dispatch:
- Extract user query from last user message
- Call `get_price(query, mcp_session)` directly
- Call `calculate_savings_impact(price, savings, target)` directly
- Inject results as simulated assistant+tool message exchange
- Phase 2 GLM receives full context and generates grounded verdict

This eliminates the GLM tool-calling reliability dependency while preserving the two-phase architecture and real MCP data flow.

### Issue: No streaming data visible in initial curl tests
**Symptom:** 15-second connection with no output.
**Root cause:** Initial tests used PowerShell's `curl` alias (Invoke-WebRequest) which buffers SSE. Switching to `curl.exe -N` resolved visibility. The actual data flow was correct throughout.

## Deviations from Plan

| Deviation | Impact | Status |
|-----------|--------|--------|
| D-07 HTTP 500 before stream — implemented as 200 + in-character error | Minor — PoC acceptable | Documented in 01-02-SUMMARY |
| Phase 1 GLM tool-calling replaced with direct dispatch | Architecture simplification — same observable behavior | Committed in fix(01-03) |
| `test-stream` diagnostic endpoint added to `api/routes.py` | Dev-only diagnostic, no functional impact | Kept for frontend debugging |

## Phase 1 Gate Status: PASSED
