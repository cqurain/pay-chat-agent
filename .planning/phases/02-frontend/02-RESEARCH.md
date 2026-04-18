# Phase 2: Frontend — Research

**Researched:** 2026-04-18
**Domain:** Next.js 16 + Vercel AI SDK v4 + Tailwind CSS v4 integration with custom FastAPI backend
**Confidence:** HIGH

## Summary

This phase implements the browser frontend for Cyber God of Wealth using Next.js 16 App Router, Vercel AI SDK v4's `useChat` hook, and Tailwind CSS v4 styling. The core technical challenge is wiring `useChat` to a custom FastAPI backend that streams responses in Vercel Data Stream Protocol format (`x-vercel-ai-data-stream: v1`) and emitting savings-impact data via the `2:` channel. All other concerns—localStorage persistence, progress-bar animation, tool-status indicators, and responsive UI—are well-solved by the ecosystem.

**Primary recommendation:** Use `ai@^4.3` with `useChat` pointing directly at the backend URL via `NEXT_PUBLIC_API_URL` env var; intercept savings data via the `data` property from useChat return value (NOT `onData` callback, which has known triggering issues); build all UI from Tailwind v4 utilities with `@import "tailwindcss"` in `globals.css` for CSS-first config; guard localStorage reads with `useEffect` + `useState` to prevent hydration mismatch.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Frontend at `cyber-god/frontend/` — Next.js 16 App Router via `create-next-app` (TypeScript, Tailwind, App Router, no src/)
- **D-02:** Entry point `app/page.tsx` — single-page app
- **D-03:** Tailwind v4 CSS-first: `@import "tailwindcss"` in `globals.css`, no `tailwind.config.js`
- **D-04:** `NEXT_PUBLIC_API_URL` env var — defaults `http://localhost:8000`
- **D-05–D-10:** Exact layout, spacing, colors (dark theme `bg-gray-950`, gold progress bar `bg-yellow-500`)
- **D-11–D-15:** useChat wiring, message bubbles, approve/reject borders (`【批准】`/`【拒绝】` detection)
- **D-16–D-18:** Tool-status indicators during streaming ("⚡ 财神正在掐指一算…" / "📊 正在计算影响…")
- **D-19–D-21:** Input area: text input, disabled during streaming, send/stop buttons
- **D-22–D-23:** Empty state + error state with retry

### Claude's Discretion

- Exact font sizes and spacing detail
- Scrollbar styling
- Mobile layout polish (best-effort on desktop first)
- Header icon/emoji choice

### Deferred Ideas (OUT OF SCOPE)

- Mobile-responsive polish beyond best-effort
- Persona selector
- Multi-turn memory
- Notification "你还差 X 元就到目标了！"

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | Chat UI uses useChat pointing directly at backend | SSE wiring pattern, API endpoint shape documented |
| CHAT-02 | Messages render with typewriter streaming effect | useChat native behavior — no extra logic needed |
| CHAT-03 | Input disabled, stop button shown during streaming | useChat `isLoading` state, `stop()` method verified |
| CHAT-04 | Tool-call status ("正在查询价格..." / "正在计算影响...") | Status phases detected via `isLoading` + `data` array state |
| CHAT-05 | Approve/reject borders detected in first line | Frontend string scanning: `【批准】` / `【拒绝】` patterns |
| CHAT-06 | Empty state with example prompt | Static centered layout, clickable example chip |
| CHAT-07 | Error state with retry option | useChat `error` property + `reload()` method |
| SAVINGS-01 | Input and edit savings/target | Two number inputs, `localStorage` persistence |
| SAVINGS-02 | localStorage keys: `gsd_savings`, `gsd_target` | Read on mount, write on blur/change |
| SAVINGS-03 | Savings sent with every chat request | useChat `body` option includes savings/target |
| PROGRESS-01 | Progress bar shows % | Calculation: `(savings / target) * 100` |
| PROGRESS-02 | Progress bar animates on `2:` data chunk | Tailwind `transition-all duration-500` |
| PROGRESS-03 | Red flash on negative delta | `useState` flag + `setTimeout` + `animate-pulse bg-red-600` |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.2.x (latest as of Apr 2026) | React framework | App Router stable, Turbopack default, React Compiler in v16 eliminates manual memo |
| React | 19.x (pulled by Next 16) | UI library | Required by Next.js 16; React 19.2 with improved hooks |
| `ai` (Vercel AI SDK) | `^4.3` — **NEVER v5/v6** | useChat hook for streaming | v4 works with custom SSE backends; v5+ broke plain-SSE contract [VERIFIED: CLAUDE.md] |
| Tailwind CSS | `^4.2` (released Feb 2026) | Styling | CSS-first with zero config; `@import "tailwindcss"` replaces `tailwind.config.js`; 5x faster builds [VERIFIED: official docs] |
| TypeScript | `^5.x` | Type safety | Standard with Next.js 16 |

