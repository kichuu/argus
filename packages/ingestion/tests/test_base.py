import hashlib
import re

from argus_ingestion.base import compute_content_hash, normalize_text


def test_compute_content_hash_is_deterministic():
    text = "the sky is blue"
    h1 = compute_content_hash(text)
    h2 = compute_content_hash(text)
    assert h1 == h2


def test_compute_content_hash_matches_sha256():
    text = "argus ingestion"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert compute_content_hash(text) == expected
    assert re.fullmatch(r"[0-9a-f]{64}", compute_content_hash(text))


def test_compute_content_hash_differs_for_different_inputs():
    assert compute_content_hash("a") != compute_content_hash("b")


def test_normalize_text_strips_html():
    html = "<p>Hello <b>world</b></p>"
    assert normalize_text(html) == "Hello world"


def test_normalize_text_collapses_whitespace():
    raw = "  hello\n\n   world\t\tfoo  "
    assert normalize_text(raw) == "hello world foo"


def test_normalize_text_handles_empty():
    assert normalize_text("") == ""


def test_normalize_text_handles_nested_tags_and_whitespace():
    html = "<div><p>One</p>  <p>Two\nlines</p></div>"
    assert normalize_text(html) == "One Two lines"
