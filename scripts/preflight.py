"""Argus local-dev preflight.

Verifies the things you need before running the Phase 4 baseline pipeline:
- OPENAI_API_KEY set
- Postgres reachable on DATABASE_URL
- alembic head matches code (or warns if not migrated yet)
- Apache AGE extension installed in the cluster (warning, not fatal)
- Configured OpenAI model IDs actually exist in your account

Usage:
    uv run python scripts/preflight.py
"""

from __future__ import annotations

import asyncio
import sys

from argus_core.db.session import get_engine
from argus_core.settings import get_settings
from sqlalchemy import text


def _ok(msg: str) -> None:
    print(f"\033[32m✓\033[0m {msg}")


def _warn(msg: str) -> None:
    print(f"\033[33m⚠\033[0m {msg}")


def _fail(msg: str) -> None:
    print(f"\033[31m✗\033[0m {msg}")


async def _check_openai_key(s) -> bool:
    if not s.openai_api_key:
        _fail("OPENAI_API_KEY is empty in .env")
        return False
    _ok(f"OPENAI_API_KEY present ({len(s.openai_api_key)} chars)")
    return True


async def _check_postgres(s) -> bool:
    safe_url = s.database_url.split("@")[-1] if "@" in s.database_url else s.database_url
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        _ok(f"Postgres reachable at {safe_url}")
        return True
    except Exception as exc:  # noqa: BLE001
        _fail(f"Postgres connection failed at {safe_url}: {exc}")
        return False


async def _check_alembic(s) -> None:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            # Force public schema — AGE may have polluted the role's search_path.
            await conn.execute(text('SET search_path = "$user", public'))
            r = await conn.execute(
                text(
                    "SELECT version_num FROM public.alembic_version "
                    "ORDER BY version_num DESC LIMIT 1"
                )
            )
            row = r.first()
        if row is None:
            _warn(
                "alembic_version table is empty — run `uv run alembic upgrade head` "
                "to create the schema."
            )
            return
        version = row[0]
        if version >= "0002":
            _ok(f"alembic at revision {version}")
        else:
            _warn(
                f"alembic at revision {version} — run `uv run alembic upgrade head` "
                "to apply the AGE migration (0002)."
            )
    except Exception as exc:  # noqa: BLE001
        _warn(
            f"Couldn't read alembic_version (likely never migrated): {exc}. "
            "Run `uv run alembic upgrade head`."
        )


async def _check_age() -> None:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            r = await conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'age'")
            )
            installed = r.scalar() is not None
        if installed:
            _ok("Apache AGE extension installed in cluster")
        else:
            _warn(
                "Apache AGE not installed — graph queries will silently return []. "
                "Install: https://age.apache.org/age-manual/master/intro/setup.html"
            )
    except Exception as exc:  # noqa: BLE001
        _warn(f"Couldn't check AGE extension: {exc}")


async def _check_openai_models(s) -> None:
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=s.openai_api_key)
        page = await client.models.list()
        available = {m.id for m in page.data}
    except Exception as exc:  # noqa: BLE001
        _warn(f"Couldn't list OpenAI models: {exc}")
        return

    targets = [
        ("synthesis", s.default_synthesis_model),
        ("extractor", s.default_extractor_model),
        ("verifier", s.default_verifier_model),
        ("research", s.default_research_model),
        ("persona", s.default_persona_model),
        ("master", s.default_master_model),
        ("critic", s.default_critic_model),
    ]
    bad: list[tuple[str, str]] = []
    for label, model in targets:
        if model in available:
            _ok(f"{label} model {model!r} available")
        else:
            _fail(f"{label} model {model!r} NOT available in your account")
            bad.append((label, model))

    if bad:
        _warn(
            "Suggested swaps (verify against platform.openai.com/docs/models): "
            "use a current chat model (e.g. gpt-4.1 or gpt-5 if your account has it) "
            "and a reasoning model (e.g. o4-mini) for the verifier."
        )


async def main() -> int:
    print("Argus preflight\n" + "=" * 40)
    s = get_settings()

    have_key = await _check_openai_key(s)
    db_ok = await _check_postgres(s)
    if not db_ok:
        return 1
    await _check_alembic(s)
    await _check_age()
    if have_key:
        await _check_openai_models(s)

    print()
    print("done. fix any ✗ before running scripts/run_baseline.py")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
