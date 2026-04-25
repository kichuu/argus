from __future__ import annotations

from uuid import UUID

from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import Entity
from sqlalchemy import text

logger = get_logger(__name__)

GRAPH_NAME = "argus_graph"


_AGE_LOAD = "LOAD 'age'"
_AGE_SEARCH_PATH = 'SET search_path = ag_catalog, "$user", public'


class GraphQuerier:
    def __init__(self, graph_name: str = GRAPH_NAME) -> None:
        self._graph = graph_name

    async def ensure_age_extension(self) -> None:
        # Each step uses its own session so a failure (e.g. graph already exists)
        # doesn't poison the transaction for the next step.
        try:
            async with session_scope() as session:
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS age"))
        except Exception as e:
            logger.warning("age_create_extension_failed", error=str(e))

        try:
            async with session_scope() as session:
                await session.execute(text(_AGE_LOAD))
                await session.execute(text(_AGE_SEARCH_PATH))
        except Exception as e:
            logger.warning("age_load_failed", error=str(e))

        try:
            async with session_scope() as session:
                await session.execute(text(_AGE_LOAD))
                await session.execute(text(_AGE_SEARCH_PATH))
                await session.execute(
                    text(f"SELECT create_graph('{self._graph}')")
                )
            logger.info("graph_created", graph=self._graph)
        except Exception as e:
            logger.debug("graph_create_skipped", error=str(e), graph=self._graph)

    async def _exec_cypher(
        self,
        session_cypher: str,
        return_cols: str = "(v agtype)",
        params: dict[str, str] | None = None,
    ) -> list[tuple]:
        # AGE Cypher is wrapped: SELECT * FROM cypher('graph', $$ ... $$) AS (col agtype).
        async with session_scope() as session:
            await session.execute(text(_AGE_LOAD))
            await session.execute(text(_AGE_SEARCH_PATH))
            sql = (
                f"SELECT * FROM cypher('{self._graph}', $$ {session_cypher} $$) "
                f"AS {return_cols}"
            )
            result = await session.execute(text(sql), params or {})
            return [tuple(row) for row in result.fetchall()]

    async def upsert_entity(self, entity: Entity) -> None:
        eid = str(entity.id)
        name = entity.canonical_name.replace("'", "\\'")
        etype = entity.entity_type.value
        cypher = (
            f"MERGE (e:Entity {{id: '{eid}'}}) "
            f"SET e.name = '{name}', e.type = '{etype}' "
            f"RETURN e.id"
        )
        try:
            await self._exec_cypher(cypher, return_cols="(id agtype)")
        except Exception as e:
            logger.warning("upsert_entity_failed", error=str(e), entity_id=eid)

    async def upsert_relation(
        self, subject_id: UUID, relation_type: str, object_id: UUID
    ) -> None:
        sid = str(subject_id)
        oid = str(object_id)
        # Relation type sanitised to avoid injection in label position.
        rel = "".join(c for c in relation_type.upper() if c.isalnum() or c == "_") or "REL"
        cypher = (
            f"MATCH (a:Entity {{id: '{sid}'}}), (b:Entity {{id: '{oid}'}}) "
            f"MERGE (a)-[r:{rel}]->(b) "
            f"RETURN r"
        )
        try:
            await self._exec_cypher(cypher, return_cols="(r agtype)")
        except Exception as e:
            logger.warning(
                "upsert_relation_failed",
                error=str(e),
                subject=sid,
                object=oid,
                rel=rel,
            )

    async def neighbors(
        self, entity_id: UUID, hops: int = 1, limit: int = 50
    ) -> list[UUID]:
        eid = str(entity_id)
        hops = max(1, int(hops))
        limit = max(1, int(limit))
        cypher = (
            f"MATCH (a:Entity {{id: '{eid}'}})-[*1..{hops}]-(b:Entity) "
            f"RETURN DISTINCT b.id LIMIT {limit}"
        )
        try:
            rows = await self._exec_cypher(cypher, return_cols="(id agtype)")
        except Exception as e:
            logger.warning("neighbors_query_failed", error=str(e), entity_id=eid)
            return []

        out: list[UUID] = []
        for row in rows:
            raw = row[0]
            if raw is None:
                continue
            # agtype scalars come back as strings like '"<uuid>"' (quoted JSON).
            s = str(raw).strip()
            if s.startswith('"') and s.endswith('"'):
                s = s[1:-1]
            try:
                out.append(UUID(s))
            except (ValueError, AttributeError):
                continue
        return out
