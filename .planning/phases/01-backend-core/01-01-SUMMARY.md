---
phase: 01-backend-core
plan: 01
subsystem: backend-scaffold
tags: [fastapi, mcp, python, tool-layer, cors]
dependency_graph:
  requires: []
  provides:
    - cyber-god/backend/requirements.txt
    - cyber-god/backend/config.py
    - cyber-god/backend/main.py
    - cyber-god/backend/price_mcp/server.py
    - cyber-god/backend/tools/savings.py
    - cyber-god/backend/tools/price.py
  affects:
    - Plan 02 (agent loop depends on all modules created here)
    - Plan 03 (API route depends on main.py and tools)
tech_stack:
  added:
    - fastapi[standard]>=0.115.0,<1.0
    - pydantic>=2.7.0,<3.0
    - uvicorn[standard]>=0.30.0
    - openai~=1.102
    - mcp>=1.0
    - python-dotenv>=1.0.0
  patterns:
    - FastAPI asynccontextmanager lifespan for MCP subprocess management
    - MCP low-level Server + stdio_server async context manager pattern
    - Single shared ClientSession via app.state.mcp_session
    - Pure function TDD for calculate_savings_impact
key_files:
  created:
    - cyber-god/backend/requirements.txt
    - cyber-god/backend/.env.example
    - cyber-god/backend/config.py
    - cyber-god/backend/main.py
    - cyber-god/backend/__init__.py
    - cyber-god/backend/price_mcp/__init__.py
    - cyber-god/backend/price_mcp/server.py
    - cyber-god/backend/tools/__init__.py
    - cyber-god/backend/tools/savings.py
    - cyber-god/backend/tools/price.py
    - cyber-god/backend/tools/test_savings.py
    - cyber-god/backend/agent/__init__.py
    - cyber-god/backend/api/__init__.py
  modified: []
decisions:
  - "StdioServerParameters imported from mcp directly (not mcp.client.stdio) — both paths resolve in mcp>=1.0"
  - "MCP server uses low-level Server + stdio_server context manager (not FastMCP) to match plan's explicit pattern"
  - "stdio_server is an @asynccontextmanager yielding (read_stream, write_stream) — must use async with, not asyncio.run(stdio_server(...))"
  - "comment_hint is neutral for price==0 (zero-cost is not a deficit)"
  - "AsyncExitStack.__aenter__() called manually to allow storing exit_stack without async with block in lifespan"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-18"
  tasks_completed: 3
  tasks_total: 3
  files_created: 13
  files_modified: 1
---

# Phase 01 Plan 01: Backend Scaffold and Tool Layer Summary

**One-liner:** FastAPI backend scaffold with MCP price server (15-item CNY catalog), savings impact calculator (TDD), and async MCP client lifecycle managed via FastAPI lifespan.

## What Was Built

### Directory Structure Created

```
cyber-god/backend/
  __init__.py
  requirements.txt          <- pinned: openai~=1.102, mcp>=1.0, fastapi[standard]>=0.115.0,<1.0
  .env.example              <- ZHIPU_API_KEY, GLM_MODEL, ALLOWED_ORIGINS template
  config.py                 <- env var loading; fail-fast on missing ZHIPU_API_KEY
  main.py                   <- FastAPI app + CORS + MCP lifespan
  price_mcp/
    __init__.py
    server.py               <- MCP server: search_products tool + 15-item catalog
  tools/
    __init__.py
    savings.py              <- calculate_savings_impact pure function
    price.py                <- async get_price() MCP client wrapper
    test_savings.py         <- 5 TDD tests (all passing)
  agent/
    __init__.py             <- empty; loop.py and prompt.py added in Plan 02
  api/
    __init__.py             <- empty; routes.py added in Plan 02
```

### MCP Server Import Paths Used (mcp 1.27.0)

| Symbol | Import Path |
|--------|-------------|
| `Server` | `from mcp.server import Server` |
| `stdio_server` | `from mcp.server.stdio import stdio_server` |
| `types` | `from mcp import types` |
| `ClientSession` | `from mcp import ClientSession` |
| `StdioServerParameters` | `from mcp import StdioServerParameters` |
| `stdio_client` | `from mcp.client.stdio import stdio_client` |

