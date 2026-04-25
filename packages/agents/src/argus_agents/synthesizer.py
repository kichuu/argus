import re

from argus_core.logging import get_logger
from argus_core.schemas import AgentMessage, AgentRole, Claim, ClaimStatus, EvidenceRef
from argus_core.schemas.claim import AgentConsensus
from argus_core.settings import get_settings
from argus_extraction.providers import Provider
from pydantic import BaseModel, Field, ValidationError

from argus_agents.base import Agent
from argus_agents.state import DiscussionState

logger = get_logger(__name__)

_REJECTED_RE = re.compile(r"REJECTED_EVIDENCE_IDS:\s*([^\n]+)")


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
    def __init__(self, provider: Provider, model: str | None = None) -> None:
        super().__init__(AgentRole.SYNTHESIZER, model or get_settings().default_synthesis_model)
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

        # Critic flagged-but-not-rejected evidence (partial verdicts) and a
        # hard-rejected set parsed from the structured marker the critic
        # leaves in its message body.
        critic_flagged_ids: set[str] = set()
        rejected_ids: set[str] = set()
        for cmsg in critic_msgs:
            for ref in cmsg.evidence_refs:
                critic_flagged_ids.add(str(ref.source_id))
            for match in _REJECTED_RE.finditer(cmsg.content):
                for eid in match.group(1).split(","):
                    eid_clean = eid.strip()
                    if eid_clean:
                        rejected_ids.add(eid_clean)

        claims: list[Claim] = []
        for prop in slate.claims:
            # Drop claims whose supporting evidence was rejected outright by
            # the critic; those are "no" verdicts per the protocol.
            supporting_ids = [
                eid
                for eid in prop.supporting_evidence_ids
                if eid in evidence_by_id and eid not in rejected_ids
            ]
            supporting = [evidence_by_id[eid] for eid in supporting_ids]
            if not supporting:
                logger.warning("synth_claim_no_evidence", statement=prop.statement)
                continue

            contradicting = [
                evidence_by_id[eid]
                for eid in prop.contradicting_evidence_ids
                if eid in evidence_by_id
            ]

            total = max(prop.agree + prop.disagree + prop.uncertain, 1)
            agree_share = prop.agree / total
            partial_hit = any(
                str(s.source_id) in critic_flagged_ids for s in supporting
            )

            # Calibrated confidence: weight by consensus *and* evidence count,
            # then haircut for partial critic verdicts and contradictions.
            evidence_factor = min(len(supporting) / 3.0, 1.0)
            base = 0.4 + 0.4 * agree_share + 0.2 * evidence_factor
            if partial_hit:
                base -= 0.25
            if contradicting:
                base -= 0.2
            confidence = max(0.05, min(0.9, base))

            if contradicting or prop.disagree > prop.agree:
                status = ClaimStatus.CONTESTED
            elif partial_hit:
                status = ClaimStatus.UNVERIFIED
            elif (
                prop.agree >= 2
                and prop.disagree == 0
                and len(supporting) >= 2
            ):
                status = ClaimStatus.LIKELY_TRUE
            else:
                status = ClaimStatus.UNVERIFIED

            try:
                claim = Claim(
                    statement=prop.statement,
                    status=status,
                    confidence=confidence,
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

        # Always append a synthesizer message so the discussion transcript has
        # a closing entry even when no claims survive evidence gating.
        if claims:
            digest_lines = [f"Synthesizer produced {len(claims)} claim(s)."]
            for c in claims[:5]:
                digest_lines.append(
                    f"- ({c.status.value}, conf={c.confidence:.2f}) {c.statement}"
                )
            digest = "\n".join(digest_lines)
            digest_refs: list[EvidenceRef] = []
            seen: set[str] = set()
            for c in claims:
                for ev in c.supporting_evidence:
                    key = str(ev.source_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    digest_refs.append(ev)
        else:
            digest = "Synthesizer produced 0 claims (no candidates survived evidence gating)."
            digest_refs = []

        state.messages.append(
            AgentMessage(
                discussion_id=state.discussion_id,
                agent_id="synthesizer",
                role=AgentRole.SYNTHESIZER,
                content=digest,
                evidence_refs=digest_refs,
            )
        )
        logger.info("synth_claims_built", count=len(claims))
        return state
