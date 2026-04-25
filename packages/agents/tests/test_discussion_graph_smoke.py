"""End-to-end smoke test for DiscussionGraph with every OpenAI call mocked.

Exercises research -> master -> personas -> critic -> synthesizer and asserts
that the resulting state carries a non-empty, citation-bearing claim ledger.
No real network calls are made.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from argus_agents.critic import _CriticReport, _CriticVerdict
from argus_agents.graph import DiscussionGraph
from argus_agents.master import _PersonaProposal, _PersonaSlate
from argus_agents.synthesizer import _ClaimSlate, _ProposedClaim
from argus_extraction.providers import Provider
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class _FakeSpan:
    source_id: UUID
    verbatim_span: str
    char_start: int
    char_end: int
    fetched_at: datetime
    trust_tier: int
    entity_ids: list[UUID]


def _make_span(text: str, *, trust_tier: int = 2) -> _FakeSpan:
    return _FakeSpan(
        source_id=uuid4(),
        verbatim_span=text,
        char_start=0,
        char_end=len(text),
        fetched_at=datetime.now(UTC),
        trust_tier=trust_tier,
        entity_ids=[],
    )


class _FakeRetriever:
    def __init__(self, spans: list[_FakeSpan]) -> None:
        self._spans = spans
        self.calls: list[tuple[str, int]] = []

    async def retrieve(self, query: str, top_k: int = 20) -> list[_FakeSpan]:
        self.calls.append((query, top_k))
        return list(self._spans[:top_k])


class _ScriptedProvider(Provider):
    """A Provider whose responses are scripted by the schema or by a flag.

    `structured_responses` maps schema class -> object to return.
    `text_responses` is a list, popped front-first, for `text_complete` calls.
    """

    name = "openai"

    def __init__(
        self,
        structured_responses: dict[type[BaseModel], BaseModel],
        text_responses: list[str] | None = None,
    ) -> None:
        self._structured = structured_responses
        self._texts = list(text_responses or [])
        self.structured_calls: list[tuple[str, type[BaseModel], str]] = []
        self.text_calls: list[tuple[str, str, int]] = []

    async def structured_extract(
        self,
        prompt: str,
        schema: type[BaseModel],
        model: str,
    ) -> BaseModel:
        self.structured_calls.append((prompt, schema, model))
        if schema in self._structured:
            return self._structured[schema]
        raise AssertionError(
            f"_ScriptedProvider: no structured response registered for {schema}"
        )

    async def text_complete(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        self.text_calls.append((prompt, model, max_tokens))
        if not self._texts:
            raise AssertionError("_ScriptedProvider: no scripted text responses left")
        return self._texts.pop(0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def evidence_spans() -> list[_FakeSpan]:
    return [
        _make_span("The treaty was signed on 12 March 2024 in Geneva."),
        _make_span("Three of the four signatories ratified by year end."),
        _make_span("The fourth signatory delayed ratification pending review."),
    ]


@pytest.fixture
def retriever(evidence_spans: list[_FakeSpan]) -> _FakeRetriever:
    return _FakeRetriever(evidence_spans)


@pytest.fixture
def master_provider() -> _ScriptedProvider:
    slate = _PersonaSlate(
        personas=[
            _PersonaProposal(
                frame="skeptical empiricist",
                description="Demands measurable, replicable claims.",
                knowledge_emphasis=["statistics", "study design"],
            ),
            _PersonaProposal(
                frame="regulator viewpoint",
                description="Reads evidence through compliance and accountability.",
                knowledge_emphasis=["policy", "compliance"],
            ),
            _PersonaProposal(
                frame="historical analogue analyst",
                description="Looks for precedent and pattern.",
                knowledge_emphasis=["history", "case studies"],
            ),
        ]
    )
    return _ScriptedProvider({_PersonaSlate: slate})


@pytest.fixture
def persona_provider(evidence_spans: list[_FakeSpan]) -> _ScriptedProvider:
    e0, e1, e2 = evidence_spans
    # Each persona returns a small block of citation-bearing sentences.
    template = (
        f"The treaty was signed in Geneva in 2024 [ev:{e0.source_id}]. "
        f"Three signatories ratified within the year [ev:{e1.source_id}]. "
        f"One signatory has not yet ratified [ev:{e2.source_id}]."
    )
    # Three personas -> three text completions.
    return _ScriptedProvider(
        structured_responses={},
        text_responses=[template, template, template],
    )


@pytest.fixture
def critic_provider(evidence_spans: list[_FakeSpan]) -> _ScriptedProvider:
    e0, e1, _e2 = evidence_spans
    report = _CriticReport(
        verdicts=[
            _CriticVerdict(
                evidence_id=str(e0.source_id),
                assertion="The treaty was signed in Geneva in 2024",
                verdict="yes",
            ),
            _CriticVerdict(
                evidence_id=str(e1.source_id),
                assertion="Three signatories ratified within the year",
                verdict="partial",
                reason="span does not specify the year explicitly",
            ),
        ]
    )
    return _ScriptedProvider({_CriticReport: report})


@pytest.fixture
def synth_provider(evidence_spans: list[_FakeSpan]) -> _ScriptedProvider:
    e0, e1, e2 = evidence_spans
    slate = _ClaimSlate(
        claims=[
            _ProposedClaim(
                statement="The treaty was signed in Geneva on 12 March 2024.",
                supporting_evidence_ids=[str(e0.source_id)],
                contradicting_evidence_ids=[],
                agree=3,
                disagree=0,
                uncertain=0,
            ),
            _ProposedClaim(
                statement="Three of four signatories ratified by year end.",
                supporting_evidence_ids=[str(e1.source_id)],
                contradicting_evidence_ids=[],
                agree=3,
                disagree=0,
                uncertain=0,
            ),
            _ProposedClaim(
                statement="One signatory has not ratified yet.",
                supporting_evidence_ids=[str(e2.source_id)],
                contradicting_evidence_ids=[],
                agree=2,
                disagree=0,
                uncertain=1,
            ),
        ]
    )
    return _ScriptedProvider({_ClaimSlate: slate})


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


async def test_discussion_graph_end_to_end_produces_cited_claims(
    retriever: _FakeRetriever,
    master_provider: _ScriptedProvider,
    persona_provider: _ScriptedProvider,
    critic_provider: _ScriptedProvider,
    synth_provider: _ScriptedProvider,
) -> None:
    graph = DiscussionGraph(
        retriever=retriever,
        master_provider=master_provider,
        persona_provider=persona_provider,
        critic_provider=critic_provider,
        synth_provider=synth_provider,
        # Use distinct families so the critic-vs-extractor warning does not fire
        # with the same family as the extractor.
        research_model="gpt-4.1",
        master_model="gpt-4.1",
        persona_model="gpt-4.1",
        critic_model="o4-mini",
        synth_model="gpt-4.1",
        extractor_family="gpt",
    )

    discussion_id = uuid4()
    state = await graph.run("Test topic", discussion_id=discussion_id)

    # Retriever was called with the topic.
    assert retriever.calls, "retriever was never invoked"
    assert retriever.calls[0][0] == "Test topic"

    # Each scripted provider got at least one call.
    assert master_provider.structured_calls, "master provider not called"
    assert len(persona_provider.text_calls) == 3, (
        "expected one text_complete per persona, "
        f"got {len(persona_provider.text_calls)}"
    )
    assert critic_provider.structured_calls, "critic provider not called"
    assert synth_provider.structured_calls, "synth provider not called"

    # State invariants.
    assert state.discussion_id == discussion_id
    assert state.evidence_pack.evidence, "evidence pack must be populated"

    roles = [m.role.value for m in state.messages]
    assert len(state.messages) >= 5, (
        f"expected >=5 messages (research, master, >=1 persona, critic, synthesizer); "
        f"got {len(state.messages)} with roles={roles}"
    )
    # Every required role must appear at least once.
    for required in ("research", "master", "persona", "critic", "synthesizer"):
        assert required in roles, f"missing message role {required!r} in {roles}"

    # Final claims: at least one and every claim must carry evidence.
    assert state.final_claims, (
        f"synthesizer returned no claims; errors={state.errors}"
    )
    for claim in state.final_claims:
        assert claim.supporting_evidence, (
            f"claim {claim.statement!r} has no supporting evidence"
        )
        assert 0.0 <= claim.confidence <= 1.0
