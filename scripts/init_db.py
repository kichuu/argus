from __future__ import annotations

import sys
from pathlib import Path

from argus_core.settings import get_settings


def _require_psycopg():
    try:
        import psycopg  # type: ignore
    except ImportError:
        print(
            "psycopg is required for init_db. Install with:\n"
            "  uv add --group dev 'psycopg[binary]>=3.2'",
            file=sys.stderr,
        )
        sys.exit(1)
    return psycopg


def _create_age(psycopg, dsn: str) -> None:
    print("Creating AGE extension...")
    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS age;")


def _create_graph(psycopg, dsn: str, graph_name: str) -> None:
    print(f"Creating graph '{graph_name}'...")
    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        try:
            # AGE must be in session_preload_libraries='age' on the target DB
            # (LOAD 'age' requires superuser). Setup memo:
            #   ALTER DATABASE argus SET session_preload_libraries='age';
            cur.execute('SET search_path = ag_catalog, "$user", public;')
            cur.execute("SELECT create_graph(%s);", (graph_name,))
            print(f"  graph '{graph_name}' created.")
        except Exception as exc:
            msg = str(exc).lower()
            if "already exists" in msg or ("graph" in msg and "exists" in msg):
                print(f"  graph '{graph_name}' already exists; skipping.")
            elif "function create_graph" in msg or "create_graph" in msg and "does not exist" in msg:
                print(
                    f"  ERROR: AGE not loaded for this session ({exc}).\n"
                    f"  Run as superuser, then retry init_db:\n"
                    f"    sudo -u postgres psql -d argus -c "
                    f"\"ALTER DATABASE argus SET session_preload_libraries='age';\"",
                    file=sys.stderr,
                )
                raise
            else:
                print(f"  ERROR creating graph: {exc}", file=sys.stderr)
                raise


def _alembic_upgrade(repo_root: Path) -> None:
    print("Running alembic upgrade head...")
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().alembic_database_url)
    command.upgrade(cfg, "head")


def main() -> int:
    psycopg = _require_psycopg()
    settings = get_settings()
    dsn = settings.alembic_database_url
    repo_root = Path(__file__).resolve().parent.parent

    _create_age(psycopg, dsn)
    _create_graph(psycopg, dsn, "argus_graph")
    _alembic_upgrade(repo_root)
    print("init_db complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
