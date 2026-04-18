---
phase: 3
slug: deployment
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-18
---

# Phase 3 — UI Design Contract

> Visual and interaction contract for Phase 3 (Deployment). Phase 3 produces no new interactive frontend components. Its only "UI" surface is the README.md, which is a developer-facing document with formatting, copywriting, and structural conventions.
>
> All application UI tokens are carried forward from Phase 2 as the authoritative reference. No new tokens are introduced in this phase.

---

## Phase Scope Clarification

Phase 3 deliverables are:

| Deliverable | UI Surface? | Contract Needed? |
|-------------|-------------|------------------|
| `cyber-god/backend/Dockerfile` | None — config file | No |
| `cyber-god/backend/docker-compose.yml` | None — config file | No |
| `cyber-god/backend/.env.example` | None — config file | No |
| `cyber-god/backend/.dockerignore` | None — config file | No |
| `README.md` (repo root) | Developer document | Yes — structure, formatting, copywriting |

The README is the single UI surface this contract governs.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | Tailwind CSS (application only — no design system for README) |
| Preset | none |
| Component library | None |
| Icon library | Unicode emoji and plain text symbols (carried from Phase 2) |
| Font | GitHub Markdown renderer default (system sans-serif) — README is rendered on GitHub |

**Note:** The application design system (light/white fintech theme with `gray-50` background, `yellow-500` accent, system font stack) was established in Phase 2 and implemented. No changes are made to it in Phase 3. The Phase 2 UI-SPEC is the authoritative reference for application tokens.

---

## Application Color Reference (Carry-Forward from Phase 2, As-Implemented)

> Recorded here for traceability. The implemented codebase diverged from the Phase 2 UI-SPEC dark theme — the actual implementation uses a light theme (per git commit "switch to white/light fintech theme"). This contract records the implemented reality.

| Role | Tailwind | Usage |
|------|----------|-------|
| **Page background** | `bg-gray-50` | Full page background |
| **Surface (panels, header, input)** | `bg-white` | Header bar, savings panel, input area |
| **Border** | `border-gray-200` | All divider lines |
| **Primary text** | `text-gray-900` | All body text |
| **Secondary text** | `text-gray-600` | Labels, sublabels |
| **Muted text** | `text-gray-400` / `text-gray-500` | Placeholders, role labels |
| **Accent — Gold** | `bg-yellow-500` / `text-yellow-500` | Progress bar fill, send button, focus rings |
| **Accent — Approve** | `border-green-500` | Left border on approve verdict bubbles |
| **Accent — Reject** | `border-red-500` | Left border on reject verdict bubbles |
| **Error/Stop** | `bg-red-500` / `bg-red-50` | Stop button, error banner background |
| **Flash** | `bg-red-600` (1.5s animate) | Progress bar negative delta flash |

---

## Spacing Scale

Carried from Phase 2 — no new spacing introduced in Phase 3.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, inline padding |
| sm | 8px | Compact element spacing |
| md | 16px | Default element spacing |
| lg | 24px | Section padding |
| xl | 32px | Layout gaps |
| 2xl | 48px | Major section breaks |

Exceptions for Phase 3: none.

---

## Typography

Carried from Phase 2 — no new typography in Phase 3 application code.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 (regular) | 1.5 |
| Label | 14px | 400 (regular) | 1.5 |
| Heading | 20px | 600 (semibold) | 1.2 |
| Display | 18px | 600 (semibold) | 1.2 |

**README typography:** Follows GitHub Markdown rendering defaults. No custom CSS applies. Heading hierarchy must be: `#` for document title, `##` for major sections, `###` for sub-sections. No heading deeper than `###`.

---

## Color

Carried from Phase 2. Phase 3 introduces no new color values.

Accent reserved for (application UI, unchanged):
1. `yellow-500` — progress bar fill, send button, focus ring
2. `green-500` — left border on approve verdicts
3. `red-500` — left border on reject verdicts, stop button
4. `red-600` — 1.5s flash animation on negative savings delta

---

## README Structure Contract

The README is the primary deliverable with user-facing design implications. The following structure is mandatory.

### Document Hierarchy

