# Phase 2: Frontend - Context

**Gathered:** 2026-04-18 (Claude's discretion — all decisions)
**Status:** Ready for planning

<domain>
## Phase Boundary

A browser user can type a spending impulse into the chat UI, watch the 财神's verdict stream token by token, and see the savings progress bar animate to reflect the tool-computed outcome. Backend (Phase 1) must be running at a known URL before wiring.

</domain>

<decisions>
## Implementation Decisions

### Project Scaffold
- **D-01:** Frontend lives at `cyber-god/frontend/` — Next.js 16 App Router, bootstrapped with `create-next-app` (TypeScript, Tailwind, App Router, no src/ directory, no Turbopack for compat).
- **D-02:** Entry point is `app/page.tsx` — a single-page app (no routing needed for PoC).
- **D-03:** Tailwind v4 CSS-first config: `@import "tailwindcss"` in `globals.css`, no `tailwind.config.js`.
- **D-04:** Environment variable: `NEXT_PUBLIC_API_URL` in `.env.local` — defaults to `http://localhost:8000` for local dev. **Never hard-code the backend URL.**

### Page Layout
- **D-05:** Single-column layout, full-height viewport. From top to bottom:
  1. **Header bar** — title "赛博财神爷" + subtitle, fixed height ~56px
  2. **Savings panel** — always-visible row with two number inputs (存款目标 / 已存金额) + progress bar directly below the inputs. Compact, ~100px total.
  3. **Chat area** — scrollable, flex-grow, fills remaining viewport height
  4. **Input row** — fixed at bottom, full width, with textarea + send/stop button

- **D-06:** Background: dark (`bg-gray-950`), text: `text-gray-100`. The whole page has a dark theme to evoke a mystical/nocturnal aesthetic fitting the 财神 persona.

### Savings Panel & Progress Bar
- **D-07:** Two inline number inputs side by side: `已存金额 [____]` and `目标金额 [____]`. Labels in Chinese. Input type `number`, min=0.
- **D-08:** `localStorage` keys: `gsd_savings` and `gsd_target`. Read on mount via `useEffect`, write on blur/change. Default values: savings=0, target=10000.
- **D-09:** Progress bar: `<div>` with Tailwind `transition-all duration-500` on the fill width. Fill is `bg-yellow-500` (gold, fitting wealth god theme). Text label shows `{pct}%` centered.
- **D-10:** Red flash on negative delta: add `animate-pulse bg-red-600` class to the fill div for 1.5s when `delta < 0`, then revert. Implemented via a `useState` flag + `setTimeout`.

### Chat Messages
- **D-11:** `useChat` from `ai` (v4) with `api: process.env.NEXT_PUBLIC_API_URL + "/api/chat"`. Body includes `savings` and `target` via the `body` option. No Next.js API proxy route.
- **D-12:** `onData` callback on `useChat` intercepts `2:` data parts. When data arrives, parse as `{new_savings, progress_pct, delta}` and update savings state.
- **D-13:** Message bubbles: user messages right-aligned (`bg-gray-700`), assistant messages left-aligned (`bg-gray-800`). No avatar — role labels only: `用户` vs `财神` in small gray text above bubble.
- **D-14:** Approve/reject visual: first line of assistant message is scanned for `【批准】` or `【拒绝】`. If found, bubble gets a left border: `border-l-4 border-green-500` for approve, `border-l-4 border-red-500` for reject. If not found (e.g. error message), no special border.
- **D-15:** Streaming typewriter: `useChat` handles this natively — no extra logic needed. The assistant message renders as it streams.

### Tool-Call Status
- **D-16:** During tool resolution phase (before streaming text begins), show a status line inside the assistant message bubble: a pulsing dot + text. The backend emits NO `0:` chunks during tool resolution (only the final `f:` init then jumps to `2:` then text). Frontend detects this as: message exists in `messages` array but `content` is empty string and `isLoading` is true → show "⚡ 财神正在掐指一算…".
- **D-17:** After the 2: data chunk arrives but before significant text renders, switch status text to "📊 正在计算影响…". Implemented by tracking whether `data` array is non-empty but `content.length < 5`.
- **D-18:** Status line styled as `text-yellow-400 text-sm animate-pulse` inside the bubble, hidden once content.length > 10.

### Input Area
- **D-19:** Single-line input (`<input type="text">`), not textarea — messages are short purchase impulses. Placeholder: `试试：我想花 800 买个盲盒`.
- **D-20:** During streaming (`isLoading=true`): input disabled, send button hidden, stop button shown (`■ 停止`). After streaming: input re-enabled, stop hidden, send shown.
- **D-21:** Submit on Enter key. Send button icon: `→` or `发送`.

### Empty State
- **D-22:** When `messages` is empty, show a centered placeholder in the chat area: the 财神 emoji or character + "财神在此，请问何处要花冤枉钱？" + example chip: "试试：我想花 800 买个盲盒" (clickable, fills input).

### Error State
- **D-23:** If `useChat` sets `error`, show a banner above the input: `⚠ 财神系统故障，请稍后再试。` + retry button that calls `reload()`.

### Claude's Discretion
- Exact font sizes and spacing
- Scrollbar styling (probably hidden or minimal)
- Mobile layout (best-effort on desktop first)
- Header icon/emoji choice

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — Phase 2 requirements: CHAT-01 through CHAT-07, SAVINGS-01 through SAVINGS-03, PROGRESS-01 through PROGRESS-03

### Architecture & Stack
- `CLAUDE.md` (project root) — Stack version pins (Next.js 16, ai@^4, Tailwind v4), what NOT to use, useChat wiring pattern, progress bar Tailwind example
- `.planning/PROJECT.md` — Core constraints (no DB, localStorage only, Chinese UI, no proxy route)
- `.planning/STATE.md §Accumulated Context` — Locked decisions: useChat api prop points directly at backend URL; 2: channel payload shape; onData callback pattern

### Backend Contract (Phase 1 output)
- `.planning/phases/01-backend-core/01-CONTEXT.md` — SSE wire format, ChatRequest shape `{messages, savings, target}`, 2: payload `{new_savings, progress_pct, delta}`
- `cyber-god/backend/api/routes.py` — Exact ChatRequest Pydantic model and response headers
- `cyber-god/backend/agent/loop.py` — What the backend emits and when (f:, 0:, 2:, e:, d: sequence)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cyber-god/backend/api/routes.py` — ChatRequest body shape: `{messages: [{role, content}], savings: float, target: float}` — must match exactly in useChat `body` option
- Backend SSE headers confirmed: `x-vercel-ai-data-stream: v1`, `X-Accel-Buffering: no` — useChat will parse 2: channel correctly

### Established Patterns
- Backend already emits `2:` as array-wrapped JSON (confirmed in loop.py) — frontend reads via `useChat.data` array
- No Next.js proxy route — this was explicitly rejected (Vercel 10s timeout kills streaming)

### Integration Points
- `NEXT_PUBLIC_API_URL/api/chat` — POST endpoint, SSE response
- `useChat.data[]` — receives 2: payload; parse `data[data.length-1]` as `{new_savings, progress_pct, delta}`
- `useChat.stop()` — stop button calls this
- `useChat.reload()` — error retry calls this

</code_context>

<specifics>
## Specific Ideas

- Dark theme (`bg-gray-950`) evokes mystical/nocturnal aesthetic — fits the 财神 god persona
- Gold progress bar (`bg-yellow-500`) ties into wealth/gold theme
- No avatar image needed — "财神" text label is sufficient for the PoC
- Approve = green left border, Reject = red left border — scan for 【批准】/【拒绝】in message content

</specifics>

<deferred>
## Deferred Ideas

- Mobile-responsive polish — Phase 2 targets desktop demo; mobile is best-effort
- Persona selector (internet-roast vs ancient-deity style) — noted in Phase 1 backlog
- Multi-turn conversation memory — v2 requirement (V2-01)
- Notification: "你还差 X 元就到目标了！" — v2 requirement (V2-04)

</deferred>

---

*Phase: 02-frontend*
*Context gathered: 2026-04-18*
