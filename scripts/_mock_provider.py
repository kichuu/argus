"""Dev-only stubs for run_discussion.py.

Defines a fake LLM provider, a fake claim extractor, and a local gold-backed
retriever. Lives outside argus_extraction to keep the real package free of
test scaffolding.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from argus_core.schemas import Source
from argus_extraction.providers.base import Provider
from argus_extraction.schemas import ExtractionResult
from pydantic import BaseModel

_EV_PATTERN = re.compile(r"\[ev:([0-9a-fA-F-]{36})\]")
_FALLBACK_FRAMES: tuple[tuple[str, str, list[str]], ...] = (
    (
        "regulator viewpoint",
        "Reads the evidence through a rules-and-mandates lens, focused on what "
        "the cited authority actually decided.",
        ["policy", "compliance", "official actions"],
    ),
    (
        "skeptical analyst",
        "Treats hedged language and missing context as load-bearing; flags "
        "anything that is not literally in the cited span.",
        ["uncertainty", "hedging", "limits of evidence"],
    ),
    (
        "affected stakeholder",
        "Speaks for the people or entities materially affected by the cited "
        "decisions; sticks to what the evidence implies for them.",
        ["impact", "real-world stakes", "affected parties"],
    ),
)

_VERTICAL_PREFIX = {"finance": "fin-", "climate": "cli-", "health": "hea-"}


def gold_id_to_uuid(gold_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"argus.gold:{gold_id}")


class _GoldEntry(BaseModel):
    id: str
    source_url: str
    source_text: str
    statement: str
    expected_verbatim_span: str
    expected_char_start: int
    expected_char_end: int


def load_gold(path: Path, vertical: str) -> list[_GoldEntry]:
    prefix = _VERTICAL_PREFIX.get(vertical.lower())
    if prefix is None:
        raise ValueError(
            f"unknown vertical {vertical!r}; expected one of {sorted(_VERTICAL_PREFIX)}"
        )
    entries: list[_GoldEntry] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if not data["id"].startswith(prefix):
                continue
            entries.append(_GoldEntry.model_validate(data))
    return entries


def gold_to_source(entry: _GoldEntry) -> Source:
    import hashlib

    return Source(
        id=gold_id_to_uuid(entry.id),
        url=entry.source_url,  # type: ignore[arg-type]
        title=f"Gold {entry.id}",
        content_hash=hashlib.sha256(entry.source_text.encode("utf-8")).hexdigest(),
        raw_text=entry.source_text,
        fetched_at=datetime.now(UTC),
        trust_tier=1,
    )


class LocalGoldRetriever:
    """Returns matching gold rows as RetrievedSpan objects.

    Lives here rather than in argus_retrieval because it is dev-only scaffolding.
    """

    def __init__(self, gold_path: Path, vertical: str) -> None:
        self._entries = load_gold(gold_path, vertical)
        self._sources: dict[UUID, Source] = {}
        for entry in self._entries:
            src = gold_to_source(entry)
            self._sources[src.id] = src

    @property
    def sources(self) -> dict[UUID, Source]:
        return self._sources

    async def retrieve(self, topic: str, top_k: int = 24) -> list[Any]:
        from argus_retrieval.types import RetrievedSpan

        spans: list[Any] = []
        for entry in self._entries[:top_k]:
            src = self._sources[gold_id_to_uuid(entry.id)]
            spans.append(
                RetrievedSpan(
                    verbatim_span=entry.expected_verbatim_span,
                    char_start=entry.expected_char_start,
                    char_end=entry.expected_char_end,
                    source_id=src.id,
                    fetched_at=src.fetched_at,
                    trust_tier=src.trust_tier,
                    score=1.0 - (0.01 * len(spans)),
                )
            )
        _ = topic
        return spans


class MockExtractor:
    """Drop-in replacement for ClaimExtractor in mock mode."""

    async def extract(self, source: Source) -> ExtractionResult:
        _ = source
        return ExtractionResult(claims=[], entities=[], relations=[])


class MockProvider(Provider):
    """Schema-aware fake LLM provider.

    Inspects the requested schema's class name and the evidence UUIDs already
    embedded in the prompt to synthesize a deterministic, valid response.
    """

    name = "mock"

    async def structured_extract(
        self,
        prompt: str,
        schema: type[BaseModel],
        model: str,
    ) -> BaseModel:
        _ = model
        evidence_ids = _EV_PATTERN.findall(prompt)
        schema_name = schema.__name__

        if schema_name == "_PersonaSlate":
            return self._build_persona_slate(schema)
        if schema_name == "_CriticReport":
            return schema.model_validate({"verdicts": []})
        if schema_name == "_ClaimSlate":
            return self._build_claim_slate(schema, prompt, evidence_ids)
        raise RuntimeError(
            f"MockProvider has no canned response for schema {schema_name!r}"
        )

    async def text_complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 512,
    ) -> str:
        _ = model, max_tokens
        evidence_ids = _EV_PATTERN.findall(prompt)
        if not evidence_ids:
            return ""
        sentences = [
            f"The cited evidence reflects the topic at hand [ev:{eid}]."
            for eid in evidence_ids[:4]
        ]
        return " ".join(sentences)

    @staticmethod
    def _build_persona_slate(schema: type[BaseModel]) -> BaseModel:
        proposals = [
            {
                "frame": frame,
                "description": desc,
                "knowledge_emphasis": list(emph),
            }
            for frame, desc, emph in _FALLBACK_FRAMES
        ]
        return schema.model_validate({"personas": proposals})

    @staticmethod
    def _build_claim_slate(
        schema: type[BaseModel],
        prompt: str,
        evidence_ids: list[str],
    ) -> BaseModel:
        seen: set[str] = set()
        unique_ids: list[str] = []
        for eid in evidence_ids:
            if eid not in seen:
                seen.add(eid)
                unique_ids.append(eid)

        spans = _extract_spans_from_prompt(prompt)
        claims = []
        for eid in unique_ids:
            statement = spans.get(eid) or f"Evidence {eid} is in the pack."
            claims.append(
                {
                    "statement": statement,
                    "supporting_evidence_ids": [eid],
                    "contradicting_evidence_ids": [],
                    "agree": 3,
                    "disagree": 0,
                    "uncertain": 0,
                }
            )
        return schema.model_validate({"claims": claims})


def _extract_spans_from_prompt(prompt: str) -> dict[str, str]:
    """Best-effort recovery of `'span'` for each `[ev:UUID]` in a synth prompt.

    Synth/master/persona prompts render evidence as: `- [ev:UUID] 'verbatim text'`.
    We pull the quoted span back out so mock claims read like real ones.
    """
    pattern = re.compile(r"\[ev:([0-9a-fA-F-]{36})\]\s+(['\"])(.*?)\2")
    out: dict[str, str] = {}
    for match in pattern.finditer(prompt):
        eid, _quote, text = match.group(1), match.group(2), match.group(3)
        out.setdefault(eid, text)
    return out
