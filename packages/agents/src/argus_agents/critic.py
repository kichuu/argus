from argus_core.logging import get_logger
from argus_core.schemas import AgentMessage, AgentRole
from argus_core.settings import get_settings
from argus_extraction.providers import Provider, family_of
from pydantic import BaseModel, Field

from argus_agents.base import _EV_PATTERN, Agent
from argus_agents.state import DiscussionState

logger = get_logger(__name__)


class _CriticVerdict(BaseModel):
    evidence_id: str
    assertion: str
    verdict: str = Field(description="one of: yes, no, partial")
    reason: str = ""


class _CriticReport(BaseModel):
    verdicts: list[_CriticVerdict] = Field(default_factory=list)


_CRITIC_PROMPT = """You audit whether each cited evidence span supports the assertion
that cites it. The standard is "reasonable grounding", not "definitive proof" — a
forecast / analyst projection / news report can support an assertion that paraphrases
or summarizes its content.

For every (assertion, evidence) pair below, return a verdict:
- "yes": span supports the assertion (the assertion is a fair paraphrase, summary,
  or reasonable inference from the span).
- "partial": span is topically related but the assertion goes beyond what the span
  warrants (overclaims, adds unstated specifics, or only partly overlaps).
- "no": span is unrelated, or directly contradicts the assertion.

Pairs to audit:
{pairs}

Return JSON. When the assertion clearly hedges ("forecasts indicate", "analysts
expect", "is projected to") and the span actually contains a forecast/analysis on
that topic, return "yes". Reserve "no" for unrelated content or outright contradiction."""


class CriticAgent(Agent):
    def __init__(
        self,
        provider: Provider,
        model: str | None = None,
        extractor_family: str = "",
    ) -> None:
        resolved_model = model or get_settings().default_critic_model
        super().__init__(AgentRole.CRITIC, resolved_model)
        # Critic shares vendor with extractor under the openai-only build. The
        # hard same-class rule lives on AdversarialVerifier (verifier-style
        # assertion). Critic reasons over already-verified evidence, so we only
        # warn when its class matches the extractor.
        critic_class = family_of(resolved_model).lower()
        ext_class = extractor_family.lower()
        if ext_class and critic_class == ext_class:
            logger.warning(
                "critic_extractor_same_class",
                critic_class=critic_class,
                extractor_class=ext_class,
            )
        self.provider = provider
        self.extractor_family = ext_class

    async def step(self, state: DiscussionState) -> DiscussionState:
        evidence_by_id = {str(e.source_id): e for e in state.evidence_pack.evidence}

        pairs: list[tuple[str, str, str]] = []
        for msg in state.messages:
            if msg.role != AgentRole.PERSONA:
                continue
            for sentence in msg.content.split(". "):
                sentence = sentence.strip()
                if not sentence:
                    continue
                for eid in _EV_PATTERN.findall(sentence):
                    span = evidence_by_id.get(eid.lower()) or evidence_by_id.get(eid)
                    if span is None:
                        continue
                    pairs.append((eid, sentence, span.verbatim_span))

        # Always emit at least one critic message so downstream consumers see
        # an audit trail entry even when there are no persona citations to audit.
        if not pairs:
            logger.info("critic_no_pairs")
            state.messages.append(
                AgentMessage(
                    discussion_id=state.discussion_id,
                    agent_id="critic",
                    role=AgentRole.CRITIC,
                    content="Critic audit: 0 (assertion, evidence) pairs to review.",
                    evidence_refs=[],
                )
            )
            return state

        pairs_block = "\n".join(
            f"{i + 1}. assertion: {a!r}\n   evidence_id: {eid}\n   span: {sp!r}"
            for i, (eid, a, sp) in enumerate(pairs)
        )
        prompt = _CRITIC_PROMPT.format(pairs=pairs_block)

        report: _CriticReport | None = None
        try:
            result = await self.provider.structured_extract(prompt, _CriticReport, self.model)
            if isinstance(result, _CriticReport):
                report = result
            else:
                state.errors.append("critic: provider returned wrong type")
        except Exception as e:
            logger.error("critic_llm_failed", error=str(e))
            state.errors.append(f"critic: {e}")

        verdicts = report.verdicts if report is not None else []
        rejected = [v for v in verdicts if v.verdict.lower() == "no"]
        partial = [v for v in verdicts if v.verdict.lower() == "partial"]
        flagged = rejected + partial

        summary_lines = [
            f"Critic audit: {len(flagged)}/{len(pairs)} pairs flagged "
            f"({len(rejected)} rejected, {len(partial)} partial)."
        ]
        for v in flagged:
            summary_lines.append(
                f"- [{v.verdict}] [ev:{v.evidence_id}] :: {v.assertion!r} -- {v.reason}"
            )
        # Tag rejected evidence ids with a machine-readable marker so the
        # synthesizer can drop any candidate claim that relies on them.
        if rejected:
            ids_marker = ",".join(v.evidence_id for v in rejected)
            summary_lines.append(f"REJECTED_EVIDENCE_IDS: {ids_marker}")
        summary = "\n".join(summary_lines)

        cited_refs = [
            evidence_by_id[v.evidence_id]
            for v in flagged
            if v.evidence_id in evidence_by_id
        ]

        state.messages.append(
            AgentMessage(
                discussion_id=state.discussion_id,
                agent_id="critic",
                role=AgentRole.CRITIC,
                content=summary,
                evidence_refs=cited_refs,
            )
        )
        return state
