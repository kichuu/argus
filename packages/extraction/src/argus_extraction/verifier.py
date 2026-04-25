from argus_core.logging import get_logger
from argus_core.schemas import EvidenceRef, Source

from argus_extraction.schemas import (
    ExtractedClaim,
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
)

logger = get_logger(__name__)


class VerificationError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def verify_span(source: Source, span: str, char_start: int, char_end: int) -> None:
    if char_start < 0 or char_end <= char_start:
        raise VerificationError(
            f"invalid offsets: char_start={char_start}, char_end={char_end}"
        )
    if char_end > len(source.raw_text):
        raise VerificationError(
            f"char_end={char_end} exceeds raw_text length {len(source.raw_text)}"
        )
    actual = source.raw_text[char_start:char_end]
    if actual != span:
        raise VerificationError(
            f"span mismatch: offsets yield {actual!r} but provided span is {span!r}"
        )


def to_evidence_ref(
    source: Source,
    span: str,
    char_start: int,
    char_end: int,
) -> EvidenceRef:
    verify_span(source, span, char_start, char_end)
    return EvidenceRef(
        source_id=source.id,
        verbatim_span=span,
        char_start=char_start,
        char_end=char_end,
        fetched_at=source.fetched_at,
        trust_tier=source.trust_tier,
    )


def verify_extraction(
    source: Source,
    result: ExtractionResult,
) -> tuple[ExtractionResult, list[VerificationError]]:
    errors: list[VerificationError] = []

    kept_claims: list[ExtractedClaim] = []
    for claim in result.claims:
        try:
            verify_span(source, claim.verbatim_span, claim.char_start, claim.char_end)
            kept_claims.append(claim)
        except VerificationError as e:
            errors.append(e)
            logger.warning(
                "claim_span_rejected",
                reason=e.reason,
                statement=claim.statement,
            )

    kept_entities: list[ExtractedEntity] = []
    for entity in result.entities:
        try:
            verify_span(source, entity.verbatim_span, entity.char_start, entity.char_end)
            kept_entities.append(entity)
        except VerificationError as e:
            errors.append(e)
            logger.warning("entity_span_rejected", reason=e.reason, name=entity.name)

    kept_relations: list[ExtractedRelation] = []
    for relation in result.relations:
        try:
            verify_span(
                source, relation.verbatim_span, relation.char_start, relation.char_end
            )
            kept_relations.append(relation)
        except VerificationError as e:
            errors.append(e)
            logger.warning(
                "relation_span_rejected",
                reason=e.reason,
                subject=relation.subject,
                object=relation.object,
            )

    filtered = ExtractionResult(
        claims=kept_claims,
        entities=kept_entities,
        relations=kept_relations,
    )
    return filtered, errors
