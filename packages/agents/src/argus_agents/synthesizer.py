from argus_agents.base import Agent
from argus_agents.state import DiscussionState
from argus_core.logging import get_logger
from argus_core.schemas import AgentRole, Claim, ClaimStatus, EvidenceRef
from argus_core.schemas.claim import AgentConsensus
from argus_extraction.providers import Provider
from pydantic import BaseModel, Field, ValidationError

logger = get_logger(__name__)


class _ProposedClaim(BaseModel):
    statement: str = Field(min_length=1)
    supporting_evidence_ids: list[str] = Field(min_length=1)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    agree: int = 0
    disagree: int = 0
    uncertain: int = 0


class _ClaimSlate(BaseModel):
    claims: list[_ProposedClaim] = Field(default_factory=list)


_SYNTH_PROMPT = """You synthesize the discussion into atomic Claims.
Output ONLY JSON. Each claim:
- statement: a single, verifiable atomic sentence (no prose).
- supporting_evidence_ids: list of evidence UUIDs from the pack that back it.
- contradicting_evidence_ids: list of evidence UUIDs from the pack that contradict it.
- agree / disagree / uncertain: counts across persona messages.

Topic: {topic}

Evidence pack:
{evidence_block}

Persona messages:
{persona_block}

Critic flags:
{critic_block}

Drop any candidate claim that lacks at least one supporting evidence id from the pack."""


class SynthesizerAgent(Agent):
    def __init__(self, provider: Provider, model: str) -> None:
        super().__init__(AgentRole.SYNTHESIZER, model)
        self.provider = provider

    async def step(self, state: DiscussionState) -> DiscussionState:
        pack = state.evidence_pack
        evidence_by_id: dict[str, EvidenceRef] = {
            str(e.source_id): e for e in pack.evidence
        }

        evidence_block = "\n".join(
            f"- [ev:{e.source_id}] {e.verbatim_span!r}" for e in pack.evidence
        ) or "(no evidence)"

        persona_msgs = [m for m in state.messages if m.role == AgentRole.PERSONA]
        critic_msgs = [m for m in state.messages if m.role == AgentRole.CRITIC]

        persona_block = "\n".join(
            f"- ({m.persona_id}) {m.content}" for m in persona_msgs
        ) or "(no persona messages)"
        critic_block = "\n".join(m.content for m in critic_msgs) or "(no critic flags)"

        prompt = _SYNTH_PROMPT.format(
            topic=state.topic,
            evidence_block=evidence_block,
            persona_block=persona_block,
            critic_block=critic_block,
        )

        try:
            slate = await self.provider.structured_extract(prompt, _ClaimSlate, self.model)
        except Exception as e:
            logger.error("synth_llm_failed", error=str(e))
            state.errors.append(f"synthesizer: {e}")
            return state

        if not isinstance(slate, _ClaimSlate):
            state.errors.append("synthesizer: provider returned wrong type")
            return state

        critic_flagged_ids: set[str] = set()
        for cmsg in critic_msgs:
            for ref in cmsg.evidence_refs:
                critic_flagged_ids.add(str(ref.source_id))

        claims: list[Claim] = []
        for prop in slate.claims:
            supporting = [
                evidence_by_id[eid]
                for eid in prop.supporting_evidence_ids
                if eid in evidence_by_id
            ]
            if not supporting:
                logger.warning("synth_claim_no_evidence", statement=prop.statement)
                continue

            contradicting = [
                evidence_by_id[eid]
                for eid in prop.contradicting_evidence_ids
                if eid in evidence_by_id
            ]

            total = max(prop.agree + prop.disagree + prop.uncertain, 1)
            confidence = prop.agree / total
            has_critic_hit = any(
                str(s.source_id) in critic_flagged_ids for s in supporting
            )
            if has_critic_hit:
                confidence = min(confidence, 0.5)

            if contradicting or prop.disagree > prop.agree:
                status = ClaimStatus.CONTESTED
            elif has_critic_hit:
                status = ClaimStatus.UNVERIFIED
            elif prop.agree >= 2 and prop.disagree == 0:
                status = ClaimStatus.LIKELY_TRUE
            else:
                status = ClaimStatus.UNVERIFIED

            try:
                claim = Claim(
                    statement=prop.statement,
                    status=status,
                    confidence=max(0.0, min(1.0, confidence)),
                    supporting_evidence=supporting,
                    contradicting_evidence=contradicting,
                    affected_entities=list(pack.entities),
                    agent_consensus=AgentConsensus(
                        agree=prop.agree,
                        disagree=prop.disagree,
                        uncertain=prop.uncertain,
                    ),
                )
            except ValidationError as ve:
                logger.warning("synth_claim_invalid", error=str(ve))
                state.errors.append(f"synthesizer: {ve}")
                continue
            claims.append(claim)

        state.final_claims = claims
        logger.info("synth_claims_built", count=len(claims))
        return state
