"""GET /suggested-topics — LLM-suggested debate prompts grounded in recent claims.

Module-level in-memory cache (5-minute TTL) avoids burning tokens on every
page load. On LLM failure or zero claims, returns an empty topic list and
the frontend falls back to a static mock list.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from argus_core.db.models import ClaimModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.settings import get_settings
from argus_extraction.providers import get_provider
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

logger = get_logger(__name__)

router = APIRouter(tags=["suggested"])

# Module-level cache. The TTL is 5 minutes; do not change without updating docs.
_CACHE_TTL = timedelta(seconds=300)
_CACHE: dict[str, Any] | None = None
_CACHE_AT: datetime | None = None


class SuggestedTopic(BaseModel):
    id: str
    title: str
    rationale: str = ""


class SuggestedTopicsResponse(BaseModel):
    topics: list[SuggestedTopic] = Field(default_factory=list)
    generated_at: datetime
    claim_basis_count: int = 0
    error: str | None = None


# Internal Pydantic schemas the LLM fills.
class _Topic(BaseModel):
    id: str
    title: str = Field(min_length=1)
    rationale: str = ""


class _TopicSlate(BaseModel):
    topics: list[_Topic] = Field(default_factory=list)


def _now() -> datetime:
    return datetime.now(UTC)


def _is_fresh(at: datetime | None) -> bool:
    if at is None:
        return False
    return (_now() - at) < _CACHE_TTL


def _first_evidence_snippet(supporting_evidence: list[dict[str, Any]] | None) -> str:
    if not supporting_evidence:
        return ""
    first = supporting_evidence[0]
    if not isinstance(first, dict):
        return ""
    for key in ("text", "span", "quote", "snippet", "content"):
        val = first.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()[:240]
    return ""


def _build_prompt(claim_lines: list[str]) -> str:
    numbered = "\n".join(f"{i + 1}. {line}" for i, line in enumerate(claim_lines))
    return (
        "You are an analyst suggesting 5 sharply-worded debate questions a "
        "geopolitics analyst would want answered TODAY, grounded in the recent "
        "claims below. Each question should be:\n"
        "- A single sentence ending with a question mark\n"
        "- Forward-looking (not factual recap)\n"
        "- Specific enough that personas can take different positions\n\n"
        "Recent claims (most-recent-first):\n"
        f"{numbered}\n\n"
        'Output JSON: {"topics": [{"id": "kebab-case-slug", "title": "...", '
        '"rationale": "1-line why this is timely given the claims"}, ...]}'
    )


def _truncate(s: str, n: int = 240) -> str:
    s = s.strip()
    return s if len(s) <= n else (s[: n - 1] + "…")


def _reset_cache() -> None:
    """Test helper: drop the module-level cache."""
    global _CACHE, _CACHE_AT
    _CACHE = None
    _CACHE_AT = None


@router.get("/suggested-topics", response_model=SuggestedTopicsResponse)
async def suggested_topics(
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    recent: Annotated[int, Query(ge=1, le=200)] = 30,
    force: Annotated[bool, Query()] = False,
) -> SuggestedTopicsResponse:
    global _CACHE, _CACHE_AT

    if not force and _CACHE is not None and _is_fresh(_CACHE_AT):
        cached = SuggestedTopicsResponse.model_validate(_CACHE)
        cached.topics = cached.topics[:limit]
        return cached

    async with session_scope() as session:
        stmt = (
            select(ClaimModel)
            .order_by(ClaimModel.created_at.desc())
            .limit(recent)
        )
        rows = (await session.execute(stmt)).scalars().all()

    if not rows:
        empty = SuggestedTopicsResponse(
            topics=[],
            generated_at=_now(),
            claim_basis_count=0,
        )
        # Don't cache the empty state — we want to pick up new claims promptly.
        return empty

    claim_lines: list[str] = []
    for row in rows:
        statement = (row.statement or "").strip()
        if not statement:
            continue
        snippet = _first_evidence_snippet(row.supporting_evidence)
        line = statement if not snippet else f"{statement} — evidence: {snippet}"
        claim_lines.append(_truncate(line, 320))

    prompt = _build_prompt(claim_lines)
    model = get_settings().default_research_model

    try:
        provider = get_provider("openai")
        result = await provider.structured_extract(
            prompt=prompt, schema=_TopicSlate, model=model
        )
        slate = result if isinstance(result, _TopicSlate) else _TopicSlate.model_validate(result)
        topics = [
            SuggestedTopic(id=t.id, title=t.title, rationale=t.rationale or "")
            for t in slate.topics
        ][:limit]
    except Exception as exc:
        logger.warning("suggested_topics.llm_failed", error=str(exc))
        return SuggestedTopicsResponse(
            topics=[],
            generated_at=_now(),
            claim_basis_count=len(claim_lines),
            error=_truncate(str(exc), 200),
        )

    response = SuggestedTopicsResponse(
        topics=topics,
        generated_at=_now(),
        claim_basis_count=len(claim_lines),
    )
    _CACHE = response.model_dump(mode="json")
    _CACHE_AT = _now()
    return response
