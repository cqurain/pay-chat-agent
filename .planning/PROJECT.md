# Cyber God of Wealth（赛博财神爷）

## What This Is

A PoC AI finance companion Agent with a "毒舌财神" (snarky wealth god) persona. Users input a spending impulse (e.g., "我想花 800 买个盲盒"), and the Agent queries mock price data, calculates impact on their savings goal, then delivers a streaming verdict — approve or reject — while updating a live savings progress bar in the frontend.

## Core Value

The Agent must make a data-backed decision (approve or reject the purchase) and stream it in character, with the progress bar updating in real time. Everything else is secondary.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] POST /api/chat backend endpoint with GLM-5 function calling and StreamingResponse
- [ ] Tool: get_mock_price — returns ±30% randomized price for any item name
- [ ] Tool: calculate_savings_impact — computes new_savings, progress %, delta, comment_hint
- [ ] 毒舌财神 system prompt — data-driven,劝退-first, sarcastic but not attacking
- [ ] Streaming token output to frontend (typewriter effect via Vercel AI SDK useChat)
- [ ] Structured data payload at end of stream for progress bar update
- [ ] Frontend: user-editable savings target + current savings (persisted in localStorage)
- [ ] Frontend: live progress bar that updates from Agent response
- [ ] Vercel deployment guide for frontend; Railway/Render guide for backend

### Out of Scope

- MCP, LangGraph, multi-agent — PoC only, single LLM loop
- Database (MySQL / Redis) — localStorage + in-memory state only
- Real price data APIs — mock only
- Mobile app — web only
- OAuth / user accounts — no auth for PoC

## Context

- **LLM**: GLM-5 via Zhipu AI (OpenAI-compatible, base_url=https://open.bigmodel.cn/api/paas/v4/)
- **API key**: configured via ZHIPU_API_KEY env var
- **Model name**: glm-4-5 (configurable via env)
- **Runtime environment**: Windows / PowerShell for local dev
- **Project root**: e:\cs\towk\pay-chat-agent
- **Monorepo structure**: /cyber-god/frontend + /cyber-god/backend at project root
- **Frontend deployment**: Vercel (Next.js App Router)
- **Backend deployment**: Railway or Render (FastAPI + uvicorn)
- **UI language**: Chinese — 财神 replies in Chinese, UI labels in Chinese

## Constraints

- **Tech stack**: FastAPI + Pydantic + Next.js App Router + Tailwind CSS + Vercel AI SDK — no deviations
- **Function calling**: must use OpenAI-compatible tool_calls pattern (works with GLM-5)
- **Streaming**: backend must use FastAPI StreamingResponse; frontend must use useChat
- **No DB**: all state in React state + localStorage

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GLM-5 via Zhipu AI | User's chosen provider, OpenAI-compatible | — Pending |
| Structured data at stream end | Progress bar needs final JSON; append as last SSE chunk | — Pending |
| localStorage for savings state | No DB, PoC scope, survives refresh | — Pending |
| Monorepo under /cyber-god | Clean separation, single repo for GitHub | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-18 after initialization*
