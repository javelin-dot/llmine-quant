"""Anthropic (Claude) provider — lazy-loads the `anthropic` SDK.

Default model: claude-sonnet-4-6 (per implementation plan).
Set `ANTHROPIC_API_KEY` and `LLM_PROVIDER=anthropic` to enable.
"""

import json
from typing import Any

from app.core.errors import LLMException
from app.integrations.llm.base import LLMMessage, LLMProvider, LLMResponse


class AnthropicLLMProvider(LLMProvider):
    """Claude provider using the official `anthropic` Python SDK."""

    name = "anthropic"
    default_model = "claude-sonnet-4-6"

    def _get_client(self) -> Any:
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:
            raise LLMException(
                "anthropic SDK not installed. Run `pip install anthropic` "
                "or `pip install -e \".[llm]\"`.",
                details={"provider": self.name},
            ) from exc

        if not self.api_key:
            raise LLMException(
                "ANTHROPIC_API_KEY is not configured.",
                details={"provider": self.name},
            )

        return anthropic.AsyncAnthropic(api_key=self.api_key, timeout=self.timeout_seconds)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        history: list[LLMMessage] | None = None,
    ) -> LLMResponse:
        client = self._get_client()

        messages: list[dict[str, str]] = []
        for m in history or []:
            messages.append({"role": m.role, "content": m.content})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            resp = await client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 — surface as LLMException
            raise LLMException(
                f"Anthropic API call failed: {exc}",
                details={"provider": self.name, "model": self.model},
            ) from exc

        # Concatenate all text blocks (skip thinking/tool blocks).
        text_parts: list[str] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        text = "\n".join(text_parts).strip()

        usage = {
            "prompt_tokens": getattr(resp.usage, "input_tokens", 0) or 0,
            "completion_tokens": getattr(resp.usage, "output_tokens", 0) or 0,
        }

        return LLMResponse(text=text, model=self.model, provider=self.name, usage=usage, raw=resp)

    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        # Append schema hint to the system prompt — Claude reliably honours
        # explicit JSON-only instructions without needing tool-use.
        schema_hint = (
            f"\n\nReturn ONLY a JSON object that conforms to this schema:\n"
            f"{json.dumps(output_schema)}\n"
            f"Do not include markdown fences or commentary."
        )
        full_system = (system_prompt or "") + schema_hint

        resp = await self.generate(
            prompt=prompt,
            system_prompt=full_system,
            temperature=temperature,
        )

        text = resp.text.strip()
        # Strip markdown fences if the model added any.
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(line for line in lines if not line.startswith("```")).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMException(
                f"Anthropic returned non-JSON output: {exc}",
                details={"provider": self.name, "raw": text[:500]},
            ) from exc
