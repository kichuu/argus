from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from argus_core.db.models import ClaimModel, EntityModel, RelationModel, SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import ClaimStatus, EvidenceRef, Source
from argus_core.settings import get_settings
from argus_extraction.extractor import ClaimExtractor
from argus_extraction.providers import get_provider
from argus_extraction.schemas import ExtractionResult
from argus_extraction.verifier import verify_extraction
from sqlalchemy import select
from temporalio import activity

logger = get_logger(__name__)


def _source_model_to_pydantic(model: SourceModel) -> Source:
    return Source(
        id=model.id,
        url=model.url,  # type: ignore[arg-type]
        feed_url=model.feed_url,  # type: ignore[arg-type]
        title=model.title,
        content_hash=model.content_hash,
        raw_text=model.raw_text,
        fetched_at=model.fetched_at,
        published_at=model.published_at,
        license=model.license,
        trust_tier=model.trust_tier,
        publisher=model.publisher,
        language=model.language,
    )


@activity.defn
async def extract_claims(source_id: str) -> list[str]:
    sid = UUID(source_id)
    settings = get_settings()

    async with session_scope() as session:
        source_row = await session.get(SourceModel, sid)
        if source_row is None:
            logger.warning("extract_claims.missing_source", source_id=source_id)
            return []
        source = _source_model_to_pydantic(source_row)

    provider = get_provider("openai")
    extractor = ClaimExtractor(provider=provider, model=settings.default_extractor_model)
    raw_result = await extractor.extract(source)
    verified, errors = verify_extraction(source, raw_result)
    if errors:
        logger.info(
            "extract_claims.span_errors",
            source_id=source_id,
            kept=len(verified.claims),
            dropped=len(errors),
        )

    persisted_ids: list[str] = []
    if not verified.claims and not verified.entities:
        return persisted_ids

    async with session_scope() as session:
        # 1. Upsert entities first (dedupe by canonical_name + entity_type) so
        #    claims can reference them by UUID.
        entity_id_by_name: dict[str, str] = {}
        for ee in verified.entities:
            existing = await session.execute(
                select(EntityModel).where(
                    EntityModel.canonical_name == ee.name,
                    EntityModel.entity_type == ee.entity_type.value,
                )
            )
            row = existing.scalar_one_or_none()
            if row is None:
                row = EntityModel(
                    id=uuid4(),
                    canonical_name=ee.name,
                    entity_type=ee.entity_type.value,
                    aliases=[],
                )
                session.add(row)
                await session.flush()
            entity_id_by_name[ee.name] = str(row.id)

        # 2. Persist relations between known entities; skip if either side
        #    didn't survive entity verification.
        for er in verified.relations:
            sid = entity_id_by_name.get(er.subject)
            oid = entity_id_by_name.get(er.object)
            if not sid or not oid:
                continue
            session.add(
                RelationModel(
                    id=uuid4(),
                    subject_id=UUID(sid),
                    relation_type=er.relation_type.value,
                    object_id=UUID(oid),
                    evidence=[
                        {
                            "source_id": str(source.id),
                            "verbatim_span": er.verbatim_span,
                            "char_start": er.char_start,
                            "char_end": er.char_end,
                        }
                    ],
                    confidence=0.0,
                )
            )

        # 3. Persist claims, mapping mentioned-entity names to the canonical
        #    entity UUIDs we just upserted (fall back to the raw name for
        #    entities the LLM mentioned but didn't extract as a typed entity).
        for ec in verified.claims:
            evidence = EvidenceRef(
                source_id=source.id,
                verbatim_span=ec.verbatim_span,
                char_start=ec.char_start,
                char_end=ec.char_end,
                fetched_at=source.fetched_at,
                trust_tier=source.trust_tier,
            )
            affected = [
                entity_id_by_name.get(name, name) for name in ec.entities_mentioned
            ]
            claim = ClaimModel(
                id=uuid4(),
                statement=ec.statement,
                status=ClaimStatus.UNVERIFIED.value,
                confidence=0.0,
                supporting_evidence=[evidence.model_dump(mode="json")],
                contradicting_evidence=[],
                affected_entities=affected,
                agent_consensus={},
            )
            session.add(claim)
            persisted_ids.append(str(claim.id))

    logger.info(
        "extract_claims.done",
        source_id=source_id,
        claims=len(persisted_ids),
        entities=len(verified.entities),
        relations=len(verified.relations),
    )
    return persisted_ids
