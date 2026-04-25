"""Flat-asyncio multi-agent orchestrator. Replaces the LangGraph DiscussionGraph.

Phases (each emits via on_status / on_post / on_phase / on_claim callbacks):
  1. researching   - ResearchAgent assembles the base evidence pack.
  2. planning      - MasterAgent picks N personas (library-first, LLM-fallback).
  3. debating      - For each persona: lens query -> per-persona retrieve -> generate post.
                     Personas fan out in parallel under a Semaphore.
  4. criticizing   - CriticAgent flags unsupported / disputed citations.
  5. synthesizing  - SynthesizerAgent emits structured Claims from evidence + posts + flags.
  6. completed (or failed)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID, uuid4

from argus_core.logging import get_logger
from argus_core.personas import PersonaLibrary, load_persona_library
from argus_core.schemas import AgentMessage, Claim, EvidenceRef, Persona
from argus_core.settings import get_settings
from argus_extraction.providers import Provider, family_of

from argus_agents.critic import CriticAgent
from argus_agents.master import MasterAgent
from argus_agents.persona import PersonaAgent
from argus_agents.research import ResearchAgent
from argus_agents.state import DiscussionState, EvidencePack
from argus_agents.synthesizer import SynthesizerAgent

logger = get_logger(__name__)


EmitPost = Callable[[AgentMessage], Awaitable[None]]
EmitStatus = Callable[[str, str, dict], Awaitable[None]]
EmitPhase = Callable[[str], Awaitable[None]]
EmitClaim = Callable[[Claim], Awaitable[None]]


def _span_to_ref(span: Any) -> EvidenceRef | None:
    try:
        return EvidenceRef(
            source_id=span.source_id,
            verbatim_span=span.verbatim_span,
            char_start=span.char_start,
            char_end=span.char_end,
            fetched_at=span.fetched_at,
            trust_tier=span.trust_tier,
        )
    except Exception as exc:  # span shape mismatch or invariant violation
        logger.warning("orchestrator_span_rejected", error=str(exc))
        return None


class CouncilOrchestrator:
    def __init__(
        self,
        provider: Provider,
        retriever: Any,
        library: PersonaLibrary | None = None,
        *,
        on_post: EmitPost | None = None,
        on_status: EmitStatus | None = None,
        on_phase: EmitPhase | None = None,
        on_claim: EmitClaim | None = None,
        master_model: str | None = None,
        persona_model: str | None = None,
        critic_model: str | None = None,
        synthesis_model: str | None = None,
        research_model: str | None = None,
        extractor_family: str = "gpt",
        max_concurrency: int = 6,
        persona_top_k: int = 6,
        master_top_k: int = 24,
    ) -> None:
        settings = get_settings()
        self.provider = provider
        self.retriever = retriever
        self.library = library if library is not None else load_persona_library()
        self.on_post = on_post
        self.on_status = on_status
        self.on_phase = on_phase
        self.on_claim = on_claim
        self.master_model = master_model or settings.default_master_model
        self.persona_model = persona_model or settings.default_persona_model
        self.critic_model = critic_model or settings.default_critic_model
        self.synthesis_model = synthesis_model or settings.default_synthesis_model
        self.research_model = research_model or settings.default_research_model
        self.extractor_family = extractor_family
        self.persona_top_k = persona_top_k
        self.master_top_k = master_top_k
        self._sem = asyncio.Semaphore(max_concurrency)

    async def _emit_phase(self, phase: str) -> None:
        logger.info("orch_phase", phase=phase)
        if self.on_phase is not None:
            await self.on_phase(phase)

    async def _emit_status(self, agent_id: str, state: str, extra: dict | None = None) -> None:
        if self.on_status is not None:
            await self.on_status(agent_id, state, extra or {})

    async def _emit_post(self, msg: AgentMessage) -> None:
        if self.on_post is not None:
            await self.on_post(msg)

    async def _emit_claim(self, claim: Claim) -> None:
        if self.on_claim is not None:
            await self.on_claim(claim)

    async def run(
        self,
        topic: str,
        vertical: str | None = None,
        num_personas: int = 3,
        discussion_id: UUID | None = None,
    ) -> DiscussionState:
        state = DiscussionState(
            discussion_id=discussion_id or uuid4(),
            topic=topic,
            evidence_pack=EvidencePack(topic=topic, vertical=vertical),
        )

        try:
            await self._emit_phase("researching")
            await self._emit_status("research", "thinking", {})
            await ResearchAgent(self.retriever, self.research_model, top_k=self.master_top_k).step(
                state
            )
            await self._emit_status("research", "done", {"n_evidence": len(state.evidence_pack.evidence)})

            await self._emit_phase("planning")
            await self._emit_status("master", "thinking", {})
            await MasterAgent(self.provider, self.master_model, library=self.library).step(state)
            state.personas = state.personas[:num_personas]
            await self._emit_status(
                "master", "done", {"n_personas": len(state.personas), "vertical": vertical}
            )
            if not state.personas:
                state.errors.append("orchestrator: no personas selected")
                await self._emit_phase("failed")
                return state

            await self._emit_phase("debating")
            await self._run_personas(state)

            await self._emit_phase("criticizing")
            await self._emit_status("critic", "thinking", {})
            critic_msg_count_before = len(state.messages)
            await CriticAgent(
                self.provider, self.critic_model, self.extractor_family
            ).step(state)
            for msg in state.messages[critic_msg_count_before:]:
                await self._emit_post(msg)
            await self._emit_status("critic", "done", {})

            await self._emit_phase("synthesizing")
            await self._emit_status("synth", "thinking", {})
            await SynthesizerAgent(self.provider, self.synthesis_model).step(state)
            for claim in state.final_claims:
                await self._emit_claim(claim)
            await self._emit_status("synth", "done", {"n_claims": len(state.final_claims)})

            await self._emit_phase("completed")
        except Exception as exc:
            logger.exception("orchestrator_failed", error=str(exc))
            state.errors.append(f"orchestrator: {exc}")
            await self._emit_phase("failed")
            raise

        return state

    async def _run_personas(self, state: DiscussionState) -> None:
        async def call_one(persona: Persona) -> None:
            agent_id = f"persona:{persona.id}"
            async with self._sem:
                await self._emit_status(
                    agent_id, "thinking", {"frame": persona.frame}
                )
                try:
                    evidence = await self._retrieve_for_persona(state.topic, persona)
                    if not evidence:
                        evidence = list(state.evidence_pack.evidence)

                    sub_state = DiscussionState(
                        discussion_id=state.discussion_id,
                        topic=state.topic,
                        evidence_pack=EvidencePack(
                            topic=state.topic,
                            vertical=state.evidence_pack.vertical,
                            evidence=evidence,
                        ),
                    )
                    sub_state = await PersonaAgent(
                        persona, self.provider, self.persona_model
                    ).step(sub_state)

                    for msg in sub_state.messages:
                        state.messages.append(msg)
                        await self._emit_post(msg)
                    state.errors.extend(sub_state.errors)

                    await self._emit_status(
                        agent_id, "done", {"n_messages": len(sub_state.messages)}
                    )
                except Exception as exc:
                    logger.exception(
                        "orch_persona_failed", frame=persona.frame, error=str(exc)
                    )
                    state.errors.append(f"persona[{persona.frame}]: {exc}")
                    await self._emit_status(agent_id, "error", {"error": str(exc)})
                    raise

        tasks = [call_one(p) for p in state.personas]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        n_fail = sum(1 for r in results if isinstance(r, Exception))
        if n_fail == len(state.personas):
            raise RuntimeError("all personas failed")
        if n_fail:
            logger.warning("orch_personas_partial_failure", n_fail=n_fail, n_total=len(state.personas))

    async def _retrieve_for_persona(self, topic: str, persona: Persona) -> list[EvidenceRef]:
        lens = ", ".join(persona.knowledge_emphasis) if persona.knowledge_emphasis else persona.frame
        query = f"{topic}\nLens: {lens}"
        try:
            spans = await self.retriever.retrieve(query, top_k=self.persona_top_k)
        except Exception as exc:
            logger.warning("orch_persona_retrieve_failed", frame=persona.frame, error=str(exc))
            return []
        refs: list[EvidenceRef] = []
        for span in spans:
            ref = _span_to_ref(span)
            if ref is not None:
                refs.append(ref)
        return refs


def _family_of_extractor() -> str:
    return family_of(get_settings().default_extractor_model)
