"""LLMProvider abstract base class.

Defines the contract every concrete provider (mock / anthropic / openai) must satisfy.
Mirrors the pattern of `app.integrations.market_data.adapter.DataSourceAdapter`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMMessage:
    """A single chat message in the LLM conversation."""

    role: str  # "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """Generic response wrapper for LLM calls."""

    text: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str = "abstract"
    default_model: str = ""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 120,
        max_tokens: int = 4096,
    ) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        history: list[LLMMessage] | None = None,
    ) -> LLMResponse:
        """Generate a free-form text response."""
        raise NotImplementedError

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Generate a JSON object matching `output_schema`.

        Returns a Python dict parsed from the model's JSON output. The schema
        is best-effort — providers may use it for tool-style calling, JSON
        mode, or as in-prompt guidance depending on capability.
        """
        raise NotImplementedError
