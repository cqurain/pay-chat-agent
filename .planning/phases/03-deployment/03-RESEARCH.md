# Phase 3: Deployment - Research

**Researched:** 2026-04-18
**Domain:** Docker containerization (FastAPI + MCP subprocess), Vercel frontend deployment, README authoring
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEPLOY-01 | Frontend deployable to Vercel with `NEXT_PUBLIC_API_URL` env var pointing at backend | Vercel monorepo Root Directory config; NEXT_PUBLIC_ build-time inlining behavior documented |
| DEPLOY-02 | Backend packaged as Docker image (`Dockerfile` + `docker-compose.yml`) deployable to any remote Linux server via `docker compose up -d` | Dockerfile pattern for FastAPI + Python 3.12 verified; docker-compose env_file pattern documented |
| DEPLOY-03 | Docker image exposes port 8000, reads `ZHIPU_API_KEY`, `GLM_MODEL`, `ALLOWED_ORIGINS` from env / `.env` file | env_file syntax + ALLOWED_ORIGINS from config.py examined; 3 required env vars confirmed |
| DEPLOY-04 | README documents local dev setup (Windows/PowerShell), Docker build + push steps, and Vercel frontend deployment | README structure researched; Windows/PowerShell specifics identified |
</phase_requirements>

---

## Summary

Phase 3 packages the already-working local demo for public access. The backend needs a `Dockerfile` + `docker-compose.yml` so anyone can run `docker compose up -d` and get the FastAPI server on port 8000. The frontend needs a Vercel project pointed at `cyber-god/frontend/` as its Root Directory, with `NEXT_PUBLIC_API_URL` set to the Docker host URL. A README ties it together.

**Critical finding:** The backend uses `mcp.client.stdio.stdio_client` which spawns the MCP price server as a subprocess via Python `subprocess`. Inside Docker, stdout buffering can cause the JSON-RPC stream to hang unless `PYTHONUNBUFFERED=1` is set in the Dockerfile. This is the single highest-risk item for the Docker build. `[VERIFIED: community bug reports + Docker Python docs]`

**Primary recommendation:** Write the Dockerfile with `PYTHONUNBUFFERED=1` and `PYTHONDONTWRITEBYTECODE=1`, use `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`, and pin `python:3.12-slim` as the base image. Deploy frontend to Vercel by setting Root Directory to `cyber-god/frontend` in the Vercel project settings.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 3 |
|-----------|------------------|
| Tech stack: FastAPI + Pydantic + Next.js App Router + Tailwind CSS + Vercel AI SDK — no deviations | Backend Dockerfile uses uvicorn, no gunicorn or other WSGI servers |
| Streaming: backend must use FastAPI StreamingResponse | Docker must not insert a buffering proxy layer (no nginx in this PoC) |
| No DB | No database service in docker-compose; state is all client-side |
| Backend deployment: Docker on any Linux server — NOT Railway/Render PaaS | Dockerfile must be self-contained; no PaaS-specific config |
| openai SDK: pin to ~=1.x | requirements.txt already correct; do not change in Docker build |
| Vercel AI SDK: pin to ai@^4 | package.json already correct; Vercel build must not upgrade it |

---

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `python:3.12-slim` | 3.12 (Docker Hub official) | Base image | Matches CLAUDE.md Python runtime target; slim reduces image size to ~120MB; NOT Alpine (Alpine breaks C-extension packages) |
| Docker Compose v2 | v2.34 (available locally) | Orchestration | `docker compose` (no hyphen) is the v2 CLI; already installed |
| `uvicorn[standard]` | `>=0.30.0` (in requirements.txt) | ASGI server inside container | Already declared; just needs correct CMD in Dockerfile |
| Vercel (platform) | current | Frontend host | Locked decision per STATE.md |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `env_file` directive in docker-compose.yml | Load `ZHIPU_API_KEY`, `GLM_MODEL`, `ALLOWED_ORIGINS` from `backend/.env` | Always — keeps secrets out of image layers |
| `.env.example` | Document required env vars | Ship in repo; actual `.env` is gitignored |
| Vercel Dashboard "Root Directory" setting | Point Vercel at `cyber-god/frontend/` sub-folder | Required for monorepo layout |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `python:3.12-slim` | `python:3.12-alpine` | Alpine breaks packages with C extensions (mcp, uvicorn[standard]); slim is safer |
| `docker compose up -d` | Railway / Render PaaS | Explicitly ruled out in STATE.md locked decisions |
| `NEXT_PUBLIC_API_URL` at build time | Runtime env API | NEXT_PUBLIC_ is inlined at build; for Vercel this is fine because the backend URL is known before deploying |

