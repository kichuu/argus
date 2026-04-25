from __future__ import annotations

from typing import Any
from uuid import UUID

from argus_core.db.models import ClaimModel, SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import ClaimStatus, EvidenceRef
from argus_core.settings import get_settings
from argus_extraction.adversarial import AdversarialVerifier
from argus_extraction.providers import class_of, get_provider
from temporalio import activity

logger = get_logger(__name__)


def _confidence_from_verdicts(verdicts: list[str]) -> tuple[ClaimStatus, float]:
    if not verdicts:
        return ClaimStatus.UNVERIFIED, 0.0
    if all(v == "supports" for v in verdicts):
        return ClaimStatus.LIKELY_TRUE, 0.9
    if any(v == "no" for v in verdicts):
        return ClaimStatus.CONTESTED, 0.3
    return ClaimStatus.CONTESTED, 0.6


@activity.defn
async def verify_claims(claim_ids: list[str]) -> dict[str, Any]:
    if not claim_ids:
        return {"verified": 0, "claim_ids": [], "verdicts": {}}

    settings = get_settings()
    extractor_class = class_of(settings.default_extractor_model)
    verifier_provider = get_provider("openai")
    verifier = AdversarialVerifier(
        verifier_provider=verifier_provider,
        extractor_model_class=extractor_class,
        model=settings.default_verifier_model,
    )

    verdicts_by_claim: dict[str, list[str]] = {}
    verified_count = 0

    for cid in claim_ids:
        cuuid = UUID(cid)
        async with session_scope() as session:
            claim = await session.get(ClaimModel, cuuid)
            if claim is None:
                logger.warning("verify_claims.missing_claim", claim_id=cid)
                continue

            evidence_refs = [
                EvidenceRef.model_validate(e) for e in claim.supporting_evidence
            ]
            if not evidence_refs:
                continue

            source_id = evidence_refs[0].source_id
            source_row = await session.get(SourceModel, source_id)
            if source_row is None:
                logger.warning("verify_claims.missing_source", claim_id=cid)
                continue

            from argus_workers.activities.extract import _source_model_to_pydantic

            source = _source_model_to_pydantic(source_row)
            verdicts: list[str] = []
            for ev in evidence_refs:
                try:
                    v = await verifier.verdict(source, claim.statement, ev)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "verify_claims.verdict_failed",
                        claim_id=cid,
                        error=str(exc),
                    )
                    v = "no"
                verdicts.append(v)

            status, confidence = _confidence_from_verdicts(verdicts)
            claim.status = status.value
            claim.confidence = confidence
            verdicts_by_claim[cid] = verdicts
            if status == ClaimStatus.LIKELY_TRUE:
                verified_count += 1

    logger.info(
        "verify_claims.done",
        total=len(claim_ids),
        likely_true=verified_count,
    )
    return {
        "verified": verified_count,
        "claim_ids": claim_ids,
        "verdicts": verdicts_by_claim,
    }