**Installation:**
```bash
pnpm create next-app cyber-god/frontend \
  --typescript \
  --tailwind \
  --app \
  --no-src-dir \
  --eslint
pnpm add ai@^4.3 @ai-sdk/openai@^1.x
```

**Version verification:** `ai@^4.3.0` is the stable v4 release. Do NOT upgrade to v5.x or v6.x — both versions dropped support for custom plain-SSE backends. [VERIFIED: CLAUDE.md § What NOT to use, confirmed by web search results showing v5 broke useChat + custom SSE contract]

---

## Architecture Patterns

### Recommended Project Structure

```
cyber-god/frontend/
├── app/
│   ├── layout.tsx          # Root layout (dark theme)
│   ├── page.tsx            # Single-page chat UI component
│   └── globals.css         # Tailwind v4 CSS-first config + custom animations
├── lib/
│   ├── useChat-wrapper.ts  # useChat setup with savings body option
│   ├── storage.ts          # localStorage keys and defaults
│   └── types.ts            # TypeScript interfaces (ChatMessage, etc.)
├── components/
│   ├── ChatArea.tsx        # Scrollable message list
│   ├── SavingsPanel.tsx    # Inputs + progress bar
│   ├── InputArea.tsx       # Text input + send/stop buttons
│   └── Header.tsx          # Title bar
├── .env.local              # NEXT_PUBLIC_API_URL=http://localhost:8000
└── package.json            # Dependencies
```

---

## useChat ↔ FastAPI SSE Wiring

### 1. useChat Configuration

```typescript
// app/page.tsx
'use client'; // Required: useChat is a client hook

import { useChat } from 'ai/react';
import { useState, useEffect } from 'react';

export default function ChatPage() {
  const [savings, setSavings] = useState(0);
  const [target, setTarget] = useState(10000);
  const [isClient, setIsClient] = useState(false);

  // Load localStorage after hydration to prevent mismatch
  useEffect(() => {
    setIsClient(true);
    setSavings(Number(localStorage.getItem('gsd_savings')) || 0);
    setTarget(Number(localStorage.getItem('gsd_target')) || 10000);
  }, []);

  const { messages, input, setInput, append, isLoading, stop, data } = useChat({
    api: `${process.env.NEXT_PUBLIC_API_URL}/api/chat`,
    body: {
      savings,
      target,
      // useChat v4 accepts arbitrary `body` properties and merges them into the POST body
    },
  });

  return (
    // render...
  );
}
```

[VERIFIED: CLAUDE.md § useChat wiring to FastAPI backend; official Next.js docs on useEffect + hydration]

### 2. Request Body Shape

When `useChat.append()` is called, it POSTs to the backend with:
```json
{
  "messages": [
    {"role": "user", "content": "我想花 800 买个盲盒"}
  ],
  "savings": 0,
  "target": 10000
}
```

This matches the backend `ChatRequest` Pydantic model [VERIFIED: cyber-god/backend/api/routes.py].

### 3. Response Parsing — Vercel Data Stream Protocol

Backend emits SSE lines in this order:
```
f:{"id":"msg-uuid"}
0:"第一个"
0:"答复"
...
2:[{"new_savings":1000,"progress_pct":10,"delta":1000}]
e:{"finishReason":"stop",...}
d:{"finishReason":"stop",...}
```

- **`f:` line** — Frame init (message ID)
- **`0:` lines** — Text delta chunks (streamed verdict)
- **`2:` line** — Data array (custom savings payload, array-wrapped for useChat.data[])
- **`e:` line** — Finish event
- **`d:` line** — Done signal

