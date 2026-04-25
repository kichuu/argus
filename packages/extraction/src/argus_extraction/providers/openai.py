import json

import openai
from pydantic import BaseModel

from argus_core.logging import get_logger
from argus_core.settings import get_settings

from argus_extraction.providers.base import Provider

logger = get_logger(__name__)


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or get_settings().openai_api_key
        self._client = openai.AsyncOpenAI(api_key=key)

    async def structured_extract(
        self,
        prompt: str,
        schema: type[BaseModel],
        model: str,
    ) -> BaseModel:
        # Prefer the Responses API (modern SDK); fall back to chat.completions.parse.
        responses = getattr(self._client, "responses", None)
        if responses is not None and hasattr(responses, "parse"):
            try:
                resp = await responses.parse(
                    model=model,
                    input=prompt,
                    text_format=schema,
                )
                parsed = getattr(resp, "output_parsed", None)
                if isinstance(parsed, schema):
                    return parsed
                if parsed is not None:
                    return schema.model_validate(parsed)
            except TypeError:
                # SDK signature drift; fall through to chat completions.
                pass

        completion = await self._client.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
        )
        message = completion.choices[0].message
        parsed = getattr(message, "parsed", None)
        if isinstance(parsed, schema):
            return parsed
        if parsed is not None:
            return schema.model_validate(parsed)
        if message.content:
            return schema.model_validate(json.loads(message.content))
        raise RuntimeError("openai response did not contain a parsed payload")

    async def text_complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 512,
    ) -> str:
        responses = getattr(self._client, "responses", None)
        if responses is not None and hasattr(responses, "create"):
            try:
                resp = await responses.create(
                    model=model,
                    input=prompt,
                    max_output_tokens=max_tokens,
                )
                text = getattr(resp, "output_text", None)
                if isinstance(text, str):
                    return text.strip()
            except TypeError:
                pass

        completion = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        content = completion.choices[0].message.content or ""
        return content.strip()
