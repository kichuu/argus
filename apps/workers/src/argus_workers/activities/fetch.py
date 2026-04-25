from typing import Any

from temporalio import activity

from argus_core.logging import get_logger

logger = get_logger(__name__)


@activity.defn
async def fetch_source(config: dict[str, Any]) -> list[str]:
    # TODO(ingestion): wire RSSConnector / GDELTConnector / WikidataConnector
    # from argus_ingestion based on config["kind"], persist via SourceModel,
    # and return persisted source UUIDs as strings. RawStore + SimHashDedup
    # should run before persistence.
    kind = config.get("kind", "unknown")
    logger.info("fetch_source.stub", kind=kind, config=config)
    return []


@activity.defn
async def index_evidence(source_id: str) -> dict[str, Any]:
    # TODO(retrieval): wire argus_retrieval embeddings + Qdrant upsert here.
    logger.info("index_evidence.stub", source_id=source_id)
    return {"source_id": source_id, "indexed": 0}
