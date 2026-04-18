---
phase: 02-frontend
plan: "01"
subsystem: ui
tags: [nextjs, react, tailwind, typescript, vercel-ai-sdk, localstorage]

# Dependency graph
requires: []
provides:
  - Next.js 16 App Router scaffold at cyber-god/frontend/
  - ai@^4.3 (Vercel AI SDK v4) installed
  - Tailwind v4 CSS-first config with flash-red @keyframes animation
  - lib/storage.ts with STORAGE_KEYS and DEFAULTS for localStorage
  - lib/types.ts with SavingsPayload, ChatMessage, ChatRequestBody interfaces
  - .env.local with NEXT_PUBLIC_API_URL=http://localhost:8000
affects: [02-02, 02-03]

# Tech tracking
tech-stack:
  added:
    - next@16.2.4
    - react@19.2.4
    - ai@^4.3.19 (Vercel AI SDK v4)
    - tailwindcss@^4.2 (CSS-first, @import "tailwindcss")
    - zod@^3.25 (peer dep for ai@4.3)
    - typescript@^5
  patterns:
    - Tailwind v4 CSS-first: @import "tailwindcss" + @theme block in globals.css
    - No tailwind.config.js — CSS-first approach only
    - System font stack applied globally via * selector in globals.css
    - Dark theme via Tailwind utilities on <body> (bg-gray-950 text-gray-100)

key-files:
  created:
    - cyber-god/frontend/package.json
    - cyber-god/frontend/.env.local.example
    - cyber-god/frontend/lib/storage.ts
    - cyber-god/frontend/lib/types.ts
    - cyber-god/frontend/app/globals.css (replaced scaffold default)
    - cyber-god/frontend/app/layout.tsx (replaced scaffold default)
  modified: []

key-decisions:
  - "ai@^4.3 pinned — NOT v5/v6 which break custom FastAPI SSE backend contract"
  - "zod@^3 added to resolve peer dep conflict with ai@4.3 (scaffold installs zod@4 by default)"
  - "tailwind.config.js deliberately absent — Tailwind v4 CSS-first uses @import in globals.css"
  - ".env.local gitignored (secret); .env.local.example tracked (template)"

patterns-established:
  - "Tailwind v4: @keyframes defined inside @theme block, not in JS config"
  - "Dark theme applied at body level via bg-gray-950 utility"
  - "lib/ directory holds shared TypeScript contracts consumed by all components"

requirements-completed: [CHAT-01]

# Metrics
duration: 8min
completed: 2026-04-18
---

# Phase 2 Plan 01: Frontend Scaffold Summary

