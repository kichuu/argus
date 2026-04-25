from __future__ import annotations

import sys
import types
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


def _install_fake_qdrant_modules(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    """Install lightweight fake qdrant_client modules so the activity's lazy
    imports succeed without the real package needing to be installed.
    """
    fake_client_instance = MagicMock()
    fake_client_instance.upsert = AsyncMock()
    fake_client_instance.close = AsyncMock()

    fake_async_qdrant_cls = MagicMock(return_value=fake_client_instance)

    fake_models = types.SimpleNamespace(
        PointStruct=lambda id, vector, payload: types.SimpleNamespace(
            id=id, vector=vector, payload=payload
        ),
    )

    qdrant_pkg = types.ModuleType("qdrant_client")
    qdrant_pkg.AsyncQdrantClient = fake_async_qdrant_cls  # type: ignore[attr-defined]

    qdrant_http = types.ModuleType("qdrant_client.http")
    qdrant_http_models = types.ModuleType("qdrant_client.http.models")
    qdrant_http_models.PointStruct = fake_models.PointStruct  # type: ignore[attr-defined]
    qdrant_http.models = qdrant_http_models  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "qdrant_client", qdrant_pkg)
    monkeypatch.setitem(sys.modules, "qdrant_client.http", qdrant_http)
    monkeypatch.setitem(sys.modules, "qdrant_client.http.models", qdrant_http_models)
    return fake_async_qdrant_cls, fake_client_instance


def _install_fake_embedder(monkeypatch: pytest.MonkeyPatch, vec: list[float]) -> MagicMock:
    """Override Embedder so we never load sentence-transformers in tests."""
    fake_embedder = MagicMock()
    fake_embedder.embed_one = AsyncMock(return_value=vec)

    fake_module = types.ModuleType("argus_retrieval.embeddings")
    fake_module.Embedder = MagicMock(return_value=fake_embedder)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "argus_retrieval.embeddings", fake_module)
    return fake_embedder


@pytest.mark.asyncio
async def test_index_evidence_upserts_with_expected_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argus_workers.activities import fetch as fetch_mod

    source_uuid = uuid4()
    claim_uuid = uuid4()
    entity_uuid = uuid4()
    fetched_at = datetime.now(UTC)

    src_row = MagicMock()
    src_row.id = source_uuid
    src_row.fetched_at = fetched_at
    src_row.trust_tier = 2

    claim_row = MagicMock()
    claim_row.id = claim_uuid
    claim_row.affected_entities = [str(entity_uuid)]
    claim_row.supporting_evidence = [
        {
            "source_id": str(source_uuid),
            "verbatim_span": "hello world",
            "char_start": 0,
            "char_end": 11,
            "trust_tier": 3,
        }
    ]

    async def fake_load(source_id: str):
        assert source_id == str(source_uuid)
        return src_row, [(claim_row, claim_row.supporting_evidence[0])]

    monkeypatch.setattr(fetch_mod, "_load_source_and_claims", fake_load)

    fake_async_qdrant_cls, fake_client = _install_fake_qdrant_modules(monkeypatch)
    fake_embedder = _install_fake_embedder(monkeypatch, [0.1, 0.2, 0.3])

    result = await fetch_mod.index_evidence(str(source_uuid))

    assert result["indexed"] == 1
    assert result["skipped"] is False
    assert result["source_id"] == str(source_uuid)

    fake_embedder.embed_one.assert_awaited_once_with("hello world")
    fake_client.upsert.assert_awaited_once()
    kwargs = fake_client.upsert.await_args.kwargs
    points = kwargs["points"]
    assert len(points) == 1
    payload = points[0].payload
    assert payload["source_id"] == str(source_uuid)
    assert payload["claim_id"] == str(claim_uuid)
    assert payload["span"] == "hello world"
    assert payload["char_start"] == 0
    assert payload["char_end"] == 11
    assert payload["trust_tier"] == 3
    assert payload["entity_ids"] == [str(entity_uuid)]
    assert payload["fetched_at"] == fetched_at.isoformat()
    assert points[0].vector == {"dense": [0.1, 0.2, 0.3]}


@pytest.mark.asyncio
async def test_index_evidence_returns_qdrant_unavailable_on_upsert_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argus_workers.activities import fetch as fetch_mod

    source_uuid = uuid4()
    claim_row = MagicMock()
    claim_row.id = uuid4()
    claim_row.affected_entities = []
    claim_row.supporting_evidence = [
        {
            "source_id": str(source_uuid),
            "verbatim_span": "x" * 5,
            "char_start": 0,
            "char_end": 5,
            "trust_tier": 2,
        }
    ]
    src_row = MagicMock()
    src_row.id = source_uuid
    src_row.fetched_at = datetime.now(UTC)
    src_row.trust_tier = 2

    async def fake_load(_: str):
        return src_row, [(claim_row, claim_row.supporting_evidence[0])]

    monkeypatch.setattr(fetch_mod, "_load_source_and_claims", fake_load)

    _cls, fake_client = _install_fake_qdrant_modules(monkeypatch)
    fake_client.upsert = AsyncMock(side_effect=ConnectionError("qdrant down"))
    _install_fake_embedder(monkeypatch, [0.0, 0.0])

    result = await fetch_mod.index_evidence(str(source_uuid))

    assert result == {
        "source_id": str(source_uuid),
        "indexed": 0,
        "skipped": True,
        "reason": "qdrant_unavailable",
    }


@pytest.mark.asyncio
async def test_index_evidence_handles_missing_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argus_workers.activities import fetch as fetch_mod

    async def fake_load(_: str):
        return None, []

    monkeypatch.setattr(fetch_mod, "_load_source_and_claims", fake_load)

    sid = str(uuid4())
    result = await fetch_mod.index_evidence(sid)
    assert result == {
        "source_id": sid,
        "indexed": 0,
        "skipped": True,
        "reason": "source_missing",
    }


@pytest.mark.asyncio
async def test_index_evidence_no_evidence_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argus_workers.activities import fetch as fetch_mod

    sid = str(uuid4())
    src_row = MagicMock()
    src_row.id = uuid4()
    src_row.fetched_at = datetime.now(UTC)
    src_row.trust_tier = 4

    async def fake_load(_: str):
        return src_row, []

    monkeypatch.setattr(fetch_mod, "_load_source_and_claims", fake_load)

    result = await fetch_mod.index_evidence(sid)
    assert result == {"source_id": sid, "indexed": 0, "skipped": False}