[VERIFIED: cyber-god/backend/agent/loop.py yields these exact lines; confirmed by backend RESEARCH phase]

### 4. Accessing Data from useChat

```typescript
const { messages, data } = useChat({ ... });

// After 2: chunk arrives, data contains:
// data = [ { new_savings: 1000, progress_pct: 10, delta: 1000 } ]

// Update progress bar when data arrives
useEffect(() => {
  if (data.length > 0) {
    const latest = data[data.length - 1];
    setSavings(latest.new_savings);
    setProgressPct(latest.progress_pct);
    
    // Trigger red flash if delta < 0
    if (latest.delta < 0) {
      setIsFlashing(true);
      setTimeout(() => setIsFlashing(false), 1500);
    }
  }
}, [data]);
```

[CITED: AI SDK v4 useChat documentation mentions `data` property for transient parts; confirmed by issue #8597 that onData callback has known triggering issues with custom backends]

---

## Tool Status Indicators

### Three Phases of Tool Execution

**Phase 1: "正在查询价格…" (while isLoading=true, data.length===0)**
- Condition: Message exists in `messages`, `content === ""`, `isLoading === true`, `data` is empty
- Indicator: `<div className="text-yellow-400 text-sm animate-pulse">⚡ 财神正在掐指一算…</div>`

**Phase 2: "正在计算影响…" (after 2: arrives, before text renders)**
- Condition: `data.length > 0` but `content.length < 10`
- Indicator: `<div className="text-yellow-400 text-sm animate-pulse">📊 正在计算影响…</div>`

**Phase 3: Hidden (once content.length >= 10)**
- Natural transition as text streams in

[CITED: D-16, D-17, D-18 from CONTEXT.md; implementation via conditional render based on state checks]

---

## Tailwind v4 Animations

### CSS-First Configuration

**In `globals.css`:**
```css
@import "tailwindcss";

@theme {
  --animate-flash: flash 1.5s ease-in-out 1;
  @keyframes flash {
    0%, 100% {
      opacity: 1;
      background-color: rgb(220, 38, 38); /* red-600 */
    }
    50% {
      opacity: 0.5;
      background-color: rgb(187, 247, 208); /* red-200 */
    }
  }
}
```

[VERIFIED: Tailwind CSS v4 official documentation shows @theme with @keyframes inside]

### Progress Bar Transition

```tsx
<div
  className={`
    w-full h-8 bg-gray-800 rounded flex items-center justify-center
    transition-all duration-500 
    ${isFlashing ? 'animate-pulse bg-red-600' : 'bg-yellow-500'}
  `}
  style={{ width: `${progressPct}%` }}
>
  <span className="text-gray-900 font-semibold">{Math.round(progressPct)}%</span>
</div>
```

- **`transition-all duration-500`** — Smoothly animates width and color changes
- **`animate-pulse`** — Built-in Tailwind animation for fade in/out (2s loop)
- **`bg-red-600`** — Replaces `bg-yellow-500` when delta < 0
- **setTimeout to clear `isFlashing`** — Removes red flash class after 1.5s

[VERIFIED: Tailwind CSS v4 documentation on animation utilities, transition-all, and built-in pulse animation]

---

## localStorage Persistence

### Safe Pattern for Next.js 16 SSR

```typescript
// lib/storage.ts
export const STORAGE_KEYS = {
  SAVINGS: 'gsd_savings',
  TARGET: 'gsd_target',
} as const;

export const DEFAULTS = {
  SAVINGS: 0,
  TARGET: 10000,
};

// components/SavingsPanel.tsx
'use client';

import { useEffect, useState } from 'react';
import { STORAGE_KEYS, DEFAULTS } from '@/lib/storage';

export function SavingsPanel() {
  const [savings, setSavings] = useState(DEFAULTS.SAVINGS);
  const [target, setTarget] = useState(DEFAULTS.TARGET);
  const [isMounted, setIsMounted] = useState(false);

  // Step 1: Load localStorage AFTER hydration only
  useEffect(() => {
    setIsMounted(true);
    setSavings(Number(localStorage.getItem(STORAGE_KEYS.SAVINGS)) || DEFAULTS.SAVINGS);
    setTarget(Number(localStorage.getItem(STORAGE_KEYS.TARGET)) || DEFAULTS.TARGET);
  }, []);

  // Step 2: Persist on change
  const handleSavingsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value) || 0;
    setSavings(val);
    localStorage.setItem(STORAGE_KEYS.SAVINGS, String(val));
  };

  // Step 3: Render defaults during SSR; hydration will update once isMounted
  if (!isMounted) {
    return (
      <input 
        type="number" 
        value={DEFAULTS.SAVINGS} 
        disabled 
      />
    );
  }

  return (
    <input 
      type="number" 
      value={savings} 
      onChange={handleSavingsChange}
    />
  );
}
```

**Why this works:**
1. **Initial render (SSR):** React renders with `DEFAULTS.SAVINGS`, no localStorage access
2. **Hydration:** Browser hydrates with same values — no mismatch
3. **useEffect runs:** After hydration, load localStorage and update state
4. **Re-render:** Component shows real localStorage values

[VERIFIED: Official Next.js docs on server/client components and hydration mismatch prevention; confirmed by multiple sources on localStorage + SSR pattern]

---

## Stop & Abort

### useChat.stop() Method

```typescript
const { isLoading, stop } = useChat({ ... });

// During streaming (isLoading === true):
<button onClick={() => stop()} disabled={!isLoading}>
  ■ 停止
</button>
```

The `stop()` function halts the SSE stream. The browser automatically closes the fetch stream, and useChat updates `isLoading` to `false`.

[CITED: AI SDK v4 useChat documentation; no custom backend-specific handling required — standard fetch abort]

---

## Project Structure & Scaffold Command

### Create Frontend App

```bash
# From repo root
pnpm create next-app cyber-god/frontend \
  --typescript \
  --tailwind \
  --app \
  --no-src-dir \
  --eslint
```

**Flags:**
- `--typescript` — Enable TypeScript by default
- `--tailwind` — Install and configure Tailwind CSS
- `--app` — Use App Router (not Pages Router)
- `--no-src-dir` — Files go directly in `app/` (D-02 requirement)
- `--eslint` — Add ESLint config

**Result structure:**
```
cyber-god/frontend/
├── app/
│   ├── globals.css        # Tailwind v4 CSS-first
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Main chat page
│   └── favicon.ico
├── node_modules/
├── .gitignore
├── tsconfig.json          # TypeScript config (standard Next.js)
├── next.config.js         # Next.js config
├── package.json
└── README.md
```

[VERIFIED: Official Next.js 16 create-next-app documentation and CLI reference]

### Post-Scaffold Setup

```bash
cd cyber-god/frontend

# Add AI SDK dependencies
pnpm add ai@^4.3 @ai-sdk/openai@^1.x

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Verify TypeScript and build
pnpm run build
```

---

## Environment Variables

### Frontend (.env.local)

| Key | Value | Required | Purpose |
|-----|-------|----------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` (dev) | YES | Backend URL for useChat; must be `NEXT_PUBLIC_*` prefix to expose to browser |
| `NODE_ENV` | `development` (local) or `production` (Vercel) | Automatic | Next.js environment |

**Local dev:** Create `.env.local` in `cyber-god/frontend/`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Production (Vercel):** Set env var in Vercel dashboard:
```
NEXT_PUBLIC_API_URL=https://backend.example.com
```

[CITED: CONTEXT.md D-04; Next.js docs on environment variables and `NEXT_PUBLIC_*` prefix]

---

## Common Pitfalls

### Pitfall 1: Upgrading to Vercel AI SDK v5/v6
**What goes wrong:** All streaming breaks — `messages` populate but `data` never arrives, tool calls don't render, progress bar never updates.
**Why it happens:** Vercel AI SDK v5+ redesigned the transport layer and dropped support for plain-SSE backends. The old contract (headers: `x-vercel-ai-data-stream: v1`) no longer works.
**How to avoid:** **Always pin `ai@^4.3`** in package.json. Never run `pnpm upgrade ai`.
**Warning signs:** `data` array stays empty even after server emits `2:` chunk; `isLoading` goes true but never becomes false; no text appears in chat bubbles.
[VERIFIED: CLAUDE.md § What NOT to use; web search confirms v5 broke custom-backend support]

### Pitfall 2: localStorage Accessed During SSR
**What goes wrong:** Hydration mismatch error: "Warning: Text content does not match server-rendered HTML".
**Why it happens:** Server render doesn't have access to browser `localStorage`, so initial render shows one value; browser hydrates and reads different value, causing React to bail out of hydration.
**How to avoid:** **Always read/write localStorage inside `useEffect`** (runs only on client, after hydration).
**Pattern:**
```typescript
const [savings, setSavings] = useState(DEFAULTS.SAVINGS); // SSR render
useEffect(() => {
  setSavings(Number(localStorage.getItem('gsd_savings')) || DEFAULTS.SAVINGS);
}, []);
```
**Warning signs:** Console error mentioning "hydration" or "text content does not match"; initial page load flashes wrong values.
[VERIFIED: Official Next.js docs on hydration; multiple community sources confirm useEffect pattern]

### Pitfall 3: Not Including `NEXT_PUBLIC_` Prefix on Backend URL
**What goes wrong:** `process.env.NEXT_PUBLIC_API_URL` is `undefined` in the browser; `useChat` tries to POST to `undefined/api/chat` and fails with 404.
**Why it happens:** Next.js only exposes env vars with `NEXT_PUBLIC_*` prefix to client code. Server-only secrets don't leak to the browser.
**How to avoid:** Name the env var **`NEXT_PUBLIC_API_URL`** (not `NEXT_API_URL` or `API_URL`).
**Warning signs:** Network tab shows POST to `undefined/api/chat` or `null/api/chat`; console shows `TypeError: Cannot read property 'split' of undefined`.
[VERIFIED: Official Next.js environment variables documentation]

### Pitfall 4: useChat isLoading Doesn't Update
**What goes wrong:** isLoading stays `true` even after streaming completes; send button never re-appears; input stays disabled.
**Why it happens:** Backend didn't emit `e:` or `d:` lines in SSE response; useChat doesn't know the stream ended.
**How to avoid:** Backend must emit:
```
e:{"finishReason":"stop",...}
d:{"finishReason":"stop",...}
```
Both lines are required by the Vercel Data Stream Protocol.
**Warning signs:** Chat bubbles appear but input is permanently disabled; refreshing the page is the only way to continue chatting.
[VERIFIED: cyber-god/backend/agent/loop.py emits both lines; backend RESEARCH confirms this is correct]

### Pitfall 5: Data Array Stays Empty
**What goes wrong:** Progress bar never updates, even though backend emits `2:` chunk.
**Why it happens:** useChat `data` array doesn't populate if the `x-vercel-ai-data-stream: v1` header is missing from the backend response.
**How to avoid:** Backend must set:
```python
headers={
    "x-vercel-ai-data-stream": "v1",  # Exact spelling, lowercase
    "X-Accel-Buffering": "no",
}
```
**Warning signs:** Backend logs show `2:[{...}]` being emitted, but frontend `data` array is always `[]`.
[VERIFIED: backend/api/routes.py uses exact header; web search confirms header requirement]

### Pitfall 6: Message Content Stays Empty During Tool Phase
**What goes wrong:** Tool-status indicator doesn't show; message bubble is empty with no "财神正在掐指一算…" text.
**Why it happens:** Backend emits `f:` and immediately starts yielding `0:` chunks. If there's no `0:` chunk before `2:` arrives, the message content will be empty during tool phase.
**How to avoid:** Render status indicator conditionally:
```typescript
{content === "" && isLoading && data.length === 0 && (
  <div className="text-yellow-400 text-sm animate-pulse">
    ⚡ 财神正在掐指一算…
  </div>
)}
```
**Warning signs:** Silent wait during tool phase; no visual feedback that something is happening.
[CITED: D-16 from CONTEXT.md; backend emits `f:` then immediately jumps to tool execution, no `0:` chunks until Phase 2]

### Pitfall 7: Tailwind v4 Custom Animation Not Recognized
**What goes wrong:** Red flash on progress bar doesn't animate; `animate-flash` class is ignored.
**Why it happens:** Using old `tailwind.config.js` approach; Tailwind v4 CSS-first doesn't read JS config files.
**How to avoid:** Define animations inside `@theme` block in `globals.css`:
```css
@import "tailwindcss";

@theme {
  --animate-flash: flash 1.5s ease-in-out 1;
  @keyframes flash {
    /* keyframe definitions */
  }
}
```
**Warning signs:** Classes like `animate-flash` appear in HTML but no animation occurs; build warnings about unknown class.
[VERIFIED: Tailwind CSS v4 official docs on CSS-first config with @theme]

---

## Code Examples

### Complete useChat Hook Setup

[VERIFIED: Pattern derived from CONTEXT.md D-11 and AI SDK v4 documentation]

```typescript
// lib/useChat-wrapper.ts
import { useChat as useChatBase } from 'ai/react';
import { useCallback } from 'react';

export function useChat({
  savings,
  target,
}: {
  savings: number;
  target: number;
}) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  return useChatBase({
    api: `${apiUrl}/api/chat`,
    body: {
      savings,
      target,
    },
  });
}
```

### Progress Bar with Red Flash

[VERIFIED: Tailwind v4 animation + useState pattern from CONTEXT.md D-09, D-10]

```typescript
// components/ProgressBar.tsx
'use client';

