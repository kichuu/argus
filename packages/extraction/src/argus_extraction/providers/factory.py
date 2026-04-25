from argus_extraction.providers.base import Provider
from argus_extraction.providers.openai import OpenAIProvider


def get_provider(name: str) -> Provider:
    key = name.lower().strip()
    if key == "openai":
        return OpenAIProvider()
    raise ValueError("only openai provider is supported in this build")


def family_of(model: str) -> str:
    m = model.lower().strip()
    if m.startswith("gpt-"):
        return "gpt"
    if m.startswith("o1") or m.startswith("o3") or m.startswith("o4"):
        return "reasoning"
    return "unknown"


def class_of(model: str) -> str:
    return family_of(model)
