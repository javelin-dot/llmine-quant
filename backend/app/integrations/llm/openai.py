"""OpenAI (GPT) provider — lazy-loads the `openai` SDK.

Default model: gpt-4o.
Set `OPENAI_API_KEY` and `LLM_PROVIDER=openai` to enable.
"""

import json
from typing import Any

from app.core.errors import LLMException
from app.integrations.llm.base import LLMMessage, LLMProvider, LLMResponse


class OpenAILLMProvider(LLMProvider):
    """GPT provider using the official `openai` Python SDK."""

    name = "openai"
    default_model = "gpt-4o"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 120,
        max_tokens: int = 4096,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )
        self.base_url = base_url

    def _get_client(self) -> Any:
        try:
            import openai  # type: ignore[import-not-found]
        except ImportError as exc:
            raise LLMException(
                "openai SDK not installed. Run `pip install openai` "
                "or `pip install -e \".[llm]\"`.",
                details={"provider": self.name},
            ) from exc

        if not self.api_key:
            raise LLMException(
                "OPENAI_API_KEY is not configured.",
                details={"provider": self.name},
            )

        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout_seconds,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return openai.AsyncOpenAI(**kwargs)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        history: list[LLMMessage] | None = None,
    ) -> LLMResponse:
        client = self._get_client()

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for m in history or []:
            messages.append({"role": m.role, "content": m.content})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = await client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                max_tokens=self.max_tokens,
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMException(
                f"OpenAI API call failed: {exc}",
                details={"provider": self.name, "model": self.model},
            ) from exc

        text = (resp.choices[0].message.content or "").strip()
        usage = {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(resp.usage, "completion_tokens", 0) or 0,
        }
        return LLMResponse(text=text, model=self.model, provider=self.name, usage=usage, raw=resp)

    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        client = self._get_client()

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = await client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                max_tokens=self.max_tokens,
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMException(
                f"OpenAI API call failed: {exc}",
                details={"provider": self.name, "model": self.model},
            ) from exc

        text = (resp.choices[0].message.content or "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMException(
                f"OpenAI returned non-JSON output: {exc}",
                details={"provider": self.name, "raw": text[:500]},
            ) from exc