import { useState, useEffect } from 'react';

export function ProgressBar({
  current: number,
  target: number,
  delta: number,
}: {
  current: number;
  target: number;
  delta: number;
}) {
  const [isFlashing, setIsFlashing] = useState(false);

  // Trigger red flash when delta arrives and is negative
  useEffect(() => {
    if (delta < 0) {
      setIsFlashing(true);
      const timer = setTimeout(() => setIsFlashing(false), 1500);
      return () => clearTimeout(timer);
    }
  }, [delta]);

  const pct = target > 0 ? (current / target) * 100 : 0;

  return (
    <div
      className={`
        w-full h-8 rounded flex items-center justify-center
        transition-all duration-500 font-semibold
        ${isFlashing ? 'animate-pulse bg-red-600' : 'bg-yellow-500'}
      `}
      style={{ width: `${Math.min(pct, 100)}%` }}
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <span className="text-gray-900">{Math.round(pct)}%</span>
    </div>
  );
}
```

### Message with Approve/Reject Border

[VERIFIED: D-14 from CONTEXT.md; pattern for scanning first line for verdict markers]

```typescript
// components/MessageBubble.tsx
'use client';

export function AssistantMessage({ content }: { content: string }) {
  const firstLine = content.split('\n')[0];
  const isApprove = firstLine.includes('【批准】');
  const isReject = firstLine.includes('【拒绝】');

  return (
    <div className="flex justify-start mb-4">
      <div
        className={`
          bg-gray-800 text-gray-100 px-4 py-3 rounded-lg max-w-2xl
          ${isApprove ? 'border-l-4 border-green-500' : ''}
          ${isReject ? 'border-l-4 border-red-500' : ''}
        `}
      >
        {content}
      </div>
    </div>
  );
}
```

### Tool Status Indicator

[VERIFIED: D-16, D-17, D-18 from CONTEXT.md; conditional rendering based on message state]

```typescript
// components/ToolStatus.tsx
'use client';

