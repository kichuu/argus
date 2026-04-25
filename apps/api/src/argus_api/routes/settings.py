from typing import Annotated

from argus_core.personas import load_persona_library
from argus_core.settings import Settings
from argus_core.trust import load_trust_config
from argus_extraction.providers import family_of
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from argus_api.deps import get_settings_dep

router = APIRouter(tags=["settings"])


class ModelConfig(BaseModel):
    role: str
    model: str
    family: str


class SettingsResponse(BaseModel):
    app_env: str
    log_level: str
    vertical: str
    embedding_provider: str
    embedding_model: str
    openai_embedding_model: str
    openai_embedding_dimensions: int
    reranker_model: str
    models: list[ModelConfig]
    trust_tier_count: int
    persona_library_count: dict[str, int]
    qdrant_collection: str
    temporal: dict[str, str]
    raw_store_backend: str


_ROLE_FIELDS: tuple[tuple[str, str], ...] = (
    ("synthesis", "default_synthesis_model"),
    ("extractor", "default_extractor_model"),
    ("verifier", "default_verifier_model"),
    ("research", "default_research_model"),
    ("persona", "default_persona_model"),
    ("master", "default_master_model"),
    ("critic", "default_critic_model"),
)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings_endpoint(
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> SettingsResponse:
    """Read-only view of safe (non-secret) configuration."""
    models = [
        ModelConfig(
            role=role,
            model=getattr(settings, field),
            family=family_of(getattr(settings, field)),
        )
        for role, field in _ROLE_FIELDS
    ]

    trust_config = load_trust_config()
    trust_tier_count = len(trust_config.tiers) + len(trust_config.domain_overrides)

    library = load_persona_library()
    persona_library_count = {
        vertical: len(templates) for vertical, templates in library.verticals.items()
    }

    return SettingsResponse(
        app_env=settings.app_env,
        log_level=settings.log_level,
        vertical=settings.vertical,
        embedding_provider=settings.embedding_provider,
        embedding_model=settings.embedding_model,
        openai_embedding_model=settings.openai_embedding_model,
        openai_embedding_dimensions=settings.openai_embedding_dimensions,
        reranker_model=settings.reranker_model,
        models=models,
        trust_tier_count=trust_tier_count,
        persona_library_count=persona_library_count,
        qdrant_collection=settings.qdrant_collection_evidence,
        temporal={
            "host": settings.temporal_host,
            "namespace": settings.temporal_namespace,
            "task_queue": settings.temporal_task_queue,
        },
        raw_store_backend=settings.raw_store_backend,
    )
