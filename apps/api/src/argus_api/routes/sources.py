from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from argus_core.db.models import SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.trust import load_trust_config
from argus_ingestion.base import compute_content_hash, normalize_text
from argus_ingestion.store import RawStore
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, select

logger = get_logger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])

SourceStatus = Literal["ok", "warn", "down"]
SourceType = Literal["rss", "api", "manual"]

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Argus/0.1"
)
_FETCH_TIMEOUT_SECONDS = 15.0
_HTML_DROP_TAGS = ("script", "style", "noscript", "nav", "footer", "header", "aside")


def _derive_type(row: SourceModel) -> SourceType:
    if row.feed_url:
        return "rss"
    if row.url:
        return "api"
    return "manual"


def _derive_status(row: SourceModel) -> SourceStatus:
    # No real status tracking yet — stub to "ok" per spec.
    return "ok"


def _derive_name(row: SourceModel) -> str | None:
    return row.title or row.publisher


class SourceOut(BaseModel):
    id: UUID
    name: str | None = None
    type: SourceType | None = None
    status: SourceStatus | None = None


class SourceDetail(BaseModel):
    id: UUID
    name: str | None = None
    type: SourceType | None = None
    status: SourceStatus | None = None
    url: str | None = None
    feed_url: str | None = None
    title: str
    content_hash: str
    raw_text_length: int
    fetched_at: datetime
    published_at: datetime | None = None
    license: str | None = None
    trust_tier: int
    publisher: str | None = None
    language: str | None = None


class PublisherCount(BaseModel):
    name: str
    count: int


class SourceStats(BaseModel):
    total: int
    last_24h: int
    events_per_hour_24h: float
    by_trust_tier: dict[str, int]
    by_publisher_top10: list[PublisherCount]
    duplicates_blocked_24h_est: int | None = None
    spark_24h: list[int]


class SourceIngestRequest(BaseModel):
    url: HttpUrl


class SourceIngestResponse(BaseModel):
    id: UUID
    title: str
    content_hash: str
    chars: int
    status: Literal["ingested", "duplicate"]
    trust_tier: int | None = Field(default=None)


def _to_summary(row: SourceModel) -> SourceOut:
    return SourceOut(
        id=row.id,
        name=_derive_name(row),
        type=_derive_type(row),
        status=_derive_status(row),
    )


def _to_detail(row: SourceModel) -> SourceDetail:
    return SourceDetail(
        id=row.id,
        name=_derive_name(row),
        type=_derive_type(row),
        status=_derive_status(row),
        url=row.url,
        feed_url=row.feed_url,
        title=row.title,
        content_hash=row.content_hash,
        raw_text_length=len(row.raw_text or ""),
        fetched_at=row.fetched_at,
        published_at=row.published_at,
        license=row.license,
        trust_tier=row.trust_tier,
        publisher=row.publisher,
        language=row.language,
    )


def _extract_html(body: str, fallback_title: str) -> tuple[str, str]:
    """Return (title, normalized_text) by stripping nav/footer/script."""
    soup = BeautifulSoup(body, "lxml")
    title_tag = soup.find("title")
    title = (title_tag.get_text(strip=True) if title_tag else "") or fallback_title

    for tag_name in _HTML_DROP_TAGS:
        for el in soup.find_all(tag_name):
            el.decompose()

    cleaned_html = str(soup)
    text = normalize_text(cleaned_html)
    return title, text


def _content_type_kind(content_type: str | None) -> Literal["html", "text", "json", "other"]:
    if not content_type:
        return "other"
    ct = content_type.split(";", 1)[0].strip().lower()
    if "html" in ct:
        return "html"
    if "json" in ct:
        return "json"
    if ct.startswith("text/"):
        return "text"
    return "other"


