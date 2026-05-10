# LLMine Quant Backend

AI-Native quantitative trading system backend.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Seed dev data
python scripts/seed_dev_data.py

# Run API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run worker (in another terminal)
celery -A app.tasks.celery_app worker -l info
```

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
