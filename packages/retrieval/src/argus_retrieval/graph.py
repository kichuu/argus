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
        return _agtype_rows_to_uuids(rows)

    async def traverse(
        self,
        start_entity_id: UUID,
        end_entity_id: UUID,
        max_hops: int = 3,
        limit: int = 10,
    ) -> list[list[UUID]]:
        sid = str(start_entity_id)
        oid = str(end_entity_id)
        max_hops = max(1, int(max_hops))
        limit = max(1, int(limit))
        cypher = (
            f"MATCH p = (a:Entity {{id: '{sid}'}})-[*1..{max_hops}]-(b:Entity {{id: '{oid}'}}) "
            f"RETURN [n IN nodes(p) | n.id] AS path "
            f"LIMIT {limit}"
        )
        try:
            rows = await self._exec_cypher(cypher, return_cols="(path agtype)")
        except Exception as e:
            logger.warning("traverse_query_failed", error=str(e), start=sid, end=oid)
            return []

        paths: list[list[UUID]] = []
        for row in rows:
            raw = row[0]
            if raw is None:
                continue
            ids = _agtype_list_to_uuids(raw)
            if ids:
                paths.append(ids)
        return paths

    async def semantic_scan(
        self, entity_ids: list[UUID], limit: int = 100
    ) -> list[UUID]:
        if not entity_ids:
            return []
        ids_literal = ", ".join(f"'{str(e)}'" for e in entity_ids)
        limit = max(1, int(limit))
        cypher = (
            f"MATCH (a:Entity)-[]-(b:Entity) "
            f"WHERE a.id IN [{ids_literal}] AND NOT b.id IN [{ids_literal}] "
            f"RETURN DISTINCT b.id LIMIT {limit}"
        )
        try:
            rows = await self._exec_cypher(cypher, return_cols="(id agtype)")
        except Exception as e:
            logger.warning(
                "semantic_scan_failed",
                error=str(e),
                seed_count=len(entity_ids),
            )
            return []
        return _agtype_rows_to_uuids(rows)


def _agtype_to_str(raw: object) -> str:
    s = str(raw).strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s


def _agtype_rows_to_uuids(rows: list[tuple]) -> list[UUID]:
    out: list[UUID] = []
    for row in rows:
        raw = row[0]
        if raw is None:
            continue
        try:
            out.append(UUID(_agtype_to_str(raw)))
        except (ValueError, AttributeError):
            continue
    return out


def _agtype_list_to_uuids(raw: object) -> list[UUID]:
    import json

    s = str(raw).strip()
    # AGE returns lists as JSON-encoded agtype, e.g. '["uuid1", "uuid2"]'.
    try:
        parsed = json.loads(s)
    except (ValueError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    out: list[UUID] = []
    for item in parsed:
        try:
            out.append(UUID(str(item)))
        except (ValueError, AttributeError):
            continue
    return out
