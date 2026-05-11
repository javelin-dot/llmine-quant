"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


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
    llm_provider: str = "mock"  # mock / anthropic / openai
    llm_timeout_seconds: int = 120
    llm_max_tokens: int = 4096
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
