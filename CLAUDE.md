# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLMine Quant is an AI-native quantitative trading platform. A Python/FastAPI backend serves a React/TypeScript frontend. The backend orchestrates LLM-driven strategy generation, backtesting, risk management, and trade execution.

## Commands

### Backend

```bash
cd backend

# Install (first time)
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Seed dev data
python scripts/seed_dev_data.py

# Start dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tests
pytest                            # all tests
pytest tests/path/test_file.py    # single file
pytest -k "test_name"             # single test

# Lint & type check
ruff check app/
mypy app/
```

### Frontend

```bash
cd frontend

npm run dev       # Dev server on :5173 (proxies /api and /ws to :8000)
npx tsc -b --force  # Type check only
npm run lint      # ESLint
npm run build     # tsc + vite production build
```

### Docker (PostgreSQL + Redis + API)

```bash
docker-compose -f deploy/docker-compose.yml up
```

## Architecture

### Backend Layers

```
app/api/v1/      → Route handlers (HTTP + WebSocket). Validate requests, call services.
app/services/    → Business logic and database transactions.
app/domains/     → Business entities per domain. Each has models.py (SQLAlchemy ORM) + schemas.py (Pydantic).
app/db/          → AsyncSession factory, Alembic migrations, declarative base.
app/integrations/→ External wrappers: LLM providers (Anthropic, OpenAI), market data sources.
app/core/        → Cross-cutting: config, logging, JWT auth, tracing, WebSocket utilities.
```

**Domains (13):** strategy, backtest, data, portfolio, execution, risk, explain, security, collaboration, audit, agents, identity — each has `models.py` + `schemas.py`.

**Route pattern:** endpoint injects `AsyncSession` via `get_db` dependency → calls service → returns Pydantic response schema.

**Key services:**
- `strategy_generation.py` — LLM-powered strategy creation (Anthropic/OpenAI)
- `daily_backtest.py` — Backtest execution engine
- `market_data_import.py` — Market data ingestion

### LLM Integration

`app/core/config.py` auto-detects credentials:
1. Explicit env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`)
2. `~/.claude/settings.json` (Claude Code credentials)
3. `~/.codex/auth.json`
4. Falls back to mock mode

Set `LLM_PROVIDER=anthropic|openai` to select provider.

### Frontend

Single-page app with no client-side router. `App.tsx` manages the active screen via `useState<Screen>`. All 11 screens live in `src/screens/`. API calls go through `src/lib/api.ts` (Axios, proxied to `:8000`). `src/contexts/` holds one React context per domain for server state.

`src/data/` contains a mock data layer that activates when the backend is unavailable. `VITE_MARKET=ashare|crypto` switches between A-share and crypto mock datasets — when you add a field to `MockData` in `types.ts`, update **both** `mock_ashare.ts` and `mock_crypto.ts`.

## Database

- Local dev: `sqlite+aiosqlite:///./llmine.db` (default `DATABASE_URL`)
- Production: `postgresql+asyncpg://...`
- Alembic config: `backend/alembic.ini`; migration files in `app/db/migrations/versions/`
- Always run `alembic upgrade head` after pulling new migration files

## Environment

Copy `backend/.env.example` to `backend/.env`. Minimum required for local dev:

```
DATABASE_URL=sqlite+aiosqlite:///./llmine.db
SECRET_KEY=dev-secret-key-change-in-production
```

`REDIS_URL` is only needed if running Celery workers.

## Code Conventions

- **Backend:** Ruff linting with rules E, F, I, N, W, UP, B, C4, SIM, ASYNC. Mypy strict. Pre-commit hooks enforce both.
- **Frontend:** ESLint catches `no-useless-assignment` — prefer `const x = condition ? a : b` over `let x = 0; if (...) x = ...`.
- **Async:** All DB operations use `async/await` with `AsyncSession`. Never use sync SQLAlchemy calls.
- **Error handling:** Raise `LLMineException` (from `app/core/errors.py`) — registered exception handlers in `main.py` translate these to HTTP responses.
