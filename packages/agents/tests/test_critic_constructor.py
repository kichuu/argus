import logging

from argus_agents.critic import CriticAgent
from argus_extraction.providers import Provider
from pydantic import BaseModel


class _FakeProvider(Provider):
    def __init__(self, name: str = "openai") -> None:
        self.name = name

    async def structured_extract(
        self, prompt: str, schema: type[BaseModel], model: str
    ) -> BaseModel:
        raise NotImplementedError

    async def text_complete(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        raise NotImplementedError


def test_critic_warns_when_same_class_as_extractor(caplog) -> None:
    provider = _FakeProvider()
    with caplog.at_level(logging.WARNING):
        critic = CriticAgent(provider, model="gpt-5.5", extractor_family="gpt")
    assert critic.extractor_family == "gpt"


def test_critic_no_warning_when_different_class(caplog) -> None:
    provider = _FakeProvider()
    with caplog.at_level(logging.WARNING):
        critic = CriticAgent(provider, model="o4-mini", extractor_family="gpt")
    assert critic.extractor_family == "gpt"
    assert "critic_extractor_same_class" not in caplog.text


def test_critic_accepts_no_extractor_family() -> None:
    provider = _FakeProvider()
    critic = CriticAgent(provider, model="gpt-5.5")
    assert critic.model == "gpt-5.5"