@router.get("", response_model=list[SourceOut])
async def list_sources(
    status_filter: Annotated[SourceStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[SourceOut]:
    async with session_scope() as session:
        stmt = (
            select(SourceModel)
            .order_by(SourceModel.fetched_at.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()

    summaries = [_to_summary(r) for r in rows]
    if status_filter is not None:
        summaries = [s for s in summaries if s.status == status_filter]
    return summaries


@router.get("/stats", response_model=SourceStats)
async def source_stats() -> SourceStats:
    """Aggregate stats over all sources for the right-rail dashboard.

    Counts are derived from the ``sources`` table; duplicates_blocked is not
    tracked yet and returned as ``null``.
    """
    now = datetime.now(UTC)
    cutoff_24h = now - timedelta(hours=24)

    async with session_scope() as session:
        total = int(
            (await session.execute(select(func.count()).select_from(SourceModel))).scalar_one()
            or 0
        )
        last_24h = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(SourceModel)
                    .where(SourceModel.fetched_at >= cutoff_24h)
                )
            ).scalar_one()
            or 0
        )

        # Trust tier distribution (across all sources, not just 24h).
        tier_rows = (
            await session.execute(
                select(SourceModel.trust_tier, func.count())
                .group_by(SourceModel.trust_tier)
            )
        ).all()
        by_trust_tier: dict[str, int] = {
            str(int(tier) if tier is not None else 4): int(cnt) for tier, cnt in tier_rows
        }

        # Top 10 publishers (across all sources). NULL/empty publishers excluded.
        pub_rows = (
            await session.execute(
                select(SourceModel.publisher, func.count())
                .where(SourceModel.publisher.is_not(None))
                .group_by(SourceModel.publisher)
                .order_by(func.count().desc())
                .limit(10)
            )
        ).all()
        by_publisher_top10 = [
            PublisherCount(name=name, count=int(cnt)) for name, cnt in pub_rows if name
        ]

        # Hourly buckets for last 24h. Bucket in Python — portable across DBs.
        recent_rows = (
            await session.execute(
                select(SourceModel.fetched_at).where(SourceModel.fetched_at >= cutoff_24h)
            )
        ).all()
        spark_24h = [0] * 24
        for (ts,) in recent_rows:
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts < cutoff_24h or ts > now:
                continue
            delta = now - ts
            idx = 23 - int(delta.total_seconds() // 3600)
            if 0 <= idx < 24:
                spark_24h[idx] += 1

    return SourceStats(
        total=total,
        last_24h=last_24h,
        events_per_hour_24h=round(last_24h / 24, 2),
        by_trust_tier=by_trust_tier,
        by_publisher_top10=by_publisher_top10,
        duplicates_blocked_24h_est=None,
        spark_24h=spark_24h,
    )


@router.get("/{source_id}", response_model=SourceDetail)
async def get_source(source_id: UUID) -> SourceDetail:
    async with session_scope() as session:
        row = await session.get(SourceModel, source_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="source not found"
            )
        return _to_detail(row)


@router.post("", response_model=SourceIngestResponse)
async def ingest_source(body: SourceIngestRequest) -> SourceIngestResponse:
    """Synchronously fetch a single URL and persist it as a Source row.

    HTML pages are stripped of nav/footer/script before normalization;
    plain-text and JSON bodies are stored verbatim. Duplicate `content_hash`
    rows return the existing id with status="duplicate".
    """
    target_url = str(body.url)

    # 1) Fetch the URL.
    try:
        async with httpx.AsyncClient(
            timeout=_FETCH_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": _DEFAULT_USER_AGENT},
        ) as client:
            response = await client.get(target_url)
    except httpx.HTTPError as exc:
        logger.warning("ingest_source.fetch_failed", url=target_url, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"failed to fetch url: {exc}",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"upstream returned {response.status_code} for {target_url}",
        )

    # 2) Decode body & determine kind.
    content_type = response.headers.get("content-type", "")
    kind = _content_type_kind(content_type)
    body_text = response.text or ""

    fallback_title = target_url
    if kind == "html":
        title, raw_text = _extract_html(body_text, fallback_title)
    elif kind in ("text", "json"):
        title = fallback_title
        raw_text = body_text
    else:
        # Try HTML-ish extraction as a best-effort fallback.
        title, raw_text = _extract_html(body_text, fallback_title)

    raw_text = raw_text.strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fetched body was empty after normalization",
        )

    # 3) Compute hash.
    content_hash = compute_content_hash(raw_text)

    # 4) Trust tier from domain.
    try:
        trust_cfg = load_trust_config()
        host = (urlparse(target_url).hostname or "").lower()
        trust_tier = trust_cfg.tier_for_domain(host) if host else 4
    except Exception as exc:  # noqa: BLE001
        logger.debug("ingest_source.trust_lookup_failed", error=str(exc))
        trust_tier = 4

    # 5) Duplicate check + insert.
    async with session_scope() as session:
        existing = await session.execute(
            select(SourceModel).where(SourceModel.content_hash == content_hash)
        )
        existing_row = existing.scalars().first()
        if existing_row is not None:
            return SourceIngestResponse(
                id=existing_row.id,
                title=existing_row.title,
                content_hash=existing_row.content_hash,
                chars=len(existing_row.raw_text or ""),
                status="duplicate",
                trust_tier=existing_row.trust_tier,
            )

        # 6) Persist raw payload + DB row.
        try:
            await RawStore().put(content_hash, raw_text.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            # Storing the blob is best-effort; we still keep the DB row since
            # raw_text is mirrored on the row itself.
            logger.warning(
                "ingest_source.raw_store_failed",
                content_hash=content_hash,
                error=str(exc),
            )

        new_id = uuid4()
        model = SourceModel(
            id=new_id,
            url=target_url,
            feed_url=None,
            title=title[:1024] if title else target_url[:1024],
            content_hash=content_hash,
            raw_text=raw_text,
            trust_tier=trust_tier,
            publisher=host or None,
            language=None,
        )
        session.add(model)

    return SourceIngestResponse(
        id=new_id,
        title=model.title,
        content_hash=content_hash,
        chars=len(raw_text),
        status="ingested",
        trust_tier=trust_tier,
    )
