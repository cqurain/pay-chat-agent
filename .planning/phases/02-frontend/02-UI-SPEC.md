---
phase: 2
slug: frontend
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-18
---

# Phase 2 — UI Design Contract

> Visual and interaction contract for the Chat UI, Savings Panel, and Progress Bar. Generated from Phase 2 CONTEXT decisions (D-01 through D-23) and REQUIREMENTS (CHAT-01 through CHAT-07, SAVINGS-01 through SAVINGS-03, PROGRESS-01 through PROGRESS-03).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | Tailwind CSS |
| Preset | none — CSS-first v4 config with `@import "tailwindcss"` in `globals.css` |
| Component library | None (built from scratch with Tailwind utilities) |
| Icon library | Unicode emoji + plain text symbols (`→`, `■`, `⚡`, `📊`, `⚠`) |
| Font | System font stack (TBD in globals.css — recommend: `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`) |

**Sources:**
- D-03: Tailwind v4 CSS-first config
- CLAUDE.md: Next.js 16.x + Tailwind CSS ^4.2

---

## Spacing Scale

Declared values (all multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Reserved for future internal gaps |
| sm | 8px | Inline padding, compact spacing |
| md | 16px | Default message padding, input padding |
| lg | 24px | Section padding (header, savings panel) |
| xl | 32px | Layout gaps between major sections |
| 2xl | 48px | Between header and savings panel |

**Layout exceptions (fixed pixel heights, not scale-based):**
- Header: 56px fixed height (D-05)
- Savings panel: 100px total height including progress bar (D-05)
- Input area: `py-4` (16px) padding, `h-12` (48px) input height

**Sources:**
- D-05: Layout structure (fixed heights for header, savings, chat area)
- D-07: Two inline inputs (no explicit gap — use `gap-4` or `gap-8` TBD in implementation)

---

## Typography

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Body | 16px | 400 (regular) | 1.5 | Chat message bubbles, input placeholder |
| Label | 14px | 400 (regular) | 1.5 | Savings input labels ("已存金额", "目标金额"), role labels ("用户", "财神"), status text |
| Heading | 20px | 600 (semibold) | 1.2 | Header title ("赛博财神爷") |
| Display | 18px | 600 (semibold) | 1.2 | Progress bar percentage text (centered, large) |

**Sources:**
- D-06: Dark theme text color: `text-gray-100`
- D-07: Input labels in Chinese
- D-13: Role labels in small gray text
- D-22: Header title "赛博财神爷"
- D-09: Progress bar shows `{pct}%` centered in large text

**Font family:** Apply system font stack to all text. Recommend:
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
```

---

## Color

| Role | Hex | RGB | Tailwind | Usage |
|------|-----|-----|----------|-------|
| **Dominant (60%)** | `#030712` | `rgb(3, 7, 18)` | `gray-950` | Page background, default surface |
| **Secondary (30%)** | `#1f2937` | `rgb(31, 41, 55)` | `gray-800` | Assistant message bubbles, default card background |
| **Tertiary (10%)** | `#374151` | `rgb(55, 65, 81)` | `gray-700` | User message bubbles, input area background |
| **Accent — Gold** | `#eab308` | `rgb(234, 179, 8)` | `yellow-500` | Progress bar fill, wealth god theme |
| **Accent — Approve** | `#22c55e` | `rgb(34, 197, 94)` | `green-500` | Left border on approve verdict messages |
| **Accent — Reject** | `#ef4444` | `rgb(239, 68, 68)` | `red-500` | Left border on reject verdict messages |
| **Accent — Reject Flash** | `#dc2626` | `rgb(220, 38, 38)` | `red-600` | Red flash bg when delta < 0 (1.5s animate-pulse) |
| **Status Text** | `#facc15` | `rgb(250, 204, 21)` | `yellow-400` | Tool-call status text (pulsing) |
| **Text Primary** | `#f3f4f6` | `rgb(243, 244, 246)` | `gray-100` | All body text, message content |
| **Text Secondary** | `#9ca3af` | `rgb(156, 163, 175)` | `gray-400` | Role labels, status sublabels |

**Accent reserved for:**
1. `yellow-500` — Progress bar fill, wealth/gold theme
2. `green-500` — Left border (`border-l-4`) on approve verdicts (detect `【批准】` in content)
3. `red-500` — Left border (`border-l-4`) on reject verdicts (detect `【拒绝】` in content)
4. `yellow-400` — Tool-call status text ("⚡ 财神正在掐指一算…", "📊 正在计算影响…") with `animate-pulse`
5. `red-600` — Temporary flash bg on progress bar when `delta < 0` (1.5s duration)

**Sources:**
- D-06: Dark theme (`bg-gray-950`, `text-gray-100`)
- D-09: Gold progress bar (`bg-yellow-500`)
- D-10: Red flash on negative delta (`bg-red-600`)
- D-14: Approve/reject borders (green/red `border-l-4`)
- D-16, D-17, D-18: Status text (`text-yellow-400 animate-pulse`)

---

## Layout & Component Contracts

### Page Structure (Full Height, Vertical Stack)

```
┌─────────────────────────────────┐
│  Header (fixed 56px)            │  Header Bar
├─────────────────────────────────┤
│  Savings Panel (100px)          │  Savings & Progress Bar
│  - Inputs + Progress            │
├─────────────────────────────────┤
│                                 │
│  Chat Area (flex-grow)          │  Scrollable message list
│                                 │
├─────────────────────────────────┤
│  Input Row (fixed)              │  Input + Send/Stop Button
└─────────────────────────────────┘
```

**Sources:** D-05 — "Single-column layout, full-height viewport. From top to bottom..."

### Header Bar (56px, fixed)

- **Background:** `bg-gray-950` (dominant)
- **Title:** "赛博财神爷" in `text-xl` (20px) `font-semibold` (weight 600)
- **Subtitle:** Optional (e.g., "你的AI财务顾问" or similar) — TBD in implementation
- **Padding:** `px-6 py-4` (16px vertical, 24px horizontal)
- **Text color:** `text-gray-100`

**Source:** D-05, D-06

### Savings Panel (100px total, fixed)

**Two-row layout:**

**Row 1: Inputs (side by side)**
- **Container:** `flex gap-8 px-6 py-4` — two number inputs with 32px gap
- **Input 1:** Label "已存金额" above `<input type="number" min="0" />` — Tailwind `w-32 px-3 py-2 bg-gray-800 border border-gray-600 text-gray-100 rounded`
- **Input 2:** Label "目标金额" above `<input type="number" min="0" />` — same styling
- **localStorage keys:** `gsd_savings` and `gsd_target`
- **Default values:** savings=0, target=10000
- **Persistence:** Read on mount via `useEffect`, write on blur/change events
- **Input text color:** `text-gray-100`, placeholder `placeholder-gray-500`

**Row 2: Progress Bar (below inputs)**
- **Container:** `px-6 py-2` — `w-full`
- **Bar bg:** `bg-gray-800` (secondary)
- **Bar fill:** `bg-yellow-500` (accent gold)
- **Fill width:** `width: {pct}%` calculated as `(savings / target) * 100`
- **Transitions:** `transition-all duration-500` for smooth animation
- **Height:** `h-8` (32px) for comfortable text centering
- **Text label:** `{pct}%` centered inside bar, bold (`font-semibold`), `text-gray-900` (dark text on gold)
- **Red flash:** When `delta < 0`, add classes `animate-pulse bg-red-600` for 1.5s, then remove. Implemented via `useState(isFlashing)` + `setTimeout`.

**Sources:** D-07, D-08, D-09, D-10

### Chat Area (flex-grow, scrollable)

- **Container:** `flex flex-col flex-grow overflow-y-auto`
- **Padding:** `px-6 py-4`
- **Scrollbar:** Hidden or minimal (Claude's discretion)

#### Empty State (when `messages.length === 0`)

- **Content:** Centered, vertical stack
- **Symbol:** "财神" emoji or character (large, ~64px)
- **Heading:** "财神在此，请问何处要花冤枉钱？" (centered, `text-lg`, `text-gray-200`)
- **Example chip:** Clickable element showing "试试：我想花 800 买个盲盒" — on click, fills input and focuses
- **Styling:** `text-gray-400` for example text, hover to `text-gray-300`, cursor pointer

**Source:** D-22

#### Error State (when `useChat.error` is set)

- **Banner:** Above input row, `bg-red-900 border-l-4 border-red-500 px-4 py-3 mb-4`
- **Text:** "⚠ 财神系统故障，请稍后再试。" in `text-red-200`
- **Retry button:** "重试" — inline, calls `reload()`

**Source:** D-23

#### Message Bubbles

**User Messages (right-aligned):**
- **Container:** `flex justify-end mb-4`
- **Bubble:** `bg-gray-700 text-gray-100 px-4 py-3 rounded-lg max-w-2xl`
- **Role label:** "用户" in small `text-gray-400` text above bubble
- **Content:** Plain text, wraps

**Assistant Messages (left-aligned):**
- **Container:** `flex justify-start mb-4`
- **Bubble:** `bg-gray-800 text-gray-100 px-4 py-3 rounded-lg max-w-2xl`
- **Role label:** "财神" in small `text-gray-400` text above bubble
- **Content:** Streams token by token (native `useChat` behavior)

**Approve/Reject Border:**
- **Detection:** Scan first line of assistant message for `【批准】` or `【拒绝】` Chinese brackets
- **Approve:** Add `border-l-4 border-green-500` to bubble
- **Reject:** Add `border-l-4 border-red-500` to bubble
- **If not found:** No special border

**Source:** D-13, D-14

#### Tool-Call Status Line

**Trigger:** Message exists in `messages` array but `content === ""` and `isLoading === true`

**Display Logic:**
1. **Phase 1:** Show "⚡ 财神正在掐指一算…" while `data.length === 0`
2. **Phase 2:** After `2:` data chunk (when `data.length > 0`), switch to "📊 正在计算影响…" while `content.length < 5`
3. **Hidden:** Once `content.length >= 10`

**Styling:** `text-yellow-400 text-sm animate-pulse`

**Sources:** D-16, D-17, D-18

### Input Row (fixed at bottom)

- **Container:** `flex gap-4 px-6 py-4 bg-gray-900 border-t border-gray-800`
- **Input:** `<input type="text" />` with placeholder "试试：我想花 800 买个盲盒"
- **Input styling:** `flex-grow px-4 py-3 bg-gray-800 border border-gray-600 text-gray-100 rounded-lg focus:outline-none focus:border-yellow-500`
- **Input state:** Disabled during streaming (`isLoading === true`)

**Button state:**
- **During streaming:** Send button hidden, Stop button (`■ 停止`) visible
- **Not streaming:** Send button visible, Stop button hidden

**Send button styling:** `px-4 py-3 bg-yellow-500 text-gray-900 font-semibold rounded-lg hover:bg-yellow-400 transition-colors`

**Stop button styling:** `px-4 py-3 bg-red-500 text-white font-semibold rounded-lg hover:bg-red-600 transition-colors`

**Keyboard:** Submit on `Enter` key press (not `Shift+Enter`)

**Sources:** D-19, D-20, D-21

---

## Copywriting Contract

| Element | Chinese Copy | English (Context Only) | Location |
|---------|--------|--------|----------|
| **Header title** | `赛博财神爷` | Cyber God of Wealth | Fixed header, `text-xl` semibold |
| **Savings label 1** | `已存金额` | Current Savings | Above input |
| **Savings label 2** | `目标金额` | Savings Target | Above input |
| **Progress percentage** | `{pct}%` | e.g., 45% | Centered in progress bar |
| **Empty state heading** | `财神在此，请问何处要花冤枉钱？` | Wealth God here. Where do you want to waste money? | Centered in empty chat |
| **Empty state example** | `试试：我想花 800 买个盲盒` | Try: I want to spend 800 on a blind box | Clickable chip below heading |
| **Tool status 1** | `⚡ 财神正在掐指一算…` | Wealth God is calculating... | Status line, animate-pulse |
| **Tool status 2** | `📊 正在计算影响…` | Calculating impact... | Status line after 2: arrives |
| **Input placeholder** | `试试：我想花 800 买个盲盒` | Try: I want to spend 800 on a blind box | Input field |
| **Role label — user** | `用户` | User | Above user messages |
| **Role label — assistant** | `财神` | Wealth God | Above assistant messages |
| **Error state banner** | `⚠ 财神系统故障，请稍后再试。` | Wealth God system error, please try again. | Red banner above input |
| **Error state button** | `重试` | Retry | Inline in error banner |
| **Stop button** | `■ 停止` | Stop | During streaming |
| **Send button** | `→` or `发送` | Send | Not streaming |
| **Approve verdict marker** | `【批准】` | [APPROVED] | Detect in first line to trigger green border |
| **Reject verdict marker** | `【拒绝】` | [REJECTED] | Detect in first line to trigger red border |

**All chat content (verdicts, tool results) is generated by the backend and streamed. Frontend only renders and applies formatting based on verdict markers.**

**Sources:** D-05 through D-23

---

## Integration Contract with Backend

### useChat Configuration

- **Hook:** `useChat` from `ai` package (v4.x)
- **API endpoint:** `process.env.NEXT_PUBLIC_API_URL + "/api/chat"`
- **Body shape:** Must match backend ChatRequest:
  ```json
  {
    "messages": [{"role": "user|assistant", "content": "..."}],
    "savings": <float>,
    "target": <float>
  }
  ```
- **Request body option:** Use `body` property in useChat config to include `savings` and `target` from React state

### Data Channel (2:)

- **Callback:** `onData` option on useChat
- **Payload:** Array-wrapped JSON from `2:` channel
- **Parse:** Last element of `useChat.data[]` as:
  ```json
  {
    "new_savings": <float>,
    "progress_pct": <float>,
    "delta": <float>
  }
  ```
- **Action:** Update React state `savings` and trigger progress bar animation

### Stop & Retry

- **Stop:** Call `useChat.stop()` during streaming
- **Retry (error):** Call `useChat.reload()`

**Sources:** D-11, D-12, STATE.md § Accumulated Context

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | None | Not applicable — no shadcn used |
| Tailwind CSS | Built-in utilities only | No third-party blocks |

**No third-party registries or unsafe component imports. All UI built from Tailwind v4 utilities and standard HTML/React.**

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending (awaiting gsd-ui-checker)

---

## Research Summary

**Pre-populated from:**
- CONTEXT.md (02-CONTEXT.md) — 23 implementation decisions (D-01 to D-23)
- REQUIREMENTS.md — 13 Phase 2 requirements (CHAT-01 through CHAT-07, SAVINGS-01 through SAVINGS-03, PROGRESS-01 through PROGRESS-03)
- CLAUDE.md — Technology stack (Next.js 16, ai@^4, Tailwind v4)
- STATE.md — Locked decisions (SSE format, useChat contract)

**No third-party research required.** All decisions pre-determined by upstream phases or made during CONTEXT discovery (Claude's discretion section is fully filled by the discuss phase).

**No ambiguities remaining.** All visual contracts, spacing, typography, color, and copywriting are fully specified. Implementation can proceed directly from this contract.

---

*UI-SPEC created: 2026-04-18*
*Phase: 02-frontend*
*Status: draft — awaiting gsd-ui-checker verification*
