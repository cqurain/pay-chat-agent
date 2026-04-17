# Phase 1: Backend Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 01-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-18
**Phase:** 01-backend-core
**Mode:** discuss
**Areas discussed:** Mock data catalog, Backend module structure, Stream error handling, 毒舌财神 system prompt tone

---

## Gray Areas Presented

| # | Area | Selected |
|---|------|----------|
| 1 | Mock data catalog | ✓ |
| 2 | Backend module structure | ✓ |
| 3 | Stream error handling | ✓ |
| 4 | 毒舌财神 system prompt tone | ✓ |
| — | Local dev setup | skipped |

---

## Decisions Made

### Mock Data Catalog
| Question | Options Presented | Decision |
|----------|------------------|----------|
| How to handle unknown items? | Any item random / Fixed catalog + fallback / Fixed catalog only | Fixed catalog (~10-15 items) + 500 RMB fallback; design for MCP extensibility |

**User note:** "设计的时候要保证后续使用真实数据的可扩展性（比如调用外部的MCP server）"
→ Captured as D-03: PriceLookup interface/protocol to enable future swap.

### Backend Module Structure
| Question | Options Presented | Decision |
|----------|------------------|----------|
| File layout? | Single main.py / Split by concern / Feature-module layout | Feature-module layout (production-style) |

### Stream Error Handling
| Question | Options Presented | Decision |
|----------|------------------|----------|
| On no tool calls? | Error as SSE stream / HTTP 500 / Retry once then stream error | Retry once with explicit instruction; fallback to in-character 0: chunk |

**User note:** "再次重试 GLM 第一次调用；如果仍然没有触发工具，发出一个带有符合人设的错误消息的 0: 数据块"
→ Captured as D-05 + D-06. HTTP 500 reserved for hard pre-stream failures (D-07).

### 毒舌财神 Persona
| Question | Options Presented | Decision |
|----------|------------------|----------|
| Fixed style vs selectable? | Pick one now / Make end-user selectable | Pick one now (scope guardrail applied) |
| Which style? | Sharp uncle / Internet-roast / Ancient deity | Internet-roast style |

**Scope guardrail applied:** End-user persona selection would be new capability beyond PERSONA-01. Deferred to backlog.

---

## Scope Guardrail Applied

**Triggered:** User requested end-user-selectable persona styles.
**Action:** Redirected — "Persona selection would be a new capability beyond Phase 1's scope (PERSONA-01 says 'hardcodes 毒舌财神 persona')." Deferred to backlog.
**Backlog item:** Persona selector — internet-roast / sharp-uncle / ancient-deity crossover.

---

## Prior Decisions Not Re-Asked

These were already locked in STATE.md and carried forward without re-asking:
- SSE wire format (Vercel Data Stream Protocol)
- Two-phase GLM loop (stream=False → tool resolution, stream=True → verdict)
- tool_choice=auto (not required — confirmed GLM bug)
- CORS via ALLOWED_ORIGINS env var
- 2: channel for savings payload
- openai SDK ~=1.x, ai SDK ^4.x
- GLM_MODEL via env var
