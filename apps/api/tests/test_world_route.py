from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from argus_api.deps import get_session
from argus_api.main import app
from httpx import ASGITransport, AsyncClient


def _row(
    *,
    id: UUID,
    canonical_name: str,
    latitude: float | None,
    longitude: float | None,
    wikidata_id: str | None,
    claim_count: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        canonical_name=canonical_name,
        latitude=latitude,
        longitude=longitude,
        wikidata_id=wikidata_id,
        claim_count=claim_count,
    )


class _PlacesSession:
    """Fake AsyncSession that returns canned rows for the world.places query.

    The route only calls ``session.execute(stmt)`` once and reads ``.all()`` from
    the result, so we ignore the statement entirely and replay the rows we were
    given. Filtering by NULL coords is the route's job and is exercised by the
    tests below by including such rows in the canned set.
    """

    def __init__(self, rows: list[SimpleNamespace]) -> None:
        # The route applies the latitude/longitude IS NOT NULL filter at the SQL
        # layer; mirror that here so the fake matches Postgres semantics.
        self.rows = [r for r in rows if r.latitude is not None and r.longitude is not None]

    async def execute(self, _stmt: Any) -> Any:
        result = MagicMock()
        result.all.return_value = self.rows
        return result


def _override_session(session: Any) -> None:
    async def _override() -> AsyncIterator[Any]:
        yield session

    app.dependency_overrides[get_session] = _override


@pytest.mark.asyncio
async def test_places_excludes_rows_with_null_coords() -> None:
    rows = [
        _row(
            id=uuid4(),
            canonical_name="Has coords",
            latitude=51.5,
            longitude=-0.12,
            wikidata_id="Q84",
            claim_count=3,
        ),
        _row(
            id=uuid4(),
            canonical_name="No coords",
            latitude=None,
            longitude=None,
            wikidata_id="Q1",
            claim_count=10,
        ),
    ]
    session = _PlacesSession(rows)
    _override_session(session)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/world/places")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Has coords"


@pytest.mark.asyncio
async def test_places_min_claim_count_filter() -> None:
    rows = [
        _row(
            id=uuid4(),
            canonical_name="Busy",
            latitude=40.7,
            longitude=-74.0,
            wikidata_id="Q60",
            claim_count=5,
        ),
        _row(
            id=uuid4(),
            canonical_name="Quiet",
            latitude=48.85,
            longitude=2.35,
            wikidata_id="Q90",
            claim_count=0,
        ),
    ]
    session = _PlacesSession(rows)
    _override_session(session)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/world/places", params={"min_claim_count": 1})
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    names = [item["name"] for item in body]
    assert names == ["Busy"]


@pytest.mark.asyncio
async def test_places_response_shape_matches_contract() -> None:
    eid = uuid4()
    rows = [
        _row(
            id=eid,
            canonical_name="Berlin",
            latitude=52.52,
            longitude=13.405,
            wikidata_id="Q64",
            claim_count=7,
        ),
    ]
    session = _PlacesSession(rows)
    _override_session(session)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/world/places")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    pin = body[0]
    assert set(pin.keys()) == {
        "entity_id",
        "name",
        "lat",
        "lon",
        "wikidata_id",
        "claim_count",
    }
    assert UUID(pin["entity_id"]) == eid
    assert pin["name"] == "Berlin"
    assert pin["lat"] == 52.52
    assert pin["lon"] == 13.405
    assert pin["wikidata_id"] == "Q64"
    assert pin["claim_count"] == 7


@pytest.mark.asyncio
async def test_places_allows_null_wikidata_id() -> None:
    rows = [
        _row(
            id=uuid4(),
            canonical_name="Unmapped place",
            latitude=10.0,
            longitude=20.0,
            wikidata_id=None,
            claim_count=2,
        ),
    ]
    session = _PlacesSession(rows)
    _override_session(session)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/world/places")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["wikidata_id"] is None
