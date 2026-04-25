"""Initialize the Qdrant evidence collection used by Argus retrieval.

Idempotent: re-runs are no-ops once the collection exists. The vector size is
detected from the configured embedding model (so this script keeps working if
``settings.embedding_model`` changes).

Payload schema for points::

    {
        "source_id": str (UUID),
        "claim_id": str (UUID) | None,
        "span": str,                # verbatim_span
        "char_start": int,
        "char_end": int,
        "fetched_at": str (ISO8601),
        "trust_tier": int,
        "entity_ids": list[str],
    }

Payload indexes are created on ``source_id``, ``entity_ids``, and ``trust_tier``
so filter-by-source / filter-by-entity / filter-by-tier queries are cheap.
"""

from __future__ import annotations

import asyncio
import sys

from argus_core.logging import get_logger
from argus_core.settings import get_settings

logger = get_logger(__name__)

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


def _require_qdrant():
    try:
        from qdrant_client import AsyncQdrantClient  # type: ignore
        from qdrant_client.http import models as qm  # type: ignore
    except ImportError:
        print(
            "qdrant-client is required. Install with:\n"
            "  uv add --group dev 'qdrant-client>=1.12'",
            file=sys.stderr,
        )
        sys.exit(1)
    return AsyncQdrantClient, qm


async def _detect_embedding_dim() -> int:
    """Detect dense-vector size by running one embed of 'x'.

    Falls back to 1024 (the bge-large-en-v1.5 size) if the embedder cannot be
    instantiated -- e.g. running this script on a host without
    sentence-transformers installed yet.
    """
    try:
        from argus_retrieval.embeddings import Embedder

        embedder = Embedder()
        vec = await embedder.embed_one("x")
        return len(vec)
    except Exception as exc:  # noqa: BLE001
        print(f"  warning: dim detection failed ({exc!r}); falling back to 1024.")
        return 1024


async def _ensure_payload_indexes(client, collection: str, qm) -> None:
    """Create payload indexes for fast filtering. Idempotent."""
    index_specs = [
        ("source_id", qm.PayloadSchemaType.KEYWORD),
        ("entity_ids", qm.PayloadSchemaType.KEYWORD),
        ("trust_tier", qm.PayloadSchemaType.INTEGER),
    ]
    for field_name, field_schema in index_specs:
        try:
            await client.create_payload_index(
                collection_name=collection,
                field_name=field_name,
                field_schema=field_schema,
            )
            print(f"  created payload index: {field_name}")
        except Exception as exc:  # noqa: BLE001
            # Qdrant returns 409/conflict if the index already exists.
            msg = str(exc).lower()
            if "already exists" in msg or "conflict" in msg or "exists" in msg:
                print(f"  payload index '{field_name}' already exists; skipping.")
            else:
                print(f"  payload index '{field_name}' create failed: {exc}")


async def _amain() -> int:
    AsyncQdrantClient, qm = _require_qdrant()
    settings = get_settings()
    collection = settings.qdrant_collection_evidence

    print(f"Connecting to Qdrant at {settings.qdrant_url}...")
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
    )

    try:
        exists = await client.collection_exists(collection)
        if exists:
            print(f"Collection '{collection}' already exists; ensuring payload indexes.")
            await _ensure_payload_indexes(client, collection, qm)
            print("init_qdrant complete (no-op).")
            return 0

        dense_dim = await _detect_embedding_dim()
        print(
            f"Creating collection '{collection}' "
            f"(dense_dim={dense_dim}, distance=COSINE)..."
        )

        try:
            await client.create_collection(
                collection_name=collection,
                vectors_config={
                    DENSE_VECTOR_NAME: qm.VectorParams(
                        size=dense_dim, distance=qm.Distance.COSINE
                    ),
                },
                sparse_vectors_config={
                    SPARSE_VECTOR_NAME: qm.SparseVectorParams(
                        index=qm.SparseIndexParams(on_disk=False)
                    ),
                },
            )
            print("  created with sparse vectors enabled.")
        except Exception as exc:  # noqa: BLE001
            print(f"  sparse-vector create failed ({exc}); falling back to dense-only.")
            await client.create_collection(
                collection_name=collection,
                vectors_config={
                    DENSE_VECTOR_NAME: qm.VectorParams(
                        size=dense_dim, distance=qm.Distance.COSINE
                    ),
                },
            )

        await _ensure_payload_indexes(client, collection, qm)
        print("init_qdrant complete.")
        return 0
    finally:
        try:
            await client.close()
        except Exception:  # noqa: BLE001
            pass


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
