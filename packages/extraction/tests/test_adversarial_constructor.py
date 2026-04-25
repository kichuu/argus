import pytest
from pydantic import BaseModel

from argus_extraction.adversarial import AdversarialVerifier
from argus_extraction.providers.base import Provider


class _FakeProvider(Provider):
    def __init__(self, name: str) -> None:
        self.name = name

    async def structured_extract(
        self,
        prompt: str,
        schema: type[BaseModel],
        model: str,
    ) -> BaseModel:
        raise NotImplementedError

    async def text_complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 512,
    ) -> str:
        return "no"


def test_rejects_same_family_anthropic() -> None:
    provider = _FakeProvider(name="anthropic")
    with pytest.raises(ValueError, match="different family"):
        AdversarialVerifier(verifier_provider=provider, extractor_family="anthropic", model="x")


def test_rejects_same_family_openai() -> None:
    provider = _FakeProvider(name="openai")
    with pytest.raises(ValueError, match="different family"):
        AdversarialVerifier(verifier_provider=provider, extractor_family="openai", model="x")


def test_accepts_cross_family() -> None:
    provider = _FakeProvider(name="openai")
    verifier = AdversarialVerifier(
        verifier_provider=provider,
        extractor_family="anthropic",
        model="gpt-x",
    )
    assert verifier is not None
