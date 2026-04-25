from typing import Any

import httpx
from argus_core.logging import get_logger
from argus_core.schemas import Entity, EntityType
from argus_core.settings import get_settings

logger = get_logger(__name__)


_INSTANCE_OF_TO_TYPE: dict[str, EntityType] = {
    "Q5": EntityType.PERSON,
    "Q43229": EntityType.ORG,
    "Q4830453": EntityType.ORG,
    "Q783794": EntityType.ORG,
    "Q3918": EntityType.ORG,
    "Q6256": EntityType.PLACE,
    "Q515": EntityType.PLACE,
    "Q486972": EntityType.PLACE,
    "Q1190554": EntityType.EVENT,
    "Q1656682": EntityType.EVENT,
    "Q2334719": EntityType.POLICY,
    "Q820655": EntityType.POLICY,
    "Q2424752": EntityType.PRODUCT,
    "Q151885": EntityType.CONCEPT,
}


class WikidataClient:
    def __init__(self, timeout: float = 30.0) -> None:
        self._settings = get_settings()
        self.timeout = timeout
        self._headers = {
            "User-Agent": self._settings.wikidata_user_agent,
            "Accept": "application/sparql-results+json",
        }

    async def lookup(self, query: str, limit: int = 10, language: str = "en") -> list[Entity]:
        sparql = self._build_search_sparql(query, limit=limit, language=language)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._settings.wikidata_sparql,
                params={"query": sparql, "format": "json"},
                headers=self._headers,
            )
            resp.raise_for_status()
            payload = resp.json()

        bindings = payload.get("results", {}).get("bindings", [])
        return [self._binding_to_entity(b) for b in bindings]

    @staticmethod
    def _build_search_sparql(query: str, *, limit: int, language: str) -> str:
        safe = query.replace('"', '\\"')
        return f"""
SELECT ?item ?itemLabel ?itemDescription ?instanceOf WHERE {{
  SERVICE wikibase:mwapi {{
    bd:serviceParam wikibase:api "EntitySearch" .
    bd:serviceParam wikibase:endpoint "www.wikidata.org" .
    bd:serviceParam mwapi:search "{safe}" .
    bd:serviceParam mwapi:language "{language}" .
    ?item wikibase:apiOutputItem mwapi:item .
  }}
  OPTIONAL {{ ?item wdt:P31 ?instanceOf . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language}" . }}
}}
LIMIT {limit}
""".strip()

    def _binding_to_entity(self, binding: dict[str, Any]) -> Entity:
        item_uri: str = binding.get("item", {}).get("value", "")
        wikidata_id = item_uri.rsplit("/", 1)[-1] if item_uri else None
        label = binding.get("itemLabel", {}).get("value") or wikidata_id or "(unknown)"
        description = binding.get("itemDescription", {}).get("value")
        instance_uri: str = binding.get("instanceOf", {}).get("value", "")
        instance_qid = instance_uri.rsplit("/", 1)[-1] if instance_uri else ""
        entity_type = _INSTANCE_OF_TO_TYPE.get(instance_qid, EntityType.CONCEPT)

        return Entity(
            canonical_name=label,
            entity_type=entity_type,
            wikidata_id=wikidata_id,
            description=description,
        )
