from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from argus_retrieval.graph import GraphQuerier


def _patch_session_scope(monkeypatch: pytest.MonkeyPatch, fetchall_rows: list[tuple]):
    executed: list[str] = []

    result = MagicMock()
    result.fetchall.return_value = fetchall_rows

    session = MagicMock()

    async def execute(stmt, params=None):
        executed.append(str(stmt))
        return result

    session.execute = execute

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "argus_retrieval.graph.session_scope", lambda: _Ctx()
    )
    return executed


@pytest.mark.asyncio
async def test_neighbors_runs_age_init_then_cypher(monkeypatch: pytest.MonkeyPatch) -> None:
    target = uuid4()
    neighbor = uuid4()
    executed = _patch_session_scope(monkeypatch, [(f'"{neighbor}"',)])

    g = GraphQuerier(graph_name="argus_graph")
    out = await g.neighbors(target, hops=1, limit=10)

    assert out == [neighbor]
    assert any("LOAD 'age'" in s for s in executed)
    assert any("ag_catalog" in s for s in executed)
    cypher_calls = [s for s in executed if "cypher(" in s]
    assert cypher_calls, "expected at least one cypher() call"
    assert "MATCH" in cypher_calls[0]
    assert ":Entity" in cypher_calls[0]
    assert str(target) in cypher_calls[0]


@pytest.mark.asyncio
async def test_traverse_returns_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    a = uuid4()
    b = uuid4()
    via = uuid4()
    executed = _patch_session_scope(
        monkeypatch, [(f'["{a}", "{via}", "{b}"]',)]
    )

    g = GraphQuerier()
    paths = await g.traverse(a, b, max_hops=3)

    assert paths == [[a, via, b]]
    cypher_calls = [s for s in executed if "cypher(" in s]
    assert cypher_calls
    assert "nodes(p)" in cypher_calls[0]


@pytest.mark.asyncio
async def test_semantic_scan_excludes_seeds(monkeypatch: pytest.MonkeyPatch) -> None:
    seed = uuid4()
    found = uuid4()
    executed = _patch_session_scope(monkeypatch, [(f'"{found}"',)])

    g = GraphQuerier()
    out = await g.semantic_scan([seed])

    assert out == [found]
    cypher_calls = [s for s in executed if "cypher(" in s]
    assert cypher_calls
    assert "NOT b.id IN" in cypher_calls[0]


@pytest.mark.asyncio
async def test_semantic_scan_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    executed = _patch_session_scope(monkeypatch, [])
    g = GraphQuerier()
    assert await g.semantic_scan([]) == []
    assert executed == []


@pytest.mark.asyncio
async def test_neighbors_swallows_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Ctx:
        async def __aenter__(self):
            raise RuntimeError("AGE not installed")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("argus_retrieval.graph.session_scope", lambda: _Ctx())
    g = GraphQuerier()
    result = await g.neighbors(UUID(int=1))
    assert result == []
