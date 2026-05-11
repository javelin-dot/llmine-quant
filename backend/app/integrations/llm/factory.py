"""LLM provider factory — selects the configured backend at runtime."""

from app.core.config import settings
from app.core.errors import LLMException
from app.integrations.llm.anthropic import AnthropicLLMProvider
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.mock import MockLLMProvider
from app.integrations.llm.openai import OpenAILLMProvider


def get_llm_provider(provider: str | None = None) -> LLMProvider:
    """Return an `LLMProvider` instance based on settings.

    Args:
        provider: override the configured provider. When None, uses
            `settings.llm_provider`.

    Raises:
        LLMException: if the provider name is unknown.
    """
    name = (provider or settings.llm_provider or "mock").lower()

    if name == "mock":
        return MockLLMProvider(
            api_key=None,
            model=None,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )

    if name == "anthropic":
        return AnthropicLLMProvider(
            api_key=settings.anthropic_api_key,
            auth_token=settings.anthropic_auth_token,
            base_url=settings.anthropic_base_url,
            model=settings.anthropic_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )

    if name == "openai":
        return OpenAILLMProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )

    raise LLMException(
        f"Unknown LLM provider: {name!r}. Expected mock / anthropic / openai.",
        details={"requested": name},
    )
