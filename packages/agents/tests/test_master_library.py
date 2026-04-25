from uuid import uuid4

import pytest
from argus_agents.master import MasterAgent
from argus_agents.state import DiscussionState, EvidencePack
from argus_core.personas import PersonaLibrary, PersonaTemplate
from argus_extraction.providers import Provider
from pydantic import BaseModel


class _ExplodingProvider(Provider):
    """Provider that fails if called — proves the library path skipped the LLM."""

    name = "openai"

    async def structured_extract(
        self, prompt: str, schema: type[BaseModel], model: str
    ) -> BaseModel:
        raise AssertionError("library path should not invoke the provider")

    async def text_complete(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        raise AssertionError("library path should not invoke the provider")


class _StubSlateProvider(Provider):
    """Provider that returns a fixed persona slate; used for the LLM fallback path."""

    name = "openai"

    async def structured_extract(
        self, prompt: str, schema: type[BaseModel], model: str
    ) -> BaseModel:
        return schema(
            personas=[
                {
                    "frame": "skeptical fact-checker",
                    "description": "claim by claim",
                    "knowledge_emphasis": ["sourcing"],
                },
                {
                    "frame": "regulator viewpoint",
                    "description": "oversight",
                    "knowledge_emphasis": ["enforcement"],
                },
                {
                    "frame": "statistician",
                    "description": "methodology",
                    "knowledge_emphasis": ["uncertainty"],
                },
            ]
        )

    async def text_complete(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        raise NotImplementedError


def _make_library() -> PersonaLibrary:
    return PersonaLibrary(
        verticals={
            "finance": [
                PersonaTemplate(
                    frame="central bank monetary-policy view",
                    description="cautious lens",
                    knowledge_emphasis=["rates"],
                ),
                PersonaTemplate(
                    frame="market analyst skeptic",
                    description="contrarian lens",
                    knowledge_emphasis=["positioning"],
                ),
                PersonaTemplate(
                    frame="financial regulator viewpoint",
                    description="prudential lens",
                    knowledge_emphasis=["systemic risk"],
                ),
                PersonaTemplate(
                    frame="household saver perspective",
                    description="affected-party lens",
                    knowledge_emphasis=["real wages"],
                ),
            ]
        }
    )


def _make_state(*, vertical: str | None) -> DiscussionState:
    return DiscussionState(
        discussion_id=uuid4(),
        topic="Inflation outlook",
        evidence_pack=EvidencePack(topic="Inflation outlook", vertical=vertical),
    )


@pytest.mark.asyncio
async def test_master_uses_library_when_vertical_matches() -> None:
    library = _make_library()
    agent = MasterAgent(
        _ExplodingProvider(),
        model="gpt-5.5",
        library=library,
        library_persona_count=3,
    )
    state = _make_state(vertical="finance")

    result = await agent.step(state)

    assert len(result.personas) == 3
    frames = [p.frame for p in result.personas]
    assert frames == [
        "central bank monetary-policy view",
        "market analyst skeptic",
        "financial regulator viewpoint",
    ]
    assert result.errors == []


@pytest.mark.asyncio
async def test_master_falls_back_to_llm_when_vertical_missing() -> None:
    library = _make_library()
    agent = MasterAgent(
        _StubSlateProvider(),
        model="gpt-5.5",
        library=library,
    )
    state = _make_state(vertical=None)

    result = await agent.step(state)

    assert len(result.personas) == 3
    assert {p.frame for p in result.personas} == {
        "skeptical fact-checker",
        "regulator viewpoint",
        "statistician",
    }


@pytest.mark.asyncio
async def test_master_falls_back_when_vertical_unknown() -> None:
    library = _make_library()
    agent = MasterAgent(
        _StubSlateProvider(),
        model="gpt-5.5",
        library=library,
    )
    state = _make_state(vertical="not-a-real-vertical")

    result = await agent.step(state)

    assert len(result.personas) == 3
    assert any(p.frame == "skeptical fact-checker" for p in result.personas)


@pytest.mark.asyncio
async def test_master_with_empty_library_uses_llm() -> None:
    agent = MasterAgent(
        _StubSlateProvider(),
        model="gpt-5.5",
        library=PersonaLibrary(verticals={}),
    )
    state = _make_state(vertical="finance")

    result = await agent.step(state)

    assert len(result.personas) == 3
