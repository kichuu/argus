from pathlib import Path

import pytest
from argus_core.personas import (
    PersonaLibrary,
    PersonaTemplate,
    load_persona_library,
)
from argus_core.schemas import Persona
from pydantic import ValidationError


def _config_path() -> Path:
    # repo root: packages/core/tests/test_personas.py -> ../../../config
    return Path(__file__).resolve().parents[3] / "config" / "personas.yaml"


def test_load_persona_library_covers_all_verticals() -> None:
    load_persona_library.cache_clear()
    lib = load_persona_library(_config_path())
    assert isinstance(lib, PersonaLibrary)
    expected = {"finance", "climate", "civic", "geopolitics", "general"}
    assert expected.issubset(set(lib.verticals.keys()))
    total = sum(len(v) for v in lib.verticals.values())
    assert total >= 25


def test_for_vertical_finance_returns_at_least_five_templates() -> None:
    load_persona_library.cache_clear()
    lib = load_persona_library(_config_path())
    finance = lib.for_vertical("finance", include_general=False)
    assert len(finance) >= 5
    for tpl in finance:
        assert isinstance(tpl, PersonaTemplate)


def test_for_vertical_appends_general_when_requested() -> None:
    load_persona_library.cache_clear()
    lib = load_persona_library(_config_path())
    base = lib.for_vertical("finance", include_general=False)
    with_general = lib.for_vertical("finance", include_general=True)
    assert len(with_general) > len(base)


def test_to_personas_produces_runtime_persona_instances() -> None:
    lib = PersonaLibrary(
        verticals={
            "finance": [
                PersonaTemplate(
                    frame="central bank monetary-policy view",
                    description="cautious lens",
                    knowledge_emphasis=["rates"],
                )
            ]
        }
    )
    personas = lib.to_personas(lib.for_vertical("finance", include_general=False))
    assert len(personas) == 1
    assert isinstance(personas[0], Persona)
    assert personas[0].frame == "central bank monetary-policy view"


def test_persona_template_rejects_act_as_prefix() -> None:
    with pytest.raises(ValidationError):
        PersonaTemplate(frame="Act as Janet Yellen", description="bad")


def test_persona_template_rejects_you_are_prefix() -> None:
    with pytest.raises(ValidationError):
        PersonaTemplate(frame="You are a banker", description="bad")


def test_load_persona_library_returns_empty_when_missing() -> None:
    load_persona_library.cache_clear()
    lib = load_persona_library(Path("/nonexistent/personas.yaml"))
    assert isinstance(lib, PersonaLibrary)
    assert lib.verticals == {}
