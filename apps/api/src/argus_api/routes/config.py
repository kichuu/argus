"""Non-secret server config exposed to the web UI.

This route is intentionally a tight whitelist: only fields that are safe to
display to a logged-in operator. Secrets (API keys, database URLs, S3 creds,
etc.) MUST NOT be added here. There is a regression test asserting this.
"""

from argus_core.settings import get_settings
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["config"])


class ModelsOut(BaseModel):
    synthesis: str
    extractor: str
    verifier: str
    research: str
    persona: str
    master: str
    critic: str


class IngestOut(BaseModel):
    enabled: bool
    interval_seconds: int
    max_items_per_feed: int
    feeds_path: str


class QdrantOut(BaseModel):
    collection: str


class ConfigOut(BaseModel):
    vertical: str
    models: ModelsOut
    ingest: IngestOut
    qdrant: QdrantOut
    embedding_model: str
    reranker_model: str


@router.get("/config", response_model=ConfigOut)
async def get_config() -> ConfigOut:
    s = get_settings()
    return ConfigOut(
        vertical=s.vertical,
        models=ModelsOut(
            synthesis=s.default_synthesis_model,
            extractor=s.default_extractor_model,
            verifier=s.default_verifier_model,
            research=s.default_research_model,
            persona=s.default_persona_model,
            master=s.default_master_model,
            critic=s.default_critic_model,
        ),
        ingest=IngestOut(
            enabled=s.ingest_enabled,
            interval_seconds=s.ingest_interval_seconds,
            max_items_per_feed=s.ingest_max_items_per_feed,
            feeds_path=str(s.ingest_feeds_path),
        ),
        qdrant=QdrantOut(collection=s.qdrant_collection_evidence),
        embedding_model=s.embedding_model,
        reranker_model=s.reranker_model,
    )
