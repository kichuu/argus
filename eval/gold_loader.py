from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from eval.gold_schema import GoldClaim


class GoldSchemaError(Exception):
    def __init__(self, line_no: int, source_id: str | None, original: Exception) -> None:
        self.line_no = line_no
        self.source_id = source_id
        self.original = original
        super().__init__(
            f"gold.jsonl line {line_no} (id={source_id!r}): {type(original).__name__}: {original}"
        )


def load_gold_claims(path: Path) -> list[GoldClaim]:
    if not path.exists():
        return []
    items: list[GoldClaim] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise GoldSchemaError(line_no, None, exc) from exc
            try:
                items.append(GoldClaim.model_validate(obj))
            except ValidationError as exc:
                raise GoldSchemaError(line_no, str(obj.get("id", "?")), exc) from exc
    return items