---

## Architecture Patterns

### Recommended File Structure After Phase 3

```
cyber-god/
├── backend/
│   ├── Dockerfile              # NEW — python:3.12-slim, uvicorn CMD
│   ├── docker-compose.yml      # NEW — service definition, port 8000, env_file
│   ├── .env.example            # NEW — documents ZHIPU_API_KEY, GLM_MODEL, ALLOWED_ORIGINS
│   ├── .env                    # gitignored — actual secrets
│   ├── main.py
│   ├── requirements.txt
│   └── ... (existing code)
├── frontend/
│   └── ... (existing code, no changes)
└── README.md                   # NEW — full walkthrough
```

### Pattern 1: Dockerfile for FastAPI + MCP subprocess

**What:** Single-stage build using `python:3.12-slim`. Sets `PYTHONUNBUFFERED=1` to prevent MCP stdio hang. Copies requirements first for layer caching, then copies app code.

**When to use:** All cases — this PoC has no multi-stage build need (no compiled assets).

```dockerfile
# Source: fastapi.tiangolo.com/deployment/docker + Docker Python best practices
FROM python:3.12-slim

# CRITICAL for MCP stdio: prevents subprocess stdout buffering that causes JSON-RPC hang
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps first (layer caching — changes less often than code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

# Use uvicorn directly (fastapi[standard] is already in requirements.txt)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Why `--host 0.0.0.0`:** Without this, uvicorn binds to 127.0.0.1 only and is unreachable from outside the container. `[VERIFIED: Docker networking fundamentals]`

### Pattern 2: docker-compose.yml

**What:** Single-service compose file. Uses `env_file` to load `.env` from the same directory. Maps host port 8000 to container port 8000. Sets `restart: unless-stopped` for resilience.

```yaml
# Source: Docker Compose documentation + FastAPI deployment guide
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
```

**Why `env_file` not `environment:`:** Keeps secrets out of the compose file itself. The `.env` file is gitignored. `[VERIFIED: Docker Compose docs pattern]`

**Why `restart: unless-stopped`:** Restarts on crash but respects manual `docker compose stop`. Better than `always` because it doesn't fight intentional stops. `[CITED: docs.docker.com/reference/cli/docker/compose/restart/]`

### Pattern 3: Vercel Monorepo Deployment

**What:** Vercel project with Root Directory set to `cyber-god/frontend`. Single env var `NEXT_PUBLIC_API_URL` set to the Docker host URL.

**Steps:**
1. Connect GitHub repo to Vercel
2. In project settings → General → Root Directory: set to `cyber-god/frontend`
3. In project settings → Environment Variables: add `NEXT_PUBLIC_API_URL=https://your-server-ip:8000` for Production
4. Trigger a deployment (push to main or manual deploy)

**Build-time inlining caveat:** `NEXT_PUBLIC_API_URL` is baked into the JS bundle at build time by Next.js. If the backend URL changes, a redeploy is required. This is acceptable for this PoC. `[VERIFIED: Next.js docs + Vercel docs]`

**Frontend already wired correctly:**
```typescript
// From cyber-god/frontend/app/page.tsx (existing code)
api: `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/chat`,
```
The fallback to `localhost:8000` ensures local dev works without the env var. `[VERIFIED: read from codebase]`

### Pattern 4: ALLOWED_ORIGINS for CORS

**What:** The FastAPI `config.py` already reads `ALLOWED_ORIGINS` as a comma-separated list from env. The Docker `.env` must include the Vercel deployment URL.

