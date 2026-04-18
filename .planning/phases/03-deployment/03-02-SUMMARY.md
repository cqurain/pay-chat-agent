---
phase: 03-deployment
plan: "02"
subsystem: infra
tags: [readme, docker, vercel, deployment, documentation]

requires:
  - phase: 03-deployment
    plan: "01"
    provides: "Dockerfile, docker-compose.yml, .env.example — referenced in README steps"

provides:
  - "README.md at repo root: complete bilingual deployment guide (Chinese + English)"
  - "Frontend Dockerfile + docker-compose.yml for self-hosted Next.js standalone"
  - "next.config.ts output: standalone for Docker-compatible build"
  - "Human-verified: Docker build succeeds, frontend chat streams without CORS errors"

affects: []

tech-stack:
  added: [docker-multi-stage-build, next-standalone]
  patterns:
    - "Next.js standalone output + multi-stage Dockerfile for minimal production image"
    - "NEXT_PUBLIC_API_URL as build ARG — baked at build time, requires rebuild on URL change"

key-files:
  created:
    - README.md
    - cyber-god/frontend/Dockerfile
    - cyber-god/frontend/docker-compose.yml
  modified:
    - cyber-god/frontend/next.config.ts

key-decisions:
  - "Self-hosted frontend via Docker instead of Vercel — user preference"
  - "output: standalone in next.config.ts — required for node server.js Docker entrypoint"
  - "Tsinghua PyPI mirror in backend Dockerfile — faster pip install on Chinese servers"
  - "NEXT_PUBLIC_API_URL passed as docker build ARG — allows different values per environment"

patterns-established:
  - "Frontend Docker: multi-stage (node:20-slim builder → runner), standalone output"

requirements-completed: [DEPLOY-01, DEPLOY-04]

duration: 30min
completed: "2026-04-19"
---

# Phase 03-02: README + Frontend Deployment Summary

**Bilingual README + self-hosted Next.js Docker packaging; full stack verified on remote server with Docker Compose**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-04-19
- **Tasks:** 2 (Task 1 auto + Task 2 human checkpoint)
- **Files modified:** 4

## Accomplishments
- README.md at repo root with 6 sections: bilingual headings, PowerShell local dev, Docker steps, Vercel steps, env var table, 5 gotcha items
- Frontend Dockerfile: multi-stage node:20-slim build with `output: standalone` and `NEXT_PUBLIC_API_URL` build ARG
- `next.config.ts` updated with `output: 'standalone'` for Docker-compatible server.js entrypoint
- Frontend `docker-compose.yml` in `cyber-god/frontend/` for independent frontend deployment
- Human checkpoint passed: Docker build succeeded, frontend chat streams token-by-token, no CORS errors

## Task Commits

1. **Task 1: Write README.md** — `1bf2d13` (feat(03-02): write repo-root README.md deployment guide)
2. **Task 2: Human checkpoint approved** — verified on 2026-04-19 (no code commit)
3. **Frontend Docker files** — `00b2843` (feat(03): add frontend Docker packaging and complete deployment config)

## Files Created/Modified
- `README.md` — Complete deployment guide; bilingual; Docker + Vercel steps; env var table
- `cyber-god/frontend/Dockerfile` — Multi-stage Next.js standalone build
- `cyber-god/frontend/docker-compose.yml` — Frontend service with NEXT_PUBLIC_API_URL build arg
- `cyber-god/frontend/next.config.ts` — Added `output: 'standalone'`

## Decisions Made
- User opted for self-hosted Docker frontend instead of Vercel deployment
- `NEXT_PUBLIC_API_URL` passed as `ARG` (not hardcoded) — allows overriding per deploy without changing the Dockerfile

## Deviations from Plan
- Vercel deployment replaced with self-hosted Docker frontend — user decision during checkpoint
- Backend Dockerfile updated with Tsinghua PyPI mirror for faster builds on Chinese servers

## Issues Encountered
- Intermittent "财神系统故障" on first deployment — resolved after correcting `ALLOWED_ORIGINS` to include frontend IP and verifying `NEXT_PUBLIC_API_URL` points to server IP (not localhost)

## Next Phase Readiness
- All Phase 3 requirements met (DEPLOY-01 through DEPLOY-04)
- Full stack running on remote server via Docker Compose
- No further phases planned for v1.0 milestone

---
*Phase: 03-deployment*
*Completed: 2026-04-19*