Note: `StdioServerParameters` resolves from both `mcp` and `mcp.client.stdio` in mcp 1.27.0.

### Catalog Items and Base Prices

| Item | Base Price (CNY) |
|------|-----------------|
| 盲盒 | 599 |
| 奶茶 | 38 |
| 耳机 | 799 |
| 口红 | 289 |
| 球鞋 | 1299 |
| 游戏皮肤 | 128 |
| 充值 | 100 |
| 手机壳 | 59 |
| 咖啡 | 42 |
| 键盘 | 899 |
| 外设 | 599 |
| 网红零食 | 88 |
| 香水 | 498 |
| 包包 | 1599 |
| 化妆品 | 368 |

All prices randomized with `base * random.uniform(0.7, 1.3)` at query time.
Unknown items use DEFAULT_PRICE = 500 with same randomization.

## Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Scaffold + config + main | bc6a582 | requirements.txt, config.py, main.py, all __init__.py |
| 2 | Price MCP server + savings TDD | bc5458e | price_mcp/server.py, tools/savings.py, tools/test_savings.py |
| 3 | MCP client wrapper + lifespan | 1d7ca8a | tools/price.py, main.py (updated) |

## Verification Results

1. `from config import ZHIPU_API_KEY, GLM_MODEL, ALLOWED_ORIGINS` — PASS (with key set)
2. `python -m pytest tools/test_savings.py -v` — 5/5 PASS
3. `python price_mcp/server.py` — starts and exits cleanly on stdin close (no crash)
4. `from tools.price import get_price; from tools.savings import calculate_savings_impact` — PASS
5. `from main import app` — PASS (with ZHIPU_API_KEY set)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] stdio_server is a context manager, not a plain coroutine**
- **Found during:** Task 2 initial server implementation
- **Issue:** Plan pseudocode showed `asyncio.run(stdio_server(server))` which fails because `stdio_server` in mcp 1.27.0 is an `@asynccontextmanager` yielding `(read_stream, write_stream)`, not a coroutine
- **Fix:** Changed `__main__` entry point to `async with stdio_server() as (read_stream, write_stream): await server.run(read_stream, write_stream, server.create_initialization_options())`
- **Files modified:** `price_mcp/server.py`
- **Commit:** bc5458e

**2. [Rule 3 - Blocking] pytest not installed in environment**
- **Found during:** Task 2 TDD RED phase
- **Issue:** `python -m pytest` failed with "No module named pytest"
- **Fix:** `pip install pytest` before running tests
- **Files modified:** None (environment setup only)
- **Commit:** bc5458e (tests pass in that commit)

## Known Stubs

None — all modules implement their full planned functionality. `agent/__init__.py` and `api/__init__.py` are intentionally empty; their content (`loop.py`, `prompt.py`, `routes.py`) is planned for Plan 02.

## Threat Flags

None — all security mitigations from the threat model are implemented:
- T-01-01: `os.environ["ZHIPU_API_KEY"]` raises KeyError on startup if missing (not logged)
- T-01-02: ALLOWED_ORIGINS loaded from env var, defaults to localhost:3000
- T-01-03: MCP subprocess path hard-coded via `__file__`, not user-supplied
- T-01-04: `AsyncExitStack.aclose()` called after `yield` in lifespan

## Self-Check: PASSED

Files exist:
- FOUND: cyber-god/backend/requirements.txt
- FOUND: cyber-god/backend/config.py
- FOUND: cyber-god/backend/main.py
- FOUND: cyber-god/backend/price_mcp/server.py
- FOUND: cyber-god/backend/tools/savings.py
- FOUND: cyber-god/backend/tools/price.py
- FOUND: cyber-god/backend/tools/test_savings.py

Commits exist:
- FOUND: bc6a582 (Task 1 scaffold)
- FOUND: bc5458e (Task 2 MCP server + TDD)
- FOUND: 1d7ca8a (Task 3 client wrapper + lifespan)
