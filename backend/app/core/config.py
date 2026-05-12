"""Application configuration using pydantic-settings.

Auto-detects existing Claude / Codex agent credentials from the user's
home directory so that operators who already use those CLIs don't need
to re-configure environment variables. Auto-detection only fills empty
fields — explicit `LLM_PROVIDER` / `ANTHROPIC_*` / `OPENAI_API_KEY`
environment variables always take precedence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from pydantic_settings import BaseSettings


# ── home-directory loaders ─────────────────────────────────────────────

def _load_claude_settings() -> dict[str, Any]:
    """Read `~/.claude/settings.json` env block (Claude Code / Kimi proxy)."""
    path = Path.home() / ".claude" / "settings.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    env = data.get("env")
    return env if isinstance(env, dict) else {}


def _load_codex_auth() -> dict[str, Any]:
    """Read `~/.codex/auth.json` (Codex CLI; only API-key mode is usable here)."""
    path = Path.home() / ".codex" / "auth.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


# ── settings ───────────────────────────────────────────────────────────

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    env: str = "development"
    app_name: str = "LLMine Quant Backend"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://llmine:llmine@localhost:5432/llmine"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24  # 1 day
    algorithm: str = "HS256"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # API
    api_v1_prefix: str = "/api/v1"
    idempotency_key_header: str = "Idempotency-Key"

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    # LLM provider
    # Leave `llm_provider` empty to auto-select from detected credentials.
    llm_provider: str = ""
    llm_timeout_seconds: int = 120
    llm_max_tokens: int = 4096
    anthropic_api_key: str | None = None
    anthropic_auth_token: str | None = None  # Bearer-style auth (Kimi / proxies)
    anthropic_base_url: str | None = None  # override base URL
    anthropic_model: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o"

    # Auto-load AI agent config from ~/.claude and ~/.codex at startup.
    auto_load_agent_config: bool = True
    # Populated after auto-detection so we can surface it in logs / health.
    llm_source: str = "none"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def _auto_detect_credentials(s: Settings) -> None:
    """Fill empty LLM fields from `~/.claude/settings.json` / `~/.codex/auth.json`.

    Precedence: explicit env / .env > Claude Code config > Codex config > mock.
    Mutates `s` in place. Safe to call exactly once on startup.
    """
    if not s.auto_load_agent_config:
        if not s.llm_provider:
            s.llm_provider = "mock"
        s.llm_source = "env"
        return

    sources: list[str] = []

    # 1) Claude Code's settings.json (Bearer-style proxy or native Anthropic)
    claude_env = _load_claude_settings()
    if claude_env:
        filled = False
        if not s.anthropic_auth_token and claude_env.get("ANTHROPIC_AUTH_TOKEN"):
            s.anthropic_auth_token = claude_env["ANTHROPIC_AUTH_TOKEN"]
            filled = True
        if not s.anthropic_api_key and claude_env.get("ANTHROPIC_API_KEY"):
            s.anthropic_api_key = claude_env["ANTHROPIC_API_KEY"]
            filled = True
        if not s.anthropic_base_url and claude_env.get("ANTHROPIC_BASE_URL"):
            s.anthropic_base_url = claude_env["ANTHROPIC_BASE_URL"]
            filled = True
        if not s.anthropic_model:
            model = (
                claude_env.get("ANTHROPIC_MODEL")
                or claude_env.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
                or claude_env.get("ANTHROPIC_DEFAULT_OPUS_MODEL")
                or claude_env.get("ANTHROPIC_DEFAULT_HAIKU_MODEL")
            )
            if model:
                s.anthropic_model = model
                filled = True
        if filled:
            sources.append("~/.claude/settings.json")

    # 2) Codex CLI's auth.json — only api-key mode is usable for service-to-service calls.
    codex = _load_codex_auth()
    if codex.get("auth_mode") == "apikey" and codex.get("OPENAI_API_KEY"):
        if not s.openai_api_key:
            s.openai_api_key = codex["OPENAI_API_KEY"]
            sources.append("~/.codex/auth.json")

    # 3) Auto-select provider when not specified.
    if not s.llm_provider:
        if s.anthropic_auth_token or s.anthropic_api_key:
            s.llm_provider = "anthropic"
        elif s.openai_api_key:
            s.llm_provider = "openai"
        else:
            s.llm_provider = "mock"

    if sources:
        s.llm_source = ",".join(sources)
    elif s.llm_provider == "mock":
        s.llm_source = "mock"
    else:
        s.llm_source = "env"


_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def _normalize_sqlite_database_url(url: str) -> str:
    """Anchor relative SQLite URLs to the backend package root (…/backend/).

    Without this, ``sqlite+aiosqlite:///./dev.db`` resolves from the process cwd.
    Overview vs. other requests then may not see the same file if cwd differs
    (e.g. ``uvicorn`` started from repo root vs. ``backend/``).
    """
    marker = "sqlite+aiosqlite:///./"
    if not url.startswith(marker):
        return url
    rel = url[len(marker) :]
    abs_path = (_BACKEND_ROOT / rel).resolve()
    # Four slashes after the scheme for absolute POSIX paths (SQLAlchemy convention).
    return "sqlite+aiosqlite:///" + quote(str(abs_path), safe="/")


settings = Settings()
_auto_detect_credentials(settings)
settings.database_url = _normalize_sqlite_database_url(settings.database_url)
