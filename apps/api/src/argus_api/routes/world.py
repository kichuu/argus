from collections import Counter
from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID

from argus_core.db.models import ClaimModel, EntityModel, SourceModel
from argus_core.logging import get_logger
from argus_core.publisher_geo import load_publisher_geo
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from argus_api.deps import get_session

logger = get_logger(__name__)

router = APIRouter(prefix="/world", tags=["world"])


class PlacePin(BaseModel):
    entity_id: UUID
    name: str
    lat: float
    lon: float
    wikidata_id: str | None
    claim_count: int


@router.get("/places", response_model=list[PlacePin])
async def list_places(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(200, ge=1, le=2000),
    min_claim_count: int = Query(0, ge=0),
) -> list[PlacePin]:
    """Places with non-null coords + count of claims that mention them."""
    # Correlated scalar subquery: count claims whose affected_entities array
    # contains the entity id (cast to text since affected_entities is text[]).
    entity_id_text = cast(EntityModel.id, String)
    claim_count_sq = (
        select(func.count(ClaimModel.id))
        .where(entity_id_text == func.any(ClaimModel.affected_entities))
        .correlate(EntityModel)
        .scalar_subquery()
    )

    stmt = (
        select(
            EntityModel.id,
            EntityModel.canonical_name,
            EntityModel.latitude,
            EntityModel.longitude,
            EntityModel.wikidata_id,
            claim_count_sq.label("claim_count"),
        )
        .where(
            EntityModel.entity_type == "place",
            EntityModel.latitude.is_not(None),
            EntityModel.longitude.is_not(None),
        )
        .order_by(claim_count_sq.desc(), EntityModel.canonical_name.asc())
        .limit(limit)
    )

    rows = (await session.execute(stmt)).all()
    pins: list[PlacePin] = []
    for row in rows:
        count = int(row.claim_count or 0)
        if count < min_claim_count:
            continue
        pins.append(
            PlacePin(
                entity_id=row.id,
                name=row.canonical_name,
                lat=row.latitude,
                lon=row.longitude,
                wikidata_id=row.wikidata_id,
                claim_count=count,
            )
        )
    return pins


class SourcePin(BaseModel):
    location_key: str  # "city, country" — used as the pin's stable id
    city: str
    country: str
    lat: float
    lon: float
    source_count: int
    publisher_count: int
    publishers: list[str]
    sample_titles: list[str]
    sample_source_ids: list[UUID]
    latest_fetched_at: datetime | None


@router.get("/sources", response_model=list[SourcePin])
async def list_source_pins(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(500, ge=1, le=2000),
) -> list[SourcePin]:
    """Pins for ingested Sources, grouped by publisher HQ location.

    Looks up each Source's publisher domain in config/publisher_locations.yaml
    and aggregates by (city, country). One pin per location, sized by source
    count, with a list of publishers + sample titles for the side panel.

    No DB schema change required — all done in-memory at request time.
    Sources whose publisher isn't in the config are silently skipped (their
    domain is logged once per request so you can extend the config).
    """
    geo = load_publisher_geo()
    stmt = (
        select(
            SourceModel.id,
            SourceModel.url,
            SourceModel.title,
            SourceModel.publisher,
            SourceModel.fetched_at,
        )
        .order_by(SourceModel.fetched_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()

    # Aggregate by location. Key = "city, country" string is unique enough
    # for our config; more granular would need composite key.
    grouped: dict[str, dict] = {}
    unmatched: Counter[str] = Counter()
    for row in rows:
        host = ""
        if row.url:
            host = urlparse(str(row.url)).hostname or ""
        if not host and row.publisher:
            host = row.publisher
        loc = geo.lookup(host)
        if loc is None:
            if host:
                unmatched[host] += 1
            continue
        key = f"{loc.city}, {loc.country}"
        bucket = grouped.setdefault(
            key,
            {
                "city": loc.city,
                "country": loc.country,
                "lat": loc.lat,
                "lon": loc.lon,
                "source_ids": [],
                "publishers": set(),
                "titles": [],
                "latest": None,
            },
        )
        bucket["source_ids"].append(row.id)
        if row.publisher:
            bucket["publishers"].add(row.publisher)
        else:
            bucket["publishers"].add(host)
        if len(bucket["titles"]) < 5:
            bucket["titles"].append(row.title or "(untitled)")
        if bucket["latest"] is None or (row.fetched_at and row.fetched_at > bucket["latest"]):
            bucket["latest"] = row.fetched_at

    if unmatched:
        logger.info("world_sources_unmatched_publishers", unmatched=dict(unmatched.most_common(10)))

    pins = [
        SourcePin(
            location_key=key,
            city=b["city"],
            country=b["country"],
            lat=b["lat"],
            lon=b["lon"],
            source_count=len(b["source_ids"]),
            publisher_count=len(b["publishers"]),
            publishers=sorted(b["publishers"])[:10],
            sample_titles=b["titles"],
            sample_source_ids=b["source_ids"][:5],
            latest_fetched_at=b["latest"],
        )
        for key, b in grouped.items()
    ]
    pins.sort(key=lambda p: p.source_count, reverse=True)
    return pins
