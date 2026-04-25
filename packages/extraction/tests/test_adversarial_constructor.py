import pytest
from argus_extraction.adversarial import AdversarialVerifier
from argus_extraction.providers.base import Provider
from pydantic import BaseModel


class _FakeProvider(Provider):
    def __init__(self, name: str = "openai") -> None:
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


def test_rejects_same_class_gpt() -> None:
    provider = _FakeProvider()
    with pytest.raises(ValueError, match="different model class"):
        AdversarialVerifier(
            verifier_provider=provider,
            extractor_model_class="gpt",
            model="gpt-5.4",
        )


def test_rejects_same_class_reasoning() -> None:
    provider = _FakeProvider()
    with pytest.raises(ValueError, match="different model class"):
        AdversarialVerifier(
            verifier_provider=provider,
            extractor_model_class="reasoning",
            model="o4-mini",
        )


def test_accepts_cross_class_reasoning_verifier() -> None:
    provider = _FakeProvider()
    verifier = AdversarialVerifier(
        verifier_provider=provider,
        extractor_model_class="gpt",
        model="o4-mini",
    )
    assert verifier is not None


def test_accepts_cross_class_gpt_verifier() -> None:
    provider = _FakeProvider()
    verifier = AdversarialVerifier(
        verifier_provider=provider,
        extractor_model_class="reasoning",
        model="gpt-5.5",
    )
    assert verifier is not None
