# 赛博财神爷 (Cyber God of Wealth)

AI 财务顾问 · 毒舌财神 · GLM-5 驱动

## 功能特性 (Features)

- GLM-5 powered snarky verdict streamed token by token in Chinese
- Tool-call transparency: shows price lookup and savings impact calculation status in real time
- Savings progress bar animates on agent response; flashes red when a purchase dents your savings
- localStorage persistence for savings goal (存款目标) and current savings (已存金额)
- One-command Docker backend (`docker compose up -d`) + Vercel-hosted frontend

## 快速开始 (Quick Start)

### 本地开发 (Local Development)

#### 后端 (Backend)

```powershell
cd cyber-god/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Edit .env: fill in ZHIPU_API_KEY
uvicorn main:app --reload --port 8000
```

Bash users: replace activation with `source .venv/bin/activate`. `cp` is the same.

#### 前端 (Frontend)

```powershell
cd cyber-god/frontend
pnpm install
# Create cyber-god/frontend/.env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm dev
```

The frontend defaults to http://localhost:8000 if NEXT_PUBLIC_API_URL is not set.

### Docker 部署 (Docker Deployment)

1. Copy `.env.example` to `.env` in `cyber-god/backend/` and fill in `ZHIPU_API_KEY`. Set `ALLOWED_ORIGINS` to include your Vercel URL for production.

2. Build and start:

```bash
cd cyber-god/backend
docker compose up -d
```

3. Verify:

```bash
curl http://localhost:8000/docs
```

Expected: HTML response (FastAPI Swagger UI page)

4. Stop:

```bash
docker compose down
```

> Stop any local uvicorn dev server before running docker compose up — both use port 8000.

> The browser calls the backend directly. Ensure port 8000 is accessible from the internet, or use a tunnel (e.g., `ngrok http 8000`) for a quick public demo.

### Vercel 前端部署 (Vercel Frontend Deployment)

1. Connect your GitHub repo to Vercel (vercel.com > New Project > Import).
2. In Project Settings > General > Root Directory: set to `cyber-god/frontend`.
3. In Project Settings > Environment Variables (Production): add `NEXT_PUBLIC_API_URL` = `https://your-docker-host-or-domain:8000`.
4. Deploy: push to main or click "Redeploy" in the Vercel dashboard.

> NEXT_PUBLIC_API_URL is baked into the JS bundle at build time. If the backend URL changes, trigger a new deployment.

> Vercel (HTTPS) requires the backend to also serve HTTPS. For local demo, use http://localhost:8000. For a public demo, add TLS (e.g., Caddy or Cloudflare Tunnel).

## 环境变量 (Environment Variables)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZHIPU_API_KEY` | Yes | — | 智谱 AI API 密钥 — 从 open.bigmodel.cn 获取 |
| `GLM_MODEL` | No | glm-4-flash | 模型名称，默认 glm-4-flash（免费快速），推荐生产用 glm-4-5 |
| `ALLOWED_ORIGINS` | No | http://localhost:3000 | 逗号分隔的 CORS 来源列表，例如 https://your-app.vercel.app,http://localhost:3000 |
| `NEXT_PUBLIC_API_URL` | No (frontend) | http://localhost:8000 | 后端 URL，构建时注入，更改后需重新部署 |

## 架构说明 (Architecture)

User sends a purchase impulse via the chat UI. The FastAPI backend spawns a local MCP price server as a subprocess, calls it to look up mock prices, then runs a savings impact calculation. It streams a GLM-5-powered snarky verdict in Vercel Data Stream Protocol format (f:, 0:, 2:, e:, d: lines). The frontend progress bar animates when the 2: data chunk arrives.

## 注意事项 (Known Issues / Gotchas)

1. `PYTHONUNBUFFERED=1` is set in the Dockerfile — required to prevent MCP subprocess stdio hang inside Docker.
2. Stop any local uvicorn dev server before running `docker compose up` — both use port 8000.
3. `NEXT_PUBLIC_API_URL` is baked into the JS bundle at build time. Changing it in the Vercel dashboard requires a new deployment.
4. Vercel (HTTPS) to HTTP backend is blocked by browsers (mixed-content policy). For a public demo, add TLS to the Docker host (e.g., Caddy reverse proxy or Cloudflare Tunnel).
5. `ALLOWED_ORIGINS` must include the exact Vercel deployment URL with no trailing slash. Using `*` disables CORS protection.
