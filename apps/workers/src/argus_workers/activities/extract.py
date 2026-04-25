from argus_core.logging import get_logger
from temporalio import activity

logger = get_logger(__name__)


@activity.defn
async def extract_claims(source_id: str) -> list[str]:
    # TODO(extraction): load SourceModel via session_scope(), run ClaimExtractor
    # from argus_extraction.extractor, run verify_extraction for span integrity,
    # persist resulting Claim rows via ClaimModel and return their UUID strings.
    logger.info("extract_claims.stub", source_id=source_id)
    return []
