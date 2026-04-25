from argus_core.logging import get_logger
from argus_core.schemas import Source
from argus_core.settings import get_settings

from argus_extraction.providers.base import Provider
from argus_extraction.schemas import ExtractionResult

logger = get_logger(__name__)


_PROMPT_TEMPLATE = """\
You extract verifiable claims, entities, and relations from a single source document.

CRITICAL RULES (any violation invalidates the output):
1. Every claim, entity, and relation MUST include a `verbatim_span` that is an EXACT
   substring of the source text below. Do not paraphrase, normalize whitespace, or
   change punctuation in the span.
2. `char_start` and `char_end` are 0-based offsets into the source text such that
   source_text[char_start:char_end] == verbatim_span. They MUST satisfy this exactly.
3. `statement` (for claims) may be your own concise rewriting; `verbatim_span` must
   remain the exact source substring that supports it.
4. Use `entity_type` from: person, org, place, event, policy, product, concept.
5. Use `relation_type` from: employed_by, located_in, part_of, participated_in,
   owns, authored, opposes, supports, caused, related_to.
6. If you are unsure whether a span is exact, OMIT the item rather than guess.

SOURCE TEXT (offsets are over this exact string):
<<<SOURCE
{source_text}
SOURCE>>>
"""


class ClaimExtractor:
    def __init__(self, provider: Provider, model: str | None = None) -> None:
        self._provider = provider
        self._model = model or get_settings().default_extractor_model

    async def extract(self, source: Source) -> ExtractionResult:
        prompt = _PROMPT_TEMPLATE.format(source_text=source.raw_text)
        result = await self._provider.structured_extract(
            prompt=prompt,
            schema=ExtractionResult,
            model=self._model,
        )
        if not isinstance(result, ExtractionResult):
            raise RuntimeError(
                f"provider returned {type(result).__name__}, expected ExtractionResult"
            )
        logger.info(
            "extraction_completed",
            source_id=str(source.id),
            model=self._model,
            claims=len(result.claims),
            entities=len(result.entities),
            relations=len(result.relations),
        )
        return result
