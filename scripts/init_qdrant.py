from __future__ import annotations

import sys

from argus_core.settings import get_settings

DENSE_SIZE = 1024


def _require_qdrant():
    try:
        from qdrant_client import QdrantClient  # type: ignore
        from qdrant_client.http import models as qm  # type: ignore
    except ImportError:
        print(
            "qdrant-client is required. Install with:\n"
            "  uv add --group dev 'qdrant-client>=1.12'",
            file=sys.stderr,
        )
        sys.exit(1)
    return QdrantClient, qm


def main() -> int:
    QdrantClient, qm = _require_qdrant()
    settings = get_settings()
    collection = settings.qdrant_collection_evidence

    print(f"Connecting to Qdrant at {settings.qdrant_url}...")
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        timeout=30,
        check_compatibility=False,
    )

    existing = {c.name for c in client.get_collections().collections}
    if collection in existing:
        print(f"Collection '{collection}' already exists; skipping create.")
        return 0

    print(f"Creating collection '{collection}'...")
    client.create_collection(
        collection_name=collection,
        vectors_config={
            "dense": qm.VectorParams(size=DENSE_SIZE, distance=qm.Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": qm.SparseVectorParams(),
        },
    )
    print("init_qdrant complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
