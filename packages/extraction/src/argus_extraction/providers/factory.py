from argus_extraction.providers.anthropic import AnthropicProvider
from argus_extraction.providers.base import Provider
from argus_extraction.providers.openai import OpenAIProvider


def get_provider(name: str) -> Provider:
    key = name.lower().strip()
    if key == "anthropic":
        return AnthropicProvider()
    if key == "openai":
        return OpenAIProvider()
    raise ValueError(f"unknown provider: {name!r}")


def family_of(model: str) -> str:
    m = model.lower().strip()
    if m.startswith("claude-"):
        return "anthropic"
    if m.startswith("gpt-") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4"):
        return "openai"
    raise ValueError(f"cannot infer provider family from model: {model!r}")
