from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.gold_loader import GoldSchemaError, load_gold_claims

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = REPO_ROOT / "eval" / "gold.jsonl"


def test_gold_loader_loads_items() -> None:
    claims = load_gold_claims(GOLD_PATH)
    assert len(claims) >= 1
    assert claims[0].expected_verbatim_span
    assert claims[0].id


def test_gold_loader_raises_on_bad_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not valid json\n", encoding="utf-8")
    with pytest.raises(GoldSchemaError) as exc_info:
        load_gold_claims(bad)
    assert exc_info.value.line_no == 1


def test_gold_loader_raises_on_missing_field(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"id": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(GoldSchemaError) as exc_info:
        load_gold_claims(bad)
    assert exc_info.value.line_no == 1
    assert exc_info.value.source_id == "x"


def test_gold_loader_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert load_gold_claims(tmp_path / "nope.jsonl") == []
