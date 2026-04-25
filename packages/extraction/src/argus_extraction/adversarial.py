from typing import Literal

from argus_core.logging import get_logger
from argus_core.schemas import EvidenceRef, Source
from argus_core.settings import get_settings

from argus_extraction.providers.base import Provider

logger = get_logger(__name__)

Verdict = Literal["supports", "partial", "no"]


_PROMPT = """\
You are an adversarial verifier. Decide whether the EVIDENCE SPAN, taken alone and
verbatim, supports the CLAIM. You must NOT use outside knowledge or inference beyond
what the span literally says.

CLAIM:
{claim}

EVIDENCE SPAN (verbatim, no other context):
{span}

Answer with EXACTLY one lowercase token on its own line:
- "supports" if the span directly and unambiguously asserts the claim.
- "partial"  if the span is consistent with but does not fully assert the claim.
- "no"       if the span does not support the claim or contradicts it.

Output only the single token. No explanation.
"""


class AdversarialVerifier:
    def __init__(
        self,
        verifier_provider: Provider,
        extractor_family: str,
        model: str | None = None,
    ) -> None:
        if verifier_provider.name == extractor_family:
            raise ValueError(
                "verifier must be from a different family than extractor "
                f"(both are {extractor_family!r})"
            )
        self._provider = verifier_provider
        self._model = model or get_settings().default_verifier_model

    async def verdict(
        self,
        source: Source,
        claim_statement: str,
        evidence: EvidenceRef,
    ) -> Verdict:
        if evidence.source_id != source.id:
            raise ValueError("evidence.source_id does not match source.id")

        prompt = _PROMPT.format(claim=claim_statement, span=evidence.verbatim_span)
        raw = await self._provider.text_complete(
            prompt=prompt,
            model=self._model,
            max_tokens=8,
        )
        token = raw.strip().splitlines()[0].strip().strip(".\"'`").lower() if raw.strip() else ""
        if token not in ("supports", "partial", "no"):
            logger.warning("adversarial_unparseable_verdict", raw=raw)
            return "no"
        return token  # type: ignore[return-value]
