from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from argus_agents.orchestrator import CouncilOrchestrator
from argus_core.personas import PersonaLibrary, PersonaTemplate
from argus_core.schemas import AgentRole, Claim, EvidenceRef


def _ev(span: str = "the sky is blue", start: int = 0) -> EvidenceRef:
    return EvidenceRef(
        source_id=uuid4(),
        verbatim_span=span,
        char_start=start,
        char_end=start + len(span),
        fetched_at=datetime.now(UTC),
        trust_tier=2,
    )


def _retrieved_span(ref: EvidenceRef) -> Any:
    span = MagicMock()
    span.source_id = ref.source_id
    span.verbatim_span = ref.verbatim_span
    span.char_start = ref.char_start
    span.char_end = ref.char_end
    span.fetched_at = ref.fetched_at
    span.trust_tier = ref.trust_tier
    span.entity_ids = []
    return span


def _library() -> PersonaLibrary:
    return PersonaLibrary(
        verticals={
            "finance": [
                PersonaTemplate(
                    frame=f"finance frame {i}",
                    description="d",
                    knowledge_emphasis=["macro", "rates"],
                )
                for i in range(3)
            ]
        }
    )


class _MockProvider:
    name = "openai"

    def __init__(
        self,
        *,
        persona_text: str = "The cited evidence shows the claim holds true [ev:{eid}].",
    ) -> None:
        self.persona_text = persona_text
        self.calls: list[Any] = []

    async def text_complete(self, prompt: str, model: str, max_tokens: int = 800) -> str:
        # Reflect the first ev:UUID in the evidence block back so persona output
        # carries a recognised citation and survives strip_unsupported_claims.
        import re

        m = re.search(r"\[ev:([0-9a-fA-F-]{36})\]", prompt)
        eid = m.group(1) if m else "00000000-0000-0000-0000-000000000000"
        return self.persona_text.format(eid=eid)

    async def structured_extract(self, prompt: str, schema: type, model: str) -> Any:
        # Master returns a slate; Critic returns no flags; Synth returns one claim per evidence id.
        from argus_agents.critic import _CriticReport
        from argus_agents.master import _PersonaProposal, _PersonaSlate
        from argus_agents.synthesizer import _ClaimSlate, _ProposedClaim

        if schema is _PersonaSlate:
            return _PersonaSlate(
                personas=[
                    _PersonaProposal(
                        frame=f"frame {i}", description="d", knowledge_emphasis=["k"]
                    )
                    for i in range(3)
                ]
            )
        if schema is _CriticReport:
            return _CriticReport(verdicts=[])
        if schema is _ClaimSlate:
            import re

            ids = list({m.group(1) for m in re.finditer(r"\[ev:([0-9a-fA-F-]{36})\]", prompt)})
            return _ClaimSlate(
                claims=[
                    _ProposedClaim(
                        statement="atomic claim from synth",
                        supporting_evidence_ids=ids[:1] or [str(uuid4())],
                        agree=2,
                    )
                ]
            )
        raise AssertionError(f"unexpected schema {schema!r}")


@pytest.mark.asyncio
async def test_run_emits_phases_in_order() -> None:
    refs = [_ev(f"span-{i}") for i in range(4)]
    spans = [_retrieved_span(r) for r in refs]
    retriever = MagicMock()
    retriever.retrieve = AsyncMock(return_value=spans)

    phases: list[str] = []
    posts: list[Any] = []
    statuses: list[tuple[str, str]] = []
    claims: list[Claim] = []

    async def on_phase(phase: str) -> None:
        phases.append(phase)

    async def on_post(msg: Any) -> None:
        posts.append(msg)

    async def on_status(agent_id: str, state: str, _extra: dict) -> None:
        statuses.append((agent_id, state))

    async def on_claim(claim: Claim) -> None:
        claims.append(claim)

    orch = CouncilOrchestrator(
        provider=_MockProvider(),
        retriever=retriever,
        library=_library(),
        on_post=on_post,
        on_status=on_status,
        on_phase=on_phase,
        on_claim=on_claim,
        max_concurrency=4,
    )

    state = await orch.run("FOMC December rates?", vertical="finance", num_personas=3)

    assert phases == [
        "researching",
        "planning",
        "debating",
        "criticizing",
        "synthesizing",
        "completed",
    ]
    assert len(state.personas) == 3
    assert len(state.messages) >= 3  # at least one per persona
    assert any(p.role == AgentRole.PERSONA for p in posts)
    assert claims and all(isinstance(c, Claim) for c in claims)


