"""Seed the five stock Argus personas via direct DB insert.

This script writes directly to the ``personas`` table using
``argus_core.db.session.session_scope`` rather than going through the API,
so it works during a fresh-DB bootstrap before ``argus_api`` is running.

Behavior:
- Default: idempotent — for each persona in the canonical list, insert if
  no row already exists with the same ``frame``; otherwise leave it alone.
- ``--reset``: hard-delete every existing persona row before seeding.

Usage:
    uv run python scripts/seed_personas.py
    uv run python scripts/seed_personas.py --reset
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from argus_core.db.models import PersonaModel
from argus_core.db.session import session_scope
from sqlalchemy import delete, select


# The five stock personas. Order is presentation-only; nothing else relies on it.
STOCK_PERSONAS: list[dict[str, object]] = [
    {
        "frame": "Skeptical Empiricist",
        "description": (
            "Tests every claim against verifiable sources; defaults to "
            "'unverified' until evidence is unambiguous; flags reliance on "
            "a single outlet."
        ),
        "knowledge_emphasis": [
            "statistics",
            "evidence_quality",
            "epistemology",
            "fact-checking",
        ],
    },
    {
        "frame": "Regulator Viewpoint",
        "description": (
            "Reasons from compliance, jurisdiction, and treaty obligations; "
            "surfaces what rules apply to whom."
        ),
        "knowledge_emphasis": [
            "international_law",
            "sanctions",
            "compliance",
            "treaties",
        ],
    },
    {
        "frame": "Operator on the Ground",
        "description": (
            "Translates abstract policy into concrete operational impact; "
            "flags second-order effects military or commercial actors will "
            "face."
        ),
        "knowledge_emphasis": [
            "operations",
            "logistics",
            "supply_chains",
            "military_doctrine",
        ],
    },
    {
        "frame": "Historical Analogue Analyst",
        "description": (
            "Maps current events onto historical precedents; warns when "
            "current dynamics rhyme with prior crises."
        ),
        "knowledge_emphasis": [
            "history",
            "comparative_politics",
            "escalation_dynamics",
        ],
    },
    {
        "frame": "Affected-Stakeholder Advocate",
        "description": (
            "Centers the impact on civilians, labor, and frontline "
            "communities; flags claims that abstract away human cost."
        ),
        "knowledge_emphasis": [
            "human_rights",
            "civilian_impact",
            "frontline_reporting",
        ],
    },
]


async def _existing_frames() -> set[str]:
    async with session_scope() as session:
        rows = (await session.execute(select(PersonaModel.frame))).all()
        return {r[0] for r in rows}


async def _hard_delete_all() -> int:
    async with session_scope() as session:
        result = await session.execute(delete(PersonaModel))
        return int(result.rowcount or 0)


async def _insert_missing(existing: set[str]) -> tuple[int, int]:
    """Insert any stock persona whose frame is not already present.

    Returns ``(existed, new)``.
    """
    existed = 0
    new = 0
    async with session_scope() as session:
        for spec in STOCK_PERSONAS:
            frame = str(spec["frame"])
            if frame in existing:
                existed += 1
                continue
            session.add(
                PersonaModel(
                    frame=frame,
                    description=str(spec["description"]),
                    knowledge_emphasis=list(spec["knowledge_emphasis"]),  # type: ignore[arg-type]
                )
            )
            new += 1
    return existed, new


async def main(args: argparse.Namespace) -> int:
    if args.reset:
        deleted = await _hard_delete_all()
        print(f"Reset: deleted {deleted} existing persona row(s).")
        existing: set[str] = set()
    else:
        existing = await _existing_frames()

    existed, new = await _insert_missing(existing)
    total = existed + new
    print(f"Seeded {total} personas ({existed} existed, {new} new).")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Seed the five stock Argus personas (idempotent by frame)."
    )
    p.add_argument(
        "--reset",
        action="store_true",
        help="Hard-delete all existing personas before seeding.",
    )
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(parse_args())))
