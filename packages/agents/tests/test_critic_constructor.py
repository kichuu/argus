import pytest
from argus_agents.critic import CriticAgent
from argus_extraction.providers import Provider
from pydantic import BaseModel


class _FakeProvider(Provider):
    def __init__(self, name: str) -> None:
        self.name = name

    async def structured_extract(
        self, prompt: str, schema: type[BaseModel], model: str
    ) -> BaseModel:
        raise NotImplementedError

    async def text_complete(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        raise NotImplementedError


def test_critic_rejects_same_family_as_extractor():
    provider = _FakeProvider(name="anthropic")
    with pytest.raises(ValueError, match="must differ"):
        CriticAgent(provider, model="gpt-5-mini", extractor_family="anthropic")


def test_critic_rejects_critic_model_in_extractor_family():
    provider = _FakeProvider(name="openai")
    with pytest.raises(ValueError, match="must differ"):
        CriticAgent(provider, model="claude-sonnet-4-6", extractor_family="anthropic")


def test_critic_accepts_different_family():
    provider = _FakeProvider(name="openai")
    critic = CriticAgent(provider, model="gpt-5-mini", extractor_family="anthropic")
    assert critic.extractor_family == "anthropic"
