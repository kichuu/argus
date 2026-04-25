from typing import Any

import anthropic
from pydantic import BaseModel

from argus_core.logging import get_logger
from argus_core.settings import get_settings

from argus_extraction.providers.base import Provider

logger = get_logger(__name__)


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or get_settings().anthropic_api_key
        self._client = anthropic.AsyncAnthropic(api_key=key)

    async def structured_extract(
        self,
        prompt: str,
        schema: type[BaseModel],
        model: str,
    ) -> BaseModel:
        json_schema = schema.model_json_schema()
        tool_name = f"emit_{schema.__name__.lower()}"
        tool: dict[str, Any] = {
            "name": tool_name,
            "description": f"Emit a structured {schema.__name__} payload.",
            "input_schema": json_schema,
        }

        response = await self._client.messages.create(
            model=model,
            max_tokens=4096,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
                payload = block.input  # type: ignore[attr-defined]
                return schema.model_validate(payload)

        raise RuntimeError("anthropic response did not contain expected tool_use block")

    async def text_complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 512,
    ) -> str:
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        parts: list[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)  # type: ignore[attr-defined]
        return "".join(parts).strip()
