---
phase: 02-frontend
plan: "02"
subsystem: ui
tags: [nextjs, react, tailwind, typescript, vercel-ai-sdk, localstorage, progress-bar, savings-panel]

# Dependency graph
requires:
  - 02-01 (Next.js scaffold, ai@^4.3, Tailwind v4 flash-red keyframes, lib/storage.ts, lib/types.ts)
provides:
  - Header component (fixed 56px, 赛博财神爷 title)
  - SavingsPanel component (两 number inputs, localStorage persistence via STORAGE_KEYS)
  - ProgressBar component (gold fill, transition-all, red flash on delta < 0)
  - page.tsx complete savings/progress state machine (savings+target in React state, useChat body wired, chatData bridge)
affects:
  - 02-03 (ChatArea + InputArea will be inserted into page.tsx main section)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SavingsPayload cast via 'as unknown' before 'as SavingsPayload' to satisfy TypeScript strict JSONValue overlap check"
    - "isMounted guard in SavingsPanel prevents SSR/client hydration mismatch on localStorage reads"
    - "prevDelta tracking in ProgressBar prevents stale delta re-triggering flash on parent re-renders"
    - "NEXT_PUBLIC_API_URL ?? fallback prevents undefined/api/chat when .env.local missing"

key-files:
  created:
    - cyber-god/frontend/components/Header.tsx
    - cyber-god/frontend/components/SavingsPanel.tsx
    - cyber-god/frontend/components/ProgressBar.tsx
  modified:
    - cyber-god/frontend/app/page.tsx

key-decisions:
  - "Cast chatData element via 'as unknown' first — TypeScript JSONValue type does not overlap SavingsPayload directly"
  - "ProgressBar tracks prevDelta to avoid re-flashing when parent re-renders with same delta value"
  - "SavingsPanel lifts state via props (onSavingsChange/onTargetChange) — page.tsx owns the source of truth for useChat body"

requirements-completed: [SAVINGS-01, SAVINGS-02, SAVINGS-03, PROGRESS-01, PROGRESS-02, PROGRESS-03]

# Metrics
duration: 17min
completed: 2026-04-18
---

# Phase 2 Plan 02: Savings Panel, Progress Bar, and page.tsx Wiring Summary

**Header (56px), SavingsPanel (两 number inputs + gsd_savings/gsd_target localStorage persistence), ProgressBar (gold fill + 1.5s red flash on delta < 0), and page.tsx state machine (savings+target in useChat body, chatData bridge to setSavings/setDelta) — all built and TypeScript build passes**

## Performance

- **Duration:** ~17 min
- **Started:** 2026-04-18T05:35:00Z
- **Completed:** 2026-04-18T05:52:02Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `components/Header.tsx` — Fixed 56px header (`h-14`) with title `赛博财神爷` and subtitle `你的AI财务顾问`, dark background `bg-gray-950`, server component (no `'use client'`)
- `components/SavingsPanel.tsx` — Two labeled number inputs (`已存金额` / `目标金额`), reads localStorage after hydration via `isMounted` guard, writes on change. Uses `STORAGE_KEYS.SAVINGS` / `STORAGE_KEYS.TARGET` (resolves to `gsd_savings` / `gsd_target`). Props lift state to page.tsx. Input guarded with `Math.max(0, ...)` for T-02-06 DoS mitigation.
- `components/ProgressBar.tsx` — Gold (`bg-yellow-500`) fill with `transition-all duration-500`. Flashes red via `animate-[flash-red_1.5s_ease-in-out_1]` + `bg-red-600` for 1500ms when `delta < 0`. Tracks `prevDelta` to prevent stale re-triggers. `role="progressbar"` with aria attributes for accessibility. Shows `%` inside bar when `displayPct > 5`, outside otherwise.
- `app/page.tsx` — Complete rewrite: `useChat` from `ai/react` with `api: NEXT_PUBLIC_API_URL ?? localhost:8000` and `body: { savings, target }`. `chatData` useEffect validates shape (cast via `unknown` for TypeScript safety, checks `typeof number && !isNaN`) before calling `setSavings` / `setDelta`. Layout skeleton: Header → SavingsPanel → ProgressBar → main (Plan 03 placeholder).
- `pnpm run build` passes with zero TypeScript errors after fixing JSONValue→SavingsPayload cast.