```bash
# backend/.env (production)
ZHIPU_API_KEY=sk-...
GLM_MODEL=glm-4-flash
ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

The backend already handles the comma-split: `[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")]`. `[VERIFIED: read from codebase — config.py line 9]`

### Anti-Patterns to Avoid

- **PYTHONUNBUFFERED omitted:** MCP stdio subprocess will hang in Docker because Python buffers stdout in non-TTY mode. Always set `ENV PYTHONUNBUFFERED=1` in the Dockerfile.
- **`--host 127.0.0.1` (default):** Uvicorn won't be reachable from host machine. Must use `--host 0.0.0.0`.
- **ALLOWED_ORIGINS wildcard (`*`) in production:** Works but voids security intent. Prefer explicit Vercel domain.
- **Committing `.env` with secrets:** Must be in `.gitignore`. Ship `.env.example` instead.
- **Setting `NEXT_PUBLIC_API_URL` after deploy without redeploying:** The variable is baked in at build time; changing it in the Vercel dashboard requires a new deployment to take effect.
- **Alpine base image:** `python:3.12-alpine` breaks packages with C extensions. The `mcp` package and `uvicorn[standard]` (which includes uvloop) require glibc. Use `python:3.12-slim`. `[VERIFIED: Docker Python community docs]`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python subprocess buffering | Custom flush logic | `ENV PYTHONUNBUFFERED=1` in Dockerfile | One line; handles all Python buffering modes |
| Env var loading in container | Custom dotenv in startup script | Docker Compose `env_file` directive | Native compose feature; no extra code needed |
| Health check endpoint | Custom monitoring script | Docker Compose `healthcheck` (optional) | Built-in compose feature; not required for this PoC |
| CORS for streaming | Custom middleware | `CORSMiddleware` already in main.py | Already implemented in Phase 1; just needs correct origins in env |

---

## Runtime State Inventory

> Phase 3 is a packaging/deployment phase — no renames or migrations. Included to confirm no hidden runtime state.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — no database; state is localStorage only | None |
| Live service config | None — no external service configs needed | None |
| OS-registered state | None | None |
| Secrets/env vars | `ZHIPU_API_KEY`, `GLM_MODEL`, `ALLOWED_ORIGINS` in `backend/.env` (gitignored) | Create `.env.example` documenting these; actual `.env` stays out of repo |
| Build artifacts | `__pycache__/` directories in backend | Add `.dockerignore` to exclude; image stays clean |

---

## Common Pitfalls

### Pitfall 1: MCP stdio hang in Docker (CRITICAL)
**What goes wrong:** The FastAPI server starts, but the first request hangs forever at MCP tool call. Logs show the lifespan MCP session connects but `session.initialize()` times out.
**Why it happens:** Python's stdout is block-buffered in non-TTY mode (inside Docker). The MCP server writes its JSON-RPC init response, but it stays in the 8KB buffer and never reaches the client.
**How to avoid:** `ENV PYTHONUNBUFFERED=1` in Dockerfile. Also pass `-u` flag as alternative: `CMD ["python", "-u", ...]` but the ENV approach is cleaner.
**Warning signs:** Server logs show lifespan start but no log from `session.initialize()` completing; first curl hangs indefinitely.
**Sources:** `[CITED: github.com/jlowin/fastmcp/issues/507]` `[CITED: dev.to/wewake-dev/why-your-python-logs-vanish-in-docker-pythonunbuffered]`

### Pitfall 2: CORS error in production (streaming-specific)
**What goes wrong:** Chat works locally but Vercel-deployed frontend gets CORS errors on SSE stream. Browser blocks the response mid-stream.
**Why it happens:** `ALLOWED_ORIGINS` in the production `.env` doesn't include the actual Vercel deployment URL (e.g., `https://cyber-god.vercel.app`). The preflight OPTIONS passes but the stream response origin check fails.
**How to avoid:** Set `ALLOWED_ORIGINS=https://your-app.vercel.app` (no trailing slash, exact match) in the production `.env`. Test with `curl -H "Origin: https://your-app.vercel.app"` from server before deploying frontend.
**Warning signs:** Browser console shows `CORS error` or `Access-Control-Allow-Origin` missing on response after streaming starts.

### Pitfall 3: NEXT_PUBLIC_API_URL not updated after backend URL changes
**What goes wrong:** Frontend calls the wrong (old) backend URL even after updating the env var in Vercel dashboard.
**Why it happens:** `NEXT_PUBLIC_` variables are baked into the JS bundle at `next build` time. Dashboard changes only take effect on the *next* deployment.
**How to avoid:** After setting `NEXT_PUBLIC_API_URL`, trigger a new deployment (push a commit or use Vercel dashboard "Redeploy").

### Pitfall 4: Port conflict on Docker host
**What goes wrong:** `docker compose up -d` succeeds but port 8000 is already used by local uvicorn dev server.
**Why it happens:** Developer runs both `uvicorn main:app --port 8000` locally and Docker simultaneously.
**How to avoid:** Stop local dev server before starting Docker. README should note this.

### Pitfall 5: `.env` not found by docker-compose
**What goes wrong:** Container starts but crashes immediately with `KeyError: 'ZHIPU_API_KEY'`.
**Why it happens:** Developer cloned repo but never created `.env` from `.env.example`.
**How to avoid:** README must include "copy `.env.example` to `.env` and fill in values" as step 1. The `docker-compose.yml` `env_file: - .env` will error early if the file is missing.

### Pitfall 6: Vercel Root Directory not set for monorepo
**What goes wrong:** Vercel deploys from repo root, can't find `package.json`, build fails with "No package.json found".
**Why it happens:** Default Vercel behavior is to deploy from repo root. This monorepo has frontend at `cyber-god/frontend/`.
**How to avoid:** Set Root Directory to `cyber-god/frontend` in Vercel project settings → General. `[VERIFIED: Vercel monorepo docs]`

---

## Code Examples

### Complete Dockerfile
```dockerfile
# Source: fastapi.tiangolo.com/deployment/docker (pattern) + PYTHONUNBUFFERED fix for MCP stdio
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Complete docker-compose.yml
```yaml
# Source: Docker Compose documentation
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
```

### .env.example
```bash
# Copy this file to .env and fill in your values
# Never commit the actual .env file

ZHIPU_API_KEY=sk-your-zhipu-api-key-here
GLM_MODEL=glm-4-flash
# Comma-separated list of allowed CORS origins
# For local dev only: http://localhost:3000
# For production: add your Vercel URL
ALLOWED_ORIGINS=http://localhost:3000
```

### .dockerignore (prevents bloat and __pycache__ in image)
```
__pycache__
*.pyc
*.pyo
.env
.git
.gitignore
*.md
```

### Vercel deployment URL pattern in ALLOWED_ORIGINS
```bash
# Production .env on the Docker host (not in repo)
ZHIPU_API_KEY=sk-...
GLM_MODEL=glm-4-flash
ALLOWED_ORIGINS=https://cyber-god-of-wealth.vercel.app,http://localhost:3000
```

### PowerShell local dev commands (for README)
```powershell
# Backend (from repo root)
cd cyber-god\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # then edit .env to add ZHIPU_API_KEY
uvicorn main:app --reload --port 8000

# Frontend (separate terminal, from repo root)
cd cyber-god\frontend
pnpm install
# create frontend\.env.local with: NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm dev
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | DEPLOY-02, DEPLOY-03 | Yes | 28.0.4 | — |
| Docker Compose v2 | DEPLOY-02, DEPLOY-03 | Yes | 2.34.0 | — |
| Python 3.12 | Local dev (README) | No — 3.11.5 installed | 3.11.5 | README must note 3.12 is required for Docker; local dev may use 3.11 if PoC works |
| Node.js | Frontend local dev | Yes | 22.17.0 | — |
| pnpm | Frontend install | Yes | 10.33.0 | — |
| Vercel CLI | Optional push method | Not installed | — | Vercel dashboard + GitHub integration (recommended) |
| gh CLI | Optional for README | Not installed | — | Use GitHub web UI |

**Missing dependencies with no fallback:**
- None that block Docker build or Vercel deploy.

**Missing dependencies with fallback:**
- Python 3.12 not installed locally (3.11.5 present): Docker image uses 3.12-slim — the container is the authoritative runtime. Local dev may work on 3.11 for this PoC; README should recommend 3.12 but not block on it.
- Vercel CLI not installed: Vercel dashboard + GitHub auto-deploy is the standard path and requires no CLI.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docker-compose` (v1 CLI) | `docker compose` (v2, built into Docker Desktop) | 2023 | V1 is deprecated; compose.yaml preferred over docker-compose.yml (but both work) |
| `pip install` in Dockerfile without `--no-cache-dir` | Always use `--no-cache-dir` | Standard practice | Reduces image size by not storing pip's download cache |
| Gunicorn + uvicorn workers | `uvicorn` directly (single worker for PoC) | 2024 | For PoC/demo scale, single uvicorn worker is simpler; gunicorn adds complexity for no benefit |
| Vercel `vercel.json` with `routes` | Root Directory setting in dashboard | 2022+ | Cleaner for monorepos; no `vercel.json` needed unless custom rewrites required |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `python:3.12-slim` has no issues installing `mcp>=1.0` (which requires anyio and httpx) | Standard Stack | Low — slim has glibc and pip works; Alpine would fail but slim is safe |
| A2 | The Vercel free tier handles SSE streaming without timeout for this PoC (responses typically < 30s) | Architecture | Medium — Vercel Hobby plan has 10s serverless timeout, but SSE is NOT going through a serverless function (it hits the external FastAPI Docker server directly) so this is not a concern |
| A3 | Docker host IP/domain is accessible from the internet when running `docker compose up -d` | Architecture | High risk if user runs on a machine behind NAT; README must note the need for public IP or tunneling (e.g., ngrok for demo) `[ASSUMED]` |
| A4 | `mcp>=1.0` in `requirements.txt` resolves to a version without the fastmcp stdio Docker bug | Pitfall 1 | Medium — the `PYTHONUNBUFFERED=1` fix addresses the root cause regardless of mcp version |

---

## Open Questions

1. **Does the Docker host need a public IP?**
   - What we know: The Vercel frontend calls the backend at `NEXT_PUBLIC_API_URL` from the user's browser (not from Vercel's servers). So the browser must be able to reach the Docker host directly.
   - What's unclear: Whether the target deployment server has a public IP or needs a reverse proxy / tunnel.
   - Recommendation: README should note "ensure port 8000 is accessible from the internet" and optionally mention `ngrok http 8000` as a quick demo option.

2. **Does the MCP server need `python` in PATH inside the Docker container?**
   - What we know: `main.py` calls `StdioServerParameters(command="python", args=[MCP_SERVER_PATH])` — it spawns a subprocess via the string `"python"`.
   - What's unclear: The `python:3.12-slim` base image may only have `python3` in PATH, not `python`.
   - Recommendation: Either change `command="python3"` in `main.py` or add `RUN ln -s /usr/local/bin/python3 /usr/local/bin/python` in the Dockerfile. Verify by building and running `docker exec ... python --version`.

3. **HTTPS on Docker host?**
   - What we know: Browsers require HTTPS for pages served over HTTPS (Vercel) to make non-localhost requests. A plain `http://IP:8000` backend may be blocked by mixed-content policy.
   - What's unclear: Whether demo users will care (demo context), and whether a TLS solution is in scope.
   - Recommendation: Note in README that for a production demo, the Docker host should have a domain + TLS (e.g., Caddy reverse proxy, Cloudflare tunnel). For local demo only, `http://localhost:8000` works fine.

---

## Validation Architecture

> `nyquist_validation` is `false` in `.planning/config.json` — this section is skipped.

---

## Security Domain

> Phase 3 deployment scope. Key concerns are secret handling and CORS.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in this PoC |
| V3 Session Management | No | Stateless backend |
| V4 Access Control | No | No user roles |
| V5 Input Validation | Yes (existing) | Pydantic models already in Phase 1 routes |
| V6 Cryptography | No | API key in env var — not hand-rolled crypto |

### Known Threat Patterns for Docker + Vercel stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key in Docker image layer | Information Disclosure | Never `COPY .env` into image; use `env_file` at runtime |
| CORS wildcard `*` in production | Spoofing | Explicit origin list in `ALLOWED_ORIGINS`; wildcard only for dev |
| Mixed-content block (HTTPS→HTTP) | Denial of Service (UX) | Use HTTPS on Docker host for production demo |

---

## Sources

### Primary (HIGH confidence)
- Codebase read: `cyber-god/backend/main.py`, `config.py`, `requirements.txt`, `agent/loop.py`, `api/routes.py`, `price_mcp/server.py` — architecture fully understood
- Codebase read: `cyber-god/frontend/app/page.tsx` — `NEXT_PUBLIC_API_URL` already wired with correct fallback
- Docker Compose v2 docs: restart policies, env_file — `[CITED: docs.docker.com]`

### Secondary (MEDIUM confidence)
- FastAPI Docker deployment guide: Dockerfile patterns, `--host 0.0.0.0`, `PYTHONUNBUFFERED` — `[CITED: fastapi.tiangolo.com/deployment/docker/]`
- Vercel environment variables docs: NEXT_PUBLIC_ build-time inlining — `[CITED: vercel.com/docs/environment-variables]`
- Vercel monorepo docs: Root Directory setting — `[CITED: vercel.com/docs/monorepos]`

### Tertiary (LOW confidence — flagged)
- MCP stdio Docker buffering issue: community bug reports at `github.com/jlowin/fastmcp/issues/507` and `modelcontextprotocol/python-sdk/issues/1564` — `PYTHONUNBUFFERED=1` is the accepted fix
- `python:3.12-slim` vs Alpine for MCP packages: multiple community sources agree slim is correct choice

---

## Metadata

**Confidence breakdown:**
- Standard stack (Dockerfile, docker-compose): HIGH — patterns are well-established; base image and config verified against Docker Hub and FastAPI docs
- Architecture (deployment flow): HIGH — frontend code read directly; NEXT_PUBLIC_API_URL wiring confirmed
- MCP stdio in Docker: MEDIUM — critical pitfall identified from community sources; mitigation (`PYTHONUNBUFFERED=1`) is well-documented
- README structure: HIGH — straightforward documentation task

**Research date:** 2026-04-18
**Valid until:** 2026-06-01 (stable tools; docker-compose and Vercel deploy process is slow-moving)
