# LLMine Quant Backend

AI-Native quantitative trading system backend.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Ensure DB schema + optional default login users (admin@llmine.local / admin123)
python scripts/seed_dev_data.py

# Run API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run worker (in another terminal)
celery -A app.tasks.celery_app worker -l info
```

### Local API without Docker (SQLite)

If PostgreSQL is not running, you can point `DATABASE_URL` at a file-backed SQLite database (works well on Windows for UI development):

1. Copy `backend/.env.example` to `backend/.env` (or export variables in your shell).
2. Keep the line `DATABASE_URL=sqlite+aiosqlite:///./dev.db` and run all commands from the `backend/` directory so `./dev.db` resolves next to the app.
3. Run `alembic upgrade head`, then `python scripts/seed_dev_data.py`, then `uvicorn` as above. Redis is optional for the HTTP API in the current codebase; use Docker Compose when you need the full stack.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://llmine:llmine@localhost/llmine` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `SECRET_KEY` | — | JWT signing key |
| `ENV` | `development` | `development` / `staging` / `production` |
| `LOG_LEVEL` | `INFO` | Logging level |

## API Docs

OpenAPI docs available at `/docs` when running.
