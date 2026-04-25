"""Sync the Apache AGE graph (``argus_graph``) from the Postgres source of truth.

Reads every ``EntityModel`` and ``RelationModel`` row and replays them as
``MERGE`` statements via ``GraphQuerier``. Re-runs are idempotent.

Usage::

    uv run python scripts/sync_age.py

Exit codes:

* 0 -- success
* 1 -- AGE permissions are missing (the ``argus`` Postgres role cannot
  ``LOAD 'age'``). Run ``scripts/grant_age.sql`` as a superuser, then retry.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from argus_core.db.models import EntityModel, RelationModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import Entity
from argus_core.schemas.entity import EntityType
from argus_retrieval.graph import GraphQuerier
from sqlalchemy import select, text

logger = get_logger(__name__)

GRANT_SQL_PATH = Path(__file__).resolve().parent / "grant_age.sql"


async def _can_load_age() -> bool:
    """Return True iff the configured Postgres role can ``LOAD 'age'``.

    AGE requires superuser to LOAD by default. Without it, every Cypher call
    silently no-ops — which is much worse than a hard failure here.
    """
    try:
        async with session_scope() as session:
            await session.execute(text("LOAD 'age'"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("sync_age.load_age_failed", error=str(exc))
        return False


async def _stream_entities() -> list[EntityModel]:
    async with session_scope() as session:
        result = await session.execute(select(EntityModel))
        return list(result.scalars().all())


async def _stream_relations() -> list[RelationModel]:
    async with session_scope() as session:
        result = await session.execute(select(RelationModel))
        return list(result.scalars().all())


def _entity_from_row(row: EntityModel) -> Entity:
    """Coerce a SQLAlchemy row into the Pydantic ``Entity`` so we can reuse
    ``GraphQuerier.upsert_entity`` (which expects a Pydantic schema)."""
    try:
        etype = EntityType(row.entity_type)
    except ValueError:
        etype = EntityType.CONCEPT  # safe fallback for legacy rows
    return Entity(
        id=row.id,
        canonical_name=row.canonical_name,
        entity_type=etype,
        wikidata_id=row.wikidata_id,
        aliases=list(row.aliases or []),
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _amain() -> int:
    print("Checking AGE permissions...")
    if not await _can_load_age():
        print(
            "ERROR: cannot LOAD 'age' as the current Postgres role.\n"
            f"  Run as a superuser: psql -U postgres -d argus -f {GRANT_SQL_PATH}\n"
            "  See the file for what it grants and why.",
            file=sys.stderr,
        )
        return 1

    g = GraphQuerier()
    print("Ensuring AGE extension + graph...")
    await g.ensure_age_extension()

    print("Loading entities from Postgres...")
    entity_rows = await _stream_entities()
    print(f"  {len(entity_rows)} entity rows.")

    entities_upserted = 0
    for row in entity_rows:
        try:
            await g.upsert_entity(_entity_from_row(row))
            entities_upserted += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "sync_age.upsert_entity_failed", entity_id=str(row.id), error=str(exc)
            )

    print("Loading relations from Postgres...")
    relation_rows = await _stream_relations()
    print(f"  {len(relation_rows)} relation rows.")

    relations_upserted = 0
    for row in relation_rows:
        try:
            await g.upsert_relation(row.subject_id, row.relation_type, row.object_id)
            relations_upserted += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "sync_age.upsert_relation_failed",
                relation_id=str(row.id),
                error=str(exc),
            )

    print(
        f"sync_age complete. entities upserted: {entities_upserted}, "
        f"relations upserted: {relations_upserted}"
    )
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
