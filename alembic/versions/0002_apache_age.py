"""apache age graph (runtime-managed; this migration is a no-op)

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-25

AGE setup (`CREATE EXTENSION age`, `LOAD 'age'`, `SELECT create_graph(...)`)
is typically superuser-only and varies by deployment. We deliberately do NOT
try it here — a single failed AGE statement poisons the alembic transaction
and blocks the version-write at the end.

Instead, `argus_retrieval.graph.GraphQuerier.ensure_age_extension()` runs the
same setup at first use, with each statement isolated in its own session so a
permission failure on one step doesn't break the others. If AGE isn't usable
under the application role, graph queries silently return `[]` and the rest
of the pipeline is unaffected.

To enable AGE manually:
    psql argus -c "CREATE EXTENSION IF NOT EXISTS age;"
    psql argus -c "GRANT USAGE ON SCHEMA ag_catalog TO argus;"
    # then start the app — graph.py will create the 'argus_graph' graph on first use.
"""
from __future__ import annotations

from typing import Sequence, Union

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
