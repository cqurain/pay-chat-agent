---
phase: 03-deployment
plan: 01
subsystem: infra
tags: [docker, dockerfile, docker-compose, fastapi, mcp, python3]

# Dependency graph
requires:
  - phase: 02-frontend
    provides: "Completed frontend + backend with working API and MCP subprocess"
provides:
  - "Dockerfile for FastAPI + MCP backend (python:3.12-slim, PYTHONUNBUFFERED=1)"
  - "docker-compose.yml for single-command startup with env_file secret injection"
  - ".dockerignore preventing .env and __pycache__ from entering image layers"
  - ".env.example documenting the three required env vars with placeholder values"
  - "Fixed MCP subprocess command (python -> python3) for correct resolution in container"
affects: [03-deployment]

# Tech tracking
tech-stack:
  added: [Docker, docker-compose v2]
  patterns: [env_file pattern for secret injection, multi-stage-friendly layer ordering (requirements before code)]

key-files:
  created:
    - cyber-god/backend/Dockerfile
    - cyber-god/backend/docker-compose.yml
    - cyber-god/backend/.dockerignore
    - cyber-god/backend/.env.example
  modified:
    - cyber-god/backend/main.py

key-decisions:
  - "python3 in StdioServerParameters.command — python:3.12-slim only has python3 in PATH, not python"
  - "env_file directive in docker-compose.yml — secrets injected from host .env, never baked into image layers"
  - "PYTHONUNBUFFERED=1 as Docker ENV — prevents MCP stdio subprocess from hanging due to block buffering in non-TTY"

patterns-established:
  - "Dockerfile pattern: ENV before WORKDIR, requirements COPY before code COPY for layer cache efficiency"
  - ".dockerignore pattern: exclude .env, .env.*, __pycache__, .git from image build context"

requirements-completed: [DEPLOY-02, DEPLOY-03]

# Metrics
duration: 10min
completed: 2026-04-18
---

# Phase 3 Plan 1: Docker Backend Packaging Summary

**Dockerfile + docker-compose.yml for FastAPI/MCP backend with env_file secret injection and python3 subprocess fix**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-18T00:00:00Z
- **Completed:** 2026-04-18
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created Dockerfile with FROM python:3.12-slim, PYTHONUNBUFFERED=1, and uvicorn CMD — enabling Docker container startup
- Created docker-compose.yml with env_file directive — anyone can `docker compose up -d` after filling .env
- Created .dockerignore excluding .env and __pycache__ — secrets never enter image layers (mitigates T-03-01)
- Created .env.example with placeholder values for ZHIPU_API_KEY, GLM_MODEL, ALLOWED_ORIGINS
- Fixed MCP subprocess command from `python` to `python3` — resolves FileNotFoundError in python:3.12-slim container

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Dockerfile, docker-compose.yml, .dockerignore, and .env.example** - `60e8fa6` (feat)
2. **Task 2: Fix MCP subprocess command in main.py to use python3** - `57c0c93` (fix)

**Plan metadata:** (docs commit pending)

## Files Created/Modified
- `cyber-god/backend/Dockerfile` - Container build instructions; python:3.12-slim base, PYTHONUNBUFFERED=1, uvicorn CMD
- `cyber-god/backend/docker-compose.yml` - Single-command startup; ports 8000:8000, env_file, restart unless-stopped
- `cyber-god/backend/.dockerignore` - Excludes .env, .env.*, __pycache__, .git, .venv from image build context
- `cyber-god/backend/.env.example` - Documents ZHIPU_API_KEY, GLM_MODEL, ALLOWED_ORIGINS with safe placeholder values
- `cyber-god/backend/main.py` - Changed StdioServerParameters command from "python" to "python3"

## Decisions Made
- `python3` instead of `python` in StdioServerParameters: `python:3.12-slim` only includes `python3` in PATH by default. Using `python` would raise FileNotFoundError when the MCP server subprocess is spawned at container startup. `python3` works in both the Docker container and local venv environments.
- `env_file` pattern over `environment:` inline values: Keeps secrets out of docker-compose.yml (which is committed), satisfies T-03-01 threat mitigation.
- `PYTHONUNBUFFERED=1` as Docker ENV (not ARG): Persists into the running container environment so the MCP stdio subprocess never blocks on stdout buffering (mitigates T-03-04).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
**Before running `docker compose up -d`**, the user must:
1. Copy `.env.example` to `.env` in `cyber-god/backend/`
2. Set `ZHIPU_API_KEY` to their actual Zhipu AI API key from open.bigmodel.cn
3. Optionally set `GLM_MODEL` (default: `glm-4-flash`) and `ALLOWED_ORIGINS` (default: `http://localhost:3000`)

## Next Phase Readiness
- Backend is Docker-ready; `docker compose up -d` in `cyber-god/backend/` starts the FastAPI server on port 8000
- Plan 03-02 (frontend Vercel deployment) can proceed independently — no dependencies on this plan's artifacts
- MCP subprocess will correctly resolve `python3` inside the container

## Threat Surface Scan
No new threat surface introduced beyond what was planned. T-03-01 (secrets in image layers) mitigated by .dockerignore. T-03-04 (MCP subprocess hang) mitigated by PYTHONUNBUFFERED=1.

---
*Phase: 03-deployment*
*Completed: 2026-04-18*

## Self-Check: PASSED

- FOUND: cyber-god/backend/Dockerfile
- FOUND: cyber-god/backend/docker-compose.yml
- FOUND: cyber-god/backend/.dockerignore
- FOUND: cyber-god/backend/.env.example
- FOUND: .planning/phases/03-deployment/03-01-SUMMARY.md
- FOUND: commit 60e8fa6 (Task 1)
- FOUND: commit 57c0c93 (Task 2)
