"""Celery application + beat schedule for periodic LLMine jobs."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


def _broker_url() -> str:
    return settings.redis_url or "redis://localhost:6379/0"


celery_app = Celery(
    "llmine",
    broker=_broker_url(),
    backend=_broker_url(),
    include=["app.tasks.paper_trading"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    task_acks_late=True,
    worker_max_tasks_per_child=200,
)

# Daily EOD batch — A-share close is 15:00 CST; schedule a little after close so
# the bar data is final. Adjust to taste in production.
celery_app.conf.beat_schedule = {
    "paper-trading-eod": {
        "task": "app.tasks.paper_trading.run_eod_for_all_accounts",
        "schedule": crontab(hour=15, minute=30, day_of_week="mon-fri"),
        "options": {"queue": "paper_trading"},
    }
}