```
# 赛博财神爷 (Cyber God of Wealth)
  — one-line description (Chinese + English)

## 功能特性 (Features)
  — 3-5 bullet points of core capabilities

## 快速开始 (Quick Start)
  ### 本地开发 (Local Development)
    #### 后端 (Backend)
    #### 前端 (Frontend)
  ### Docker 部署 (Docker Deployment)
  ### Vercel 前端部署 (Vercel Frontend Deployment)

## 环境变量 (Environment Variables)
  — table: variable name | required | default | description

## 架构说明 (Architecture)
  — brief description only; no deep dives

## 注意事项 (Known Issues / Gotchas)
  — critical deployment pitfalls (5 max)
```

### Formatting Rules

1. Every section heading must include both Chinese and English in parentheses: `## 快速开始 (Quick Start)`
2. All code blocks must specify language: ` ```bash `, ` ```dockerfile `, ` ```yaml `, ` ```typescript `
3. Shell commands use PowerShell syntax (Windows-primary audience per DEPLOY-04); bash alternatives shown inline as comments where they differ
4. No inline HTML — pure Markdown only
5. All file paths use forward slashes in code blocks even on Windows paths for cross-platform clarity
6. No emojis in README section headings or code blocks; plain emoji acceptable in description text only

### Code Block Conventions

- All environment variable values use placeholder format: `sk-your-key-here` (never real values)
- Docker commands use `docker compose` (v2, no hyphen) — never `docker-compose`
- npm/yarn alternatives not shown — pnpm is the canonical package manager per `pnpm-lock.yaml`
- Python environment activation shows PowerShell path: `.\.venv\Scripts\Activate.ps1`

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| README title | `赛博财神爷 (Cyber God of Wealth)` |
| README subtitle | `AI 财务顾问 · 毒舌财神 · GLM-5 驱动` (one line, no period) |
| Quick Start section heading | `快速开始 (Quick Start)` |
| Env var table heading | `环境变量 (Environment Variables)` |
| ZHIPU_API_KEY description | `智谱 AI API 密钥 — 从 open.bigmodel.cn 获取` |
| GLM_MODEL description | `模型名称，默认 glm-4-flash（免费快速），推荐生产用 glm-4-5` |
| ALLOWED_ORIGINS description | `逗号分隔的 CORS 来源列表，例如 https://your-app.vercel.app,http://localhost:3000` |
| NEXT_PUBLIC_API_URL description | `后端 URL，构建时注入，更改后需重新部署` |
| Step 1 note (copy .env) | `cp .env.example .env` then `# 填入 ZHIPU_API_KEY` |
| Docker startup command | `docker compose up -d` |
| Docker stop command | `docker compose down` |
| Critical pitfall note (PYTHONUNBUFFERED) | `PYTHONUNBUFFERED=1 is set in the Dockerfile — required to prevent MCP subprocess stdio hang inside Docker` |
| Mixed-content warning | `Vercel (HTTPS) requires the backend to also serve HTTPS. For local demo, use http://localhost:8000. For public demo, add TLS (e.g., Caddy or Cloudflare Tunnel).` |
| Port conflict note | `Stop any local uvicorn dev server before running docker compose up — both use port 8000` |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | None | Not applicable — no shadcn used |
| Tailwind CSS | Built-in utilities only | No third-party blocks |

No new registries or third-party component imports in Phase 3. All infrastructure tooling (Docker, Vercel) has no frontend registry implications.

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

## Pre-Population Sources

| Source | Decisions Used |
|--------|---------------|
| Phase 2 UI-SPEC (`02-UI-SPEC.md`) | All application tokens (color, spacing, typography) carried forward |
| Codebase scan (page.tsx, globals.css, all components) | Confirmed light/white theme as implemented reality; overrides Phase 2 dark theme spec |
| REQUIREMENTS.md (DEPLOY-04) | README must cover Windows/PowerShell, Docker build + push, Vercel deploy |
| RESEARCH.md (03-RESEARCH.md) | README structure, PowerShell commands, env var names, Docker pitfalls |
| CLAUDE.md | No deviations from stack; pnpm is package manager; no DB |
| User input | None required — all decisions answered by upstream artifacts |

---

*UI-SPEC created: 2026-04-18*
*Phase: 03-deployment*
*Status: draft — awaiting gsd-ui-checker verification*
