from uuid import uuid4

from argus_agents.base import strip_unsupported_claims


def test_strip_unsupported_keeps_only_valid_citation():
    valid = uuid4()
    unknown = uuid4()
    content = (
        f"The treaty was signed in 2024 [ev:{valid}]. "
        f"It was ratified by all parties [ev:{unknown}]."
    )

    cleaned, stripped = strip_unsupported_claims(content, {valid})

    assert f"[ev:{valid}]" in cleaned
    assert f"[ev:{unknown}]" not in cleaned
    assert "treaty" in cleaned
    assert any("ratified" in s for s in stripped)
    assert len(stripped) == 1


def test_strip_unsupported_drops_uncited_sentence():
    valid = uuid4()
    content = (
        f"This is uncited prose. "
        f"This one cites the source [ev:{valid}]."
    )

    cleaned, stripped = strip_unsupported_claims(content, {valid})

    assert "uncited prose" not in cleaned
    assert f"[ev:{valid}]" in cleaned
    assert any("uncited" in s for s in stripped)
