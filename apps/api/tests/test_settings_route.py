from pathlib import Path
from typing import Any

import pytest
from argus_api.main import app
from argus_core.settings import get_settings
from httpx import ASGITransport, AsyncClient

_SECRET_SUBSTRINGS = (
    "api_key",
    "password",
    "token",
    "secret",
)


@pytest.mark.asyncio
async def test_settings_ok() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/settings")
    assert resp.status_code == 200
    body = resp.json()

    assert isinstance(body["app_env"], str)
    assert isinstance(body["log_level"], str)
    assert isinstance(body["vertical"], str)
    assert isinstance(body["embedding_provider"], str)
    assert isinstance(body["embedding_model"], str)
    assert isinstance(body["openai_embedding_model"], str)
    assert isinstance(body["openai_embedding_dimensions"], int)
    assert isinstance(body["reranker_model"], str)
    assert isinstance(body["qdrant_collection"], str)
    assert isinstance(body["raw_store_backend"], str)
    assert set(body["temporal"].keys()) == {"host", "namespace", "task_queue"}
    assert isinstance(body["persona_library_count"], dict)


@pytest.mark.asyncio
async def test_settings_no_secret_fields() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/settings")
    assert resp.status_code == 200
    body = resp.json()

    forbidden_keys = {
        "openai_api_key",
        "qdrant_api_key",
        "huggingface_token",
        "cohere_api_key",
        "s3_access_key",
        "s3_secret_key",
        "newsapi_key",
        "gnews_key",
        "alpha_vantage_key",
        "climate_trace_key",
        "noaa_api_key",
        "congress_gov_api_key",
        "propublica_api_key",
        "database_url",
        "redis_url",
    }
    assert forbidden_keys.isdisjoint(body.keys())

    keys: list[Any] = []

    def _collect_keys(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.append(k)
                _collect_keys(v)
        elif isinstance(obj, list):
            for v in obj:
                _collect_keys(v)

    _collect_keys(body)
    for k in keys:
        assert isinstance(k, str)
        lowered = k.lower()
        for needle in _SECRET_SUBSTRINGS:
            assert needle not in lowered, f"secret-shaped key in response: {k!r}"


@pytest.mark.asyncio
async def test_settings_models_seven_roles() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/settings")
    assert resp.status_code == 200
    body = resp.json()

    models = body["models"]
    assert isinstance(models, list)
    assert len(models) == 7
    roles = {m["role"] for m in models}
    assert roles == {
        "synthesis",
        "extractor",
        "verifier",
        "research",
        "persona",
        "master",
        "critic",
    }
    for m in models:
        assert isinstance(m["model"], str) and m["model"]
        assert m["family"] in {"gpt", "reasoning", "unknown"}


@pytest.mark.asyncio
async def test_settings_trust_tier_count_when_config_present() -> None:
    settings = get_settings()
    if not Path(settings.trust_tiers_path).exists():
        pytest.skip("trust_tiers.yaml not present")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["trust_tier_count"] > 0