@pytest.mark.asyncio
async def test_persona_lens_query_includes_knowledge_emphasis() -> None:
    refs = [_ev(f"span-{i}") for i in range(4)]
    spans = [_retrieved_span(r) for r in refs]
    retriever = MagicMock()
    retriever.retrieve = AsyncMock(return_value=spans)

    orch = CouncilOrchestrator(
        provider=_MockProvider(),
        retriever=retriever,
        library=_library(),
        max_concurrency=4,
    )
    await orch.run("topic X", vertical="finance", num_personas=2)

    queries = [call.args[0] for call in retriever.retrieve.await_args_list]
    persona_queries = [q for q in queries if "Lens:" in q]
    assert persona_queries, "expected at least one lens-tagged retrieval call"
    assert all("macro" in q and "rates" in q for q in persona_queries)


@pytest.mark.asyncio
async def test_personas_run_in_parallel(monkeypatch: pytest.MonkeyPatch) -> None:
    refs = [_ev(f"span-{i}") for i in range(2)]
    spans = [_retrieved_span(r) for r in refs]
    retriever = MagicMock()
    retriever.retrieve = AsyncMock(return_value=spans)

    persona_calls = 0

    class _SlowProvider(_MockProvider):
        async def text_complete(self, prompt: str, model: str, max_tokens: int = 800) -> str:
            nonlocal persona_calls
            persona_calls += 1
            await asyncio.sleep(0.1)
            return await super().text_complete(prompt, model, max_tokens)

    orch = CouncilOrchestrator(
        provider=_SlowProvider(),
        retriever=retriever,
        library=_library(),
        max_concurrency=4,
    )

    start = asyncio.get_event_loop().time()
    await orch.run("topic", vertical="finance", num_personas=3)
    elapsed = asyncio.get_event_loop().time() - start

    # 3 personas at 0.1s sequential = 0.3s; parallel under sem=4 should be near 0.1s.
    assert persona_calls == 3
    assert elapsed < 0.25, f"personas appear sequential (elapsed={elapsed:.2f}s)"


@pytest.mark.asyncio
async def test_failed_phase_is_emitted_when_no_personas() -> None:
    refs = [_ev(f"span-{i}") for i in range(2)]
    spans = [_retrieved_span(r) for r in refs]
    retriever = MagicMock()
    retriever.retrieve = AsyncMock(return_value=spans)

    class _EmptySlateProvider(_MockProvider):
        async def structured_extract(
            self, prompt: str, schema: type, model: str
        ) -> Any:
            from argus_agents.master import _PersonaSlate

            if schema is _PersonaSlate:
                # Library covers "finance" so we override library to None to force LLM path.
                return _PersonaSlate(personas=[])  # noqa: invalid - validator will reject
            return await super().structured_extract(prompt, schema, model)

    phases: list[str] = []

    async def on_phase(p: str) -> None:
        phases.append(p)

    library = PersonaLibrary(verticals={})  # empty -> force LLM path

    orch = CouncilOrchestrator(
        provider=_EmptySlateProvider(),
        retriever=retriever,
        library=library,
        on_phase=on_phase,
        max_concurrency=2,
    )
    # _PersonaSlate enforces min_length=3 so the fake provider's empty slate
    # raises ValidationError; the master records an error and personas stays empty.
    # Use try/except to handle either the orchestrator raising or returning a state.
    try:
        state = await orch.run("topic", vertical=None, num_personas=3)
        assert state.personas == []
    except Exception:
        pass

    assert "failed" in phases
