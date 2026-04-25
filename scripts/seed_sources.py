from __future__ import annotations

import sys
from pathlib import Path

import yaml

SEED_PATH = Path("./config/seed_sources.yaml")


def main() -> int:
    if not SEED_PATH.exists():
        print(
            f"No seed file at {SEED_PATH}. Create it with a list of RSS feed URLs "
            "to seed the sources table. Skipping."
        )
        return 0

    raw = yaml.safe_load(SEED_PATH.read_text(encoding="utf-8")) or {}
    feeds = raw.get("feeds", [])
    if not feeds:
        print(f"{SEED_PATH} has no 'feeds' entries; nothing to seed.")
        return 0

    # TODO: wire to argus_core.db.session and upsert SourceModel rows.
    print(f"Found {len(feeds)} feed entries. Seeding not yet implemented.")
    print("TODO: upsert into sources table via argus_core.db.session.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
