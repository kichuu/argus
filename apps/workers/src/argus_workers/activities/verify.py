from typing import Any

from temporalio import activity

from argus_core.logging import get_logger

logger = get_logger(__name__)


@activity.defn
async def verify_claims(claim_ids: list[str]) -> dict[str, Any]:
    # TODO(extraction): instantiate AdversarialVerifier (cross-family, e.g. OpenAI
    # verifier over Claude extractor output) for each claim, update ClaimModel.status
    # and confidence based on agreement.
    logger.info("verify_claims.stub", count=len(claim_ids))
    return {"verified": 0, "claim_ids": claim_ids}
