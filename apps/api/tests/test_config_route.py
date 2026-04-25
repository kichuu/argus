"""Tests for /config.

Verifies the response shape and explicitly guards against any secret-bearing
field (API keys, DB URL, S3 creds) leaking into the public payload.
"""

import pytest
from argus_api.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_config_shape() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/config")

    assert resp.status_code == 200
    body = resp.json()

    # Top-level fields
    assert set(body.keys()) == {
        "vertical",
        "models",
        "ingest",
        "qdrant",
        "embedding_model",
        "reranker_model",
    }
    assert isinstance(body["vertical"], str)
    assert isinstance(body["embedding_model"], str)
    assert isinstance(body["reranker_model"], str)

    # Models block: all 7 roles present
    assert set(body["models"].keys()) == {
        "synthesis",
        "extractor",
        "verifier",
        "research",
        "persona",
        "master",
        "critic",
    }
    for role, value in body["models"].items():
        assert isinstance(value, str), f"model {role} must be a string"

    # Ingest block
    assert set(body["ingest"].keys()) == {
        "enabled",
        "interval_seconds",
        "max_items_per_feed",
        "feeds_path",
    }
    assert isinstance(body["ingest"]["enabled"], bool)
    assert isinstance(body["ingest"]["interval_seconds"], int)
    assert isinstance(body["ingest"]["max_items_per_feed"], int)
    assert isinstance(body["ingest"]["feeds_path"], str)

    # Qdrant block
    assert set(body["qdrant"].keys()) == {"collection"}
    assert isinstance(body["qdrant"]["collection"], str)


@pytest.mark.asyncio
async def test_config_does_not_leak_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force concrete (and recognisable) values into Settings via env so we can
    # search the response for them. If any of these strings ever appears in the
    # body it means a secret has leaked through the whitelist.
    sentinel_openai = "sk-SENTINEL-OPENAI-DO-NOT-LEAK"
    sentinel_qdrant = "qdr-SENTINEL-DO-NOT-LEAK"
    sentinel_s3_secret = "s3secret-SENTINEL-DO-NOT-LEAK"
    sentinel_s3_access = "s3access-SENTINEL-DO-NOT-LEAK"
    sentinel_hf = "hf_SENTINEL-DO-NOT-LEAK"
    sentinel_cohere = "cohere-SENTINEL-DO-NOT-LEAK"
    sentinel_db = "postgresql+asyncpg://leakuser:leakpass@leakhost/leakdb"

    monkeypatch.setenv("OPENAI_API_KEY", sentinel_openai)
    monkeypatch.setenv("QDRANT_API_KEY", sentinel_qdrant)
    monkeypatch.setenv("S3_SECRET_KEY", sentinel_s3_secret)
    monkeypatch.setenv("S3_ACCESS_KEY", sentinel_s3_access)
    monkeypatch.setenv("HUGGINGFACE_TOKEN", sentinel_hf)
    monkeypatch.setenv("COHERE_API_KEY", sentinel_cohere)
    monkeypatch.setenv("DATABASE_URL", sentinel_db)

    # get_settings() is lru_cached — bust it so the env we just set is honoured.
    from argus_core.settings import get_settings

    get_settings.cache_clear()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/config")
        assert resp.status_code == 200
        body = resp.json()

        # Forbidden field names (case-insensitive substring match against the
        # serialized body).
        serialized = str(body).lower()
        for forbidden_key in [
            "openai_api_key",
            "qdrant_api_key",
            "database_url",
            "alembic_database_url",
            "s3_secret_key",
            "s3_access_key",
            "huggingface_token",
            "cohere_api_key",
            "newsapi_key",
            "redis_url",
        ]:
            assert forbidden_key not in body, f"forbidden key {forbidden_key} present at top level"
            assert forbidden_key not in serialized, (
                f"forbidden key name {forbidden_key} appears in serialized body"
            )

        # Forbidden secret values — these must never appear anywhere in the body.
        for sentinel in [
            sentinel_openai,
            sentinel_qdrant,
            sentinel_s3_secret,
            sentinel_s3_access,
            sentinel_hf,
            sentinel_cohere,
            sentinel_db,
        ]:
            assert sentinel not in str(body), f"secret value {sentinel!r} leaked into response"
    finally:
        get_settings.cache_clear()
