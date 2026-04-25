"""apache age graph

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-25

Creates the Apache AGE extension and the `argus_graph` graph used by
`packages/retrieval/src/argus_retrieval/graph.py`.

If AGE is not installed at the cluster level, the upgrade emits a clear
RuntimeError pointing at the install docs. The downgrade drops the graph and
extension best-effort and tolerates them being absent.

Install reference: https://age.apache.org/age-manual/master/intro/setup.html
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GRAPH_NAME = "argus_graph"


def upgrade() -> None:
    bind = op.get_bind()

    try:
        bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS age")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Apache AGE extension is not installed in this Postgres cluster. "
            "Install it before running this migration: "
            "https://age.apache.org/age-manual/master/intro/setup.html"
        ) from exc

    bind.exec_driver_sql("LOAD 'age'")
    bind.exec_driver_sql('SET search_path = ag_catalog, "$user", public')

    try:
        bind.exec_driver_sql(f"SELECT create_graph('{GRAPH_NAME}')")
    except Exception:
        # create_graph raises if the graph already exists; idempotent re-run.
        pass


def downgrade() -> None:
    bind = op.get_bind()
    try:
        bind.exec_driver_sql("LOAD 'age'")
        bind.exec_driver_sql('SET search_path = ag_catalog, "$user", public')
        bind.exec_driver_sql(f"SELECT drop_graph('{GRAPH_NAME}', true)")
    except Exception:
        pass
    try:
        bind.exec_driver_sql("DROP EXTENSION IF EXISTS age")
    except Exception:
        pass