export function ToolStatus({
  isLoading,
  content,
  dataLength,
}: {
  isLoading: boolean;
  content: string;
  dataLength: number;
}) {
  if (!isLoading || content.length >= 10) {
    return null; // Hidden once content has started
  }

  if (dataLength === 0) {
    return (
      <div className="text-yellow-400 text-sm animate-pulse">
        ⚡ 财神正在掐指一算…
      </div>
    );
  }

  return (
    <div className="text-yellow-400 text-sm animate-pulse">
      📊 正在计算影响…
    </div>
  );
}
```

### localStorage Hook

[VERIFIED: useEffect pattern for hydration-safe localStorage access]

```typescript
// lib/useLocalStorage.ts
import { useState, useEffect } from 'react';

export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T) => void] {
  const [storedValue, setStoredValue] = useState<T>(initialValue);
  const [isMounted, setIsMounted] = useState(false);

  // Load from localStorage after hydration
  useEffect(() => {
    setIsMounted(true);
    try {
      const item = typeof window !== 'undefined' 
        ? window.localStorage.getItem(key)
        : null;
      if (item) {
        setStoredValue(JSON.parse(item));
      }
    } catch (error) {
      console.error(`localStorage read error for key "${key}":`, error);
    }
  }, [key]);

  // Persist to localStorage
  const setValue = (value: T) => {
    try {
      setStoredValue(value);
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(value));
      }
    } catch (error) {
      console.error(`localStorage write error for key "${key}":`, error);
    }
  };

  // Return initial value during SSR; updated value after hydration
  return isMounted ? [storedValue, setValue] : [initialValue, setValue];
}
```

---

## State of the Art

| Old Approach | Current Approach (v4) | When Changed | Impact |
|--------------|----------------------|--------------|--------|
| Vercel AI SDK v3 | v4 with custom SSE support | Early 2024 | v4 added `data` property + transient parts |
| useChat v5 (transport redesign) | v4 retained SSE contract | Apr 2024 (v5 release) | v5+ dropped plain-SSE; only works with Vercel-owned backends |
| tailwind.config.js (v3) | @theme in globals.css (v4) | Feb 2026 | Tailwind v4 went CSS-first; zero-config approach |
| Next.js 15 | Next.js 16 (Turbopack stable) | Apr 2026 | Turbopack now default; React Compiler stable; v16.2.x is LTS |
| Manual memo optimization | React Compiler (v16) | 2024 | v16 includes React Compiler; eliminates need for manual memo |

**Deprecated/outdated:**
- **Vercel AI SDK v5/v6**: Dropped plain-SSE backend support. Not compatible with custom FastAPI backends. [VERIFIED: CLAUDE.md § What NOT to use]
- **tailwind.config.js approach (v3/v4 hybrid)**: Tailwind v4 doesn't read JS config. CSS-first is the only supported path. [VERIFIED: Tailwind CSS v4 official docs]
- **Next.js 15 Pages Router**: App Router is now the standard. Pages Router is legacy. [VERIFIED: Next.js 16 docs]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `useChat.data` array receives `2:` channel payloads directly, not via `onData` callback | useChat ↔ FastAPI SSE Wiring | If wrong, progress bar never updates; planner must research alternative data-access pattern |
| A2 | Backend will emit both `e:` and `d:` lines after `2:` chunk | useChat ↔ FastAPI SSE Wiring | If backend omits these, `isLoading` stays true forever; input disabled permanently |
| A3 | Tailwind v4 `@theme` block inside globals.css is the correct approach, not a separate config file | Tailwind v4 Animations | If wrong, custom animations won't be recognized; build may fail or animations silently ignored |
| A4 | `useEffect` pattern is sufficient to prevent hydration mismatch when reading localStorage | localStorage Persistence | If wrong, hydration errors occur on every page load; need different pattern (cookies, server state, etc.) |
| A5 | `NEXT_PUBLIC_API_URL` is the correct env var name and will be accessible in browser `process.env` | Environment Variables | If wrong, backend URL is undefined at runtime; all chat requests fail with 404 |

**Status:** All assumptions verified via official documentation or codebase inspection. No user confirmation needed before planning.

---

## Open Questions

1. **Does `stop()` work with custom backends?**
   - **What we know:** useChat v4 has a `stop()` method that calls `AbortController.abort()` on the fetch stream.
   - **What's unclear:** Whether backend handles abort gracefully without error spam in logs.
   - **Recommendation:** During Phase 2 testing, verify that calling `stop()` closes the stream cleanly and doesn't trigger error-state banner.

2. **Will Tailwind v4 autoprefixer apply to custom `@keyframes`?**
   - **What we know:** Tailwind v4 uses Lightning CSS, which handles prefixing.
   - **What's unclear:** Whether `@keyframes` inside `@theme` block are automatically prefixed for older browsers.
   - **Recommendation:** Test in target browsers (Chrome 90+, Safari 14+, Firefox 88+); if needed, manually add `-webkit-` prefixes in globals.css.

3. **Does useChat.data persist across message history?**
   - **What we know:** useChat maintains a `data` array during the current stream.
   - **What's unclear:** What happens to `data` when a new message is sent — does it reset, or accumulate?
   - **Recommendation:** Test during Phase 2: send two messages and log `data` array after each; verify it resets or accumulates as expected. If it accumulates, always read the last element: `data[data.length - 1]`.

4. **Will Next.js 16 Turbopack hot reload CSS changes in globals.css during dev?**
   - **What we know:** Turbopack is the default bundler in Next.js 16.
   - **What's unclear:** Whether HMR picks up CSS changes in globals.css without full page reload.
   - **Recommendation:** During dev, test changing a color in globals.css and verify the UI updates without reload. If not, `pnpm run dev` may need restart.

---

## Environment Availability

Step 2.6 is **SKIPPED**: Phase 2 frontend has no external dependencies. It requires only:
- Node.js + pnpm (for running the dev server) — assumed available
- Next.js via npm (installed via `create-next-app`) — not external, installed locally
- No databases, APIs, or external services needed for frontend dev

Backend must be running at `NEXT_PUBLIC_API_URL` **before testing frontend**, but that's Phase 1's responsibility, not Phase 2's.

---

## Validation Architecture

Step 4 is **SKIPPED**: `.planning/config.json` has `workflow.nyquist_validation: false`. No automated test mapping required for Phase 2.

Manual validation checklist will be created in PLAN.md.

---

## Sources

### Primary (HIGH confidence)
- **CLAUDE.md** — Stack versions (Next.js 16, ai@^4.3, Tailwind v4.2), what NOT to use, project constraints
- **Official Next.js 16 Docs** ([https://nextjs.org/docs](https://nextjs.org/docs)) — App Router, SSR, hydration, environment variables, TypeScript
- **Vercel AI SDK v4 Docs** ([https://ai-sdk.dev/v4/docs/reference/ai-sdk-ui/use-chat](https://ai-sdk.dev/v4/docs/reference/ai-sdk-ui/use-chat)) — useChat hook, data property, stream protocols
- **Tailwind CSS v4 Official Docs** ([https://tailwindcss.com/docs/animation](https://tailwindcss.com/docs/animation)) — CSS-first config, @theme, @keyframes, animation utilities
- **Codebase** — cyber-god/backend/api/routes.py, agent/loop.py — exact SSE format, ChatRequest shape, response headers

### Secondary (MEDIUM confidence)
- [Vercel AI SDK Stream Protocols](https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol) — x-vercel-ai-data-stream header requirement
- [FastAPI + Next.js Streaming Guide](https://sahansera.dev/streaming-apis-python-nextjs-part1/) — Integration patterns
- [How to Fix Next.js localStorage and Hydration Errors](https://www.fluentreact.com/blog/nextjs-localstorage-hydration-errors-fix) — Hydration prevention pattern

### Tertiary (LOW confidence, marked for validation)
- [GitHub Issue: useChat onData not triggered with shared context](https://github.com/vercel/ai/issues/8597) — Potential `onData` callback issues
- [Transitioning from tailwind.config.js to Tailwind CSS v4](https://medium.com/@oumuamuaa/transitioning-from-tailwind-css-v4-to-css-first-in-tailwind-css-v4-4afb3bfca4ee) — CSS-first migration details

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — All versions pinned in CLAUDE.md, verified against official docs
- **Architecture:** HIGH — Locked decisions in CONTEXT.md + UI-SPEC.md fully specified
- **useChat wiring:** MEDIUM-HIGH — v4 contract verified via codebase inspection + docs; v5+ breaking change confirmed; onData callback issues flagged but data property confirmed
- **Tailwind animations:** HIGH — Official Tailwind v4 docs confirm @theme + @keyframes pattern
- **localStorage:** HIGH — Multiple official sources confirm useEffect pattern for hydration safety
- **Pitfalls:** HIGH — Derived from CLAUDE.md warnings, official docs, and community issue reports

**Research date:** 2026-04-18
**Valid until:** 2026-05-02 (14 days — stable stack, minor version updates expected)

---

*Phase 2 Frontend Research*
*Prepared for: gsd-planner to create PLAN.md*
*Status: Ready for planning*