**Next.js 16 App Router bootstrapped with ai@^4.3, Tailwind v4 CSS-first flash-red animation, and shared TypeScript contracts (SavingsPayload, STORAGE_KEYS) ready for downstream component imports**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-18T00:35:00Z
- **Completed:** 2026-04-18T00:43:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Next.js 16.2.4 scaffold at `cyber-god/frontend/` with App Router, TypeScript, Tailwind v4
- Installed `ai@^4.3.19` (Vercel AI SDK v4 — NOT v5/v6 per CLAUDE.md constraint)
- Replaced default `globals.css` with Tailwind v4 `@import "tailwindcss"` + `@theme { @keyframes flash-red }` for progress bar red flash
- Updated `layout.tsx` with dark theme (`bg-gray-950`), `lang="zh-CN"`, title "赛博财神爷"
- Created `lib/storage.ts` — exports `STORAGE_KEYS` (`gsd_savings`, `gsd_target`) and `DEFAULTS` (0, 10000)
- Created `lib/types.ts` — exports `SavingsPayload`, `ChatMessage`, `ChatRequestBody` matching backend Pydantic shapes exactly
- Created `.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Build passes: `pnpm run build` completes successfully with Next.js 16 + Tailwind v4

## Files Created/Modified

- `cyber-god/frontend/package.json` — ai@^4.3.19, next@16.2.4, zod@^3.25.76, tailwindcss@^4
- `cyber-god/frontend/.env.local.example` — backend URL template (committed; .env.local gitignored)
- `cyber-god/frontend/.gitignore` — added `!.env*.example` to allow example templates
- `cyber-god/frontend/app/globals.css` — Tailwind v4 CSS-first + flash-red keyframes + system font stack
- `cyber-god/frontend/app/layout.tsx` — dark theme, Chinese lang, metadata
- `cyber-god/frontend/lib/storage.ts` — localStorage contract
- `cyber-god/frontend/lib/types.ts` — TypeScript interfaces for backend SSE contract

## Decisions Made

- Pinned `ai@^4.3` — v5/v6 break the custom FastAPI SSE backend contract (per CLAUDE.md § What NOT to use)
- Added `zod@^3` as explicit dep — create-next-app installs zod@4 by default; ai@4.3 requires zod@^3.23.8
- Tailwind v4 CSS-first: no `tailwind.config.js` — `@import "tailwindcss"` + `@theme {}` in globals.css only
- `.env.local` gitignored by frontend `.gitignore` (`.env*` rule); `.env.local.example` unblocked via `!.env*.example`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added zod@^3 to resolve ai@4.3 peer dependency conflict**
- **Found during:** Task 1 (ai@^4.3 installation)
- **Issue:** create-next-app installs zod@4 by default; ai@4.3.19 requires `zod@^3.23.8` — pnpm reports unmet peer warning which causes build failures in some configurations
- **Fix:** `pnpm add zod@^3.25.76` explicitly pinned to v3 satisfying ai@4.3 peer requirement
- **Files modified:** `cyber-god/frontend/package.json`, `cyber-god/frontend/pnpm-lock.yaml`
- **Verification:** `pnpm run build` completes without peer dependency errors
- **Committed in:** 7de0836 (Task 1 commit)

**2. [Rule 3 - Blocking] Added `!.env*.example` negation to frontend .gitignore**
- **Found during:** Task 1 (staging .env.local.example)
- **Issue:** Frontend `.gitignore` has `.env*` which blocked `git add .env.local.example`
- **Fix:** Added `!.env*.example` negation rule so template files can be committed while secrets remain ignored
- **Files modified:** `cyber-god/frontend/.gitignore`
- **Verification:** `git add cyber-god/frontend/.env.local.example` succeeds without force flag
- **Committed in:** 7de0836 (Task 1 commit)

**3. [Rule 3 - Blocking] Ran `CI=true pnpm install` to fix @swc/helpers missing module error**
- **Found during:** Task 2 verification (pnpm run build)
- **Issue:** First `pnpm run build` failed with `Cannot find module '@swc/helpers/_/_interop_require_default'` — pnpm had the package in `.pnpm/` store but not symlinked into `node_modules/@swc/`
- **Fix:** Ran `CI=true pnpm install` to force clean reinstall without TTY prompt; subsequent build succeeded
- **Files modified:** None (no lockfile change; package resolution corrected)
- **Verification:** `pnpm run build` completes with "✓ Compiled successfully"

---

**Total deviations:** 3 auto-fixed (all Rule 3 - blocking issues)
**Impact on plan:** All fixes essential for build to pass. No scope creep.

## Known Stubs

None — this plan creates foundation files only (no UI components, no data wiring). All exported contracts (`SavingsPayload`, `STORAGE_KEYS`, `DEFAULTS`) are concrete values, not stubs.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary changes introduced. `.env.local` correctly gitignored (T-02-01 satisfied). `NEXT_PUBLIC_API_URL` intentionally public (T-02-03 accepted).

## Self-Check: PASSED

- `cyber-god/frontend/package.json` — FOUND
- `cyber-god/frontend/app/globals.css` — FOUND (contains `@import "tailwindcss"` and `flash-red`)
- `cyber-god/frontend/app/layout.tsx` — FOUND (contains `bg-gray-950`, `lang="zh-CN"`)
- `cyber-god/frontend/lib/storage.ts` — FOUND (exports `STORAGE_KEYS`, `DEFAULTS`)
- `cyber-god/frontend/lib/types.ts` — FOUND (exports `SavingsPayload`, `ChatMessage`, `ChatRequestBody`)
- `cyber-god/frontend/.env.local` — FOUND (gitignored, not committed)
- `cyber-god/frontend/.env.local.example` — FOUND (committed)
- Commit 7de0836 — FOUND
- Commit 1e1e471 — FOUND
- `pnpm run build` — PASSED

---

*Phase: 02-frontend*
*Plan: 01*
*Completed: 2026-04-18*
