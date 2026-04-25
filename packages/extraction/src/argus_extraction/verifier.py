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


def heal_span(
    source: Source, span: str, char_start: int, char_end: int
) -> tuple[int, int] | None:
    """Try to locate `span` in `source.raw_text`; return corrected (start, end) or None.

    LLMs reliably produce verbatim spans but unreliably produce char offsets — they
    drift by a few chars or truncate. We trust the span and search for it. If the
    span is unique in the source we accept the unique position; otherwise we pick
    the occurrence closest to the model-claimed offsets.
    """
    if not span:
        return None
    text = source.raw_text
    occurrences: list[int] = []
    pos = text.find(span)
    while pos != -1:
        occurrences.append(pos)
        pos = text.find(span, pos + 1)
    if not occurrences:
        return None
    if len(occurrences) == 1:
        start = occurrences[0]
        return start, start + len(span)
    # Disambiguate by proximity to the model's claimed start.
    best = min(occurrences, key=lambda p: abs(p - char_start))
    return best, best + len(span)


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


def _heal_or_drop(
    source: Source,
    span: str,
    char_start: int,
    char_end: int,
    kind: str,
    label: str,
    errors: list[VerificationError],
) -> tuple[int, int] | None:
    """Try strict verify; on failure attempt heal_span; log + return None if drop."""
    try:
        verify_span(source, span, char_start, char_end)
        return char_start, char_end
    except VerificationError as e:
        healed = heal_span(source, span, char_start, char_end)
        if healed is not None:
            logger.info(
                f"{kind}_span_healed",
                label=label,
                old=(char_start, char_end),
                new=healed,
            )
            return healed
        errors.append(e)
        logger.warning(f"{kind}_span_rejected", reason=e.reason, label=label)
        return None


def verify_extraction(
    source: Source,
    result: ExtractionResult,
) -> tuple[ExtractionResult, list[VerificationError]]:
    errors: list[VerificationError] = []

    kept_claims: list[ExtractedClaim] = []
    for claim in result.claims:
        offsets = _heal_or_drop(
            source, claim.verbatim_span, claim.char_start, claim.char_end,
            "claim", claim.statement, errors,
        )
        if offsets is None:
            continue
        kept_claims.append(claim.model_copy(update={"char_start": offsets[0], "char_end": offsets[1]}))

    kept_entities: list[ExtractedEntity] = []
    for entity in result.entities:
        offsets = _heal_or_drop(
            source, entity.verbatim_span, entity.char_start, entity.char_end,
            "entity", entity.name, errors,
        )
        if offsets is None:
            continue
        kept_entities.append(entity.model_copy(update={"char_start": offsets[0], "char_end": offsets[1]}))

    kept_relations: list[ExtractedRelation] = []
    for relation in result.relations:
        label = f"{relation.subject} -[{relation.relation_type}]-> {relation.object}"
        offsets = _heal_or_drop(
            source, relation.verbatim_span, relation.char_start, relation.char_end,
            "relation", label, errors,
        )
        if offsets is None:
            continue
        kept_relations.append(relation.model_copy(update={"char_start": offsets[0], "char_end": offsets[1]}))

    filtered = ExtractionResult(
        claims=kept_claims,
        entities=kept_entities,
        relations=kept_relations,
    )
    return filtered, errors
