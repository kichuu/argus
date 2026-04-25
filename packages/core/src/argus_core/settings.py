from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "dev"
    log_level: str = "INFO"

    openai_api_key: str = ""

    default_synthesis_model: str = "gpt-5.5"
    default_extractor_model: str = "gpt-5.4"
    default_verifier_model: str = "o4-mini"
    default_research_model: str = "gpt-5.5"
    default_persona_model: str = "gpt-5.4"
    default_master_model: str = "gpt-5.5"
    default_critic_model: str = "gpt-5.5"

    database_url: str = "postgresql+asyncpg://argus:@localhost:5432/argus"
    alembic_database_url: str = "postgresql://argus:@localhost:5432/argus"

    redis_url: str = "redis://localhost:6379/0"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_evidence: str = "argus_evidence"

    raw_store_backend: str = "local"
    raw_store_local_path: Path = Path("./local_data/raw")
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_raw: str = "argus-raw"
    s3_region: str = "us-east-1"

    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "argus-default"

    gdelt_base: str = "https://api.gdeltproject.org/api/v2"
    wikidata_sparql: str = "https://query.wikidata.org/sparql"
    wikidata_user_agent: str = "argus/0.1"

    huggingface_token: str = ""
    cohere_api_key: str = ""

    embedding_provider: str = "openai"  # "openai" | "sentence_transformers"
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1024  # matches Qdrant collection DENSE_SIZE
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    phoenix_collector_endpoint: str = "http://localhost:6006"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "argus"

    gold_set_path: Path = Path("./eval/gold.jsonl")
    trust_tiers_path: Path = Path("./config/trust_tiers.yaml")
    personas_path: Path = Path("./config/personas.yaml")

    newsapi_key: str = ""
    gnews_key: str = ""
    alpha_vantage_key: str = ""
    sec_edgar_user_agent: str = ""
    climate_trace_key: str = ""
    noaa_api_key: str = ""
    congress_gov_api_key: str = ""
    propublica_api_key: str = ""

    vertical: str = Field(default="unset", description="Active vertical: geopolitics|climate|finance|civic|unset")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