## Files Created/Modified

- `cyber-god/frontend/components/Header.tsx` — created (commit e42634b)
- `cyber-god/frontend/components/SavingsPanel.tsx` — created (commit e42634b)
- `cyber-god/frontend/components/ProgressBar.tsx` — created (commit e42634b)
- `cyber-god/frontend/app/page.tsx` — replaced scaffold with state machine (commit 66ad2ef)

## Decisions Made

- Cast `chatData` element as `unknown` before `SavingsPayload` — TypeScript `JSONValue` union type (from ai@4.3) does not overlap with the custom interface directly; `as unknown as SavingsPayload` is the correct pattern
- `prevDelta` state in ProgressBar — without tracking previous delta value, every parent re-render with the same `delta` prop would re-trigger the flash (same `delta` reference in useEffect deps causes spurious re-runs)
- State ownership in page.tsx — `savings` and `target` live in page.tsx (not SavingsPanel) so `useChat` body always has the authoritative value; SavingsPanel receives them as props and calls lift functions on change

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript JSONValue→SavingsPayload cast error**
- **Found during:** Task 2 verification (`pnpm run build`)
- **Issue:** `raw as SavingsPayload` failed TypeScript strict check because `JSONValue` type (from ai@4.3 SDK) does not sufficiently overlap with `SavingsPayload` interface — TypeScript error: "Conversion of type '...' to type 'SavingsPayload' may be a mistake"
- **Fix:** Changed `chatData[chatData.length - 1]` to `chatData[chatData.length - 1] as unknown`, allowing the subsequent `as SavingsPayload` cast to work correctly
- **Files modified:** `cyber-god/frontend/app/page.tsx` (line 58)
- **Commit:** 66ad2ef (same task commit — fixed inline before committing)

## Known Stubs

- `<main>` in `page.tsx` contains a placeholder `<div>Chat area (Plan 03)</div>` — intentional skeleton for Plan 03 to replace with ChatArea + InputArea components. This does not prevent Plan 02's goal (savings panel + progress bar functional). Plan 03 resolves this stub.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced. All threat mitigations from the plan's threat model implemented:
- T-02-05: chatData payload validated (`typeof number && !isNaN`) before `setSavings`
- T-02-06: `Math.max(0, Number(val) || 0)` in SavingsPanel handlers prevents negative/NaN input
- T-02-07: localStorage gsd_savings/gsd_target accepted (per-origin, non-sensitive planning data)
- T-02-08: Progress bar visual manipulation accepted (local JS execution required)

## Self-Check: PASSED

- `cyber-god/frontend/components/Header.tsx` — FOUND (contains `赛博财神爷`, `h-14`)
- `cyber-god/frontend/components/SavingsPanel.tsx` — FOUND (contains `STORAGE_KEYS.SAVINGS`, `已存金额`, `目标金额`, `isMounted`, `localStorage.setItem`)
- `cyber-god/frontend/components/ProgressBar.tsx` — FOUND (contains `isFlashing`, `flash-red`, `delta < 0`, `setTimeout(...1500)`, `role="progressbar"`, `transition-all duration-500`)
- `cyber-god/frontend/app/page.tsx` — FOUND (contains `useChat`, `NEXT_PUBLIC_API_URL`, `body: {`, `chatData`, `setSavings`, `setDelta`, `Header`, `SavingsPanel`, `ProgressBar`, `h-screen`)
- Commit e42634b — FOUND (3 component files)
- Commit 66ad2ef — FOUND (page.tsx wiring)
- `pnpm run build` — PASSED (zero TypeScript errors)

---

*Phase: 02-frontend*
*Plan: 02*
*Completed: 2026-04-18*
