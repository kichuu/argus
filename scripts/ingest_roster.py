"""Argus roster ingest CLI.

Manual replacement for the (not-yet-built) Temporal cron that would run the
geopolitics feed roster every ~15 minutes. For now an operator runs this
script directly:

    uv run python scripts/ingest_roster.py
    uv run python scripts/ingest_roster.py --group wire_services
    uv run python scripts/ingest_roster.py --dry-run
    uv run python scripts/ingest_roster.py --max-items-override 3

How the roster works
--------------------
* The roster lives in ``config/feeds.yaml``. Each feed belongs to a group,
  and each group declares a ``trust_tier`` (1 = primary/official,
  2 = established outlets, etc. — see ``config/trust_tiers.yaml``).
* This script loads the YAML, expands the per-feed ``max_items`` from
  ``defaults.max_items_per_feed`` if not set, then for each feed it
  builds an RSS ingestion config and invokes the existing
  ``fetch_source`` activity (the same one Temporal would call). It is
  the activity, not this script, that actually persists rows into the
  ``sources`` table and dedups by ``content_hash``.

Adding a new feed
-----------------
1. Pick the group in ``config/feeds.yaml`` whose ``trust_tier`` matches
   how trustworthy the publisher is.
2. Add an entry::

       - name: Some Outlet
         url: https://example.com/rss

3. Run ``uv run python scripts/ingest_roster.py --group <group_name>``
   to confirm it ingests cleanly. No code changes required.

Disabling a feed
----------------
Add ``disabled: true`` and a ``note:`` explaining why::

    - name: Flaky Source
      url: https://flaky.example.com/feed
      disabled: true
      note: "Returns 503 since 2026-04-20; awaiting upstream fix."

The script will print ``skipped: <name> (<reason>)`` and move on.

Why we don't auto-discover feeds
--------------------------------
Argus is a citation-grounded platform; trust-tier curation is the whole
point. Auto-discovery (e.g., walking sitemaps or scraping aggregators)
would mix unvetted sources into evidence retrieval and undercut the
trust-tier weighting that downstream ranking and embargo rules rely on.
Adding a feed should be a deliberate, reviewed act.

How trust tiers flow through
----------------------------
For each feed we extract the URL host with ``urllib.parse.urlparse``
and pass ``{<host>: <group.trust_tier>}`` as
``trust_tier_overrides`` in the activity config. Inside ``RSSConnector``
this short-circuits the global ``trust_tiers.yaml`` lookup, so the
group's tier wins for items whose link host matches. The resolved
integer ends up on ``SourceModel.trust_tier`` and from there flows into
retrieval/ranking and the JSONB ``trust_tier`` payload on indexed
evidence spans.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

DEFAULT_CONFIG = Path("./config/feeds.yaml")
PROBE_TIMEOUT_S = 10.0


def _load_roster(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERR roster file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as exc:
        print(f"ERR malformed YAML in {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(raw, dict):
        print(f"ERR roster {path} must be a mapping at the top level", file=sys.stderr)
        sys.exit(1)

    if not isinstance(raw.get("groups"), list) or not raw["groups"]:
        print(f"ERR roster {path} has no 'groups' list", file=sys.stderr)
        sys.exit(1)

    return raw


def _expand_defaults(roster: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the roster into a list of per-feed dicts with defaults applied."""
    defaults = roster.get("defaults") or {}
    default_max = int(defaults.get("max_items_per_feed", 5))

    flat: list[dict[str, Any]] = []
    for group in roster["groups"]:
        if not isinstance(group, dict):
            continue
        gname = group.get("name") or "(unnamed)"
        gtier = int(group.get("trust_tier", 4))
        for feed in group.get("feeds") or []:
            if not isinstance(feed, dict):
                continue
            entry = {
                "group": gname,
                "trust_tier": gtier,
                "name": feed.get("name") or feed.get("url") or "(unnamed)",
                "url": feed.get("url"),
                "disabled": bool(feed.get("disabled", False)),
                "note": feed.get("note"),
                "max_items": int(feed.get("max_items", default_max)),
            }
            flat.append(entry)
    return flat


def _probe(url: str) -> tuple[bool, str]:
    """HEAD-probe a URL. Returns (ok, reason)."""
    try:
        r = httpx.head(url, timeout=PROBE_TIMEOUT_S, follow_redirects=True)
    except httpx.HTTPError as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if r.status_code >= 400:
        return False, f"HTTP {r.status_code}"
    return True, f"HTTP {r.status_code}"


async def _run_feed(feed: dict[str, Any]) -> tuple[int, str | None]:
    """Invoke fetch_source for one feed. Returns (n_persisted, error_str)."""
    # Imported lazily so --help / --dry-run don't pay the import cost
    # (fetch_source pulls in SQLAlchemy, Temporal, the ingestion stack, etc.).
    from argus_workers.activities.fetch import fetch_source  # type: ignore

    host = urlparse(feed["url"]).hostname or ""
    cfg = {
        "kind": "rss",
        "feed_urls": [feed["url"]],
        "max_items": feed["max_items"],
        "trust_tier_overrides": {host: feed["trust_tier"]} if host else {},
    }

    # Temporal's @activity.defn can wrap the function; prefer the
    # unwrapped coroutine when present so we don't trip activity-context
    # assertions when calling outside a worker.
    runner = getattr(fetch_source, "__wrapped__", fetch_source)
    try:
        ids = await runner(cfg)
    except TypeError:
        # If __wrapped__ existed but had a different signature, fall back.
        ids = await fetch_source(cfg)
    return len(ids or []), None


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ingest_roster",
        description=(
            "Ingest the curated geopolitics feed roster (config/feeds.yaml) "
            "through the Argus fetch_source activity. Manual stand-in for a "
            "scheduled Temporal cron."
        ),
    )
    p.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Path to roster YAML (default: {DEFAULT_CONFIG})",
    )
    p.add_argument(
        "--group",
        type=str,
        default=None,
        help="Only ingest feeds in this group name (e.g. wire_services)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List feeds and probe URLs without invoking fetch_source",
    )
    p.add_argument(
        "--max-items-override",
        type=int,
        default=None,
        metavar="N",
        help="Override max_items for every feed (otherwise per-feed/default)",
    )
    return p.parse_args()


async def _amain(args: argparse.Namespace) -> int:
    roster = _load_roster(args.config)
    vertical = roster.get("vertical", "(unknown)")
    feeds = _expand_defaults(roster)

    if args.group:
        feeds = [f for f in feeds if f["group"] == args.group]
        if not feeds:
            print(f"ERR no feeds found in group {args.group!r}", file=sys.stderr)
            return 1

    if args.max_items_override is not None:
        for f in feeds:
            f["max_items"] = int(args.max_items_override)

    n_groups = len({f["group"] for f in feeds})
    print(
        f"Argus roster ingest: {vertical}, {len(feeds)} feeds across {n_groups} groups"
        + (f" (dry-run)" if args.dry_run else "")
    )

    by_group_persisted: dict[str, int] = {}
    by_group_feeds: dict[str, int] = {}
    total_persisted = 0
    total_attempted = 0
    total_skipped = 0

    for feed in feeds:
        name = feed["name"]
        group = feed["group"]
        url = feed["url"]
        by_group_feeds[group] = by_group_feeds.get(group, 0) + 1

        if not url:
            print(f"skipped: {name} (no url)")
            total_skipped += 1
            continue

        if feed["disabled"]:
            reason = feed.get("note") or "disabled: true"
            print(f"skipped: {name} ({reason})")
            total_skipped += 1
            continue

        ok, why = _probe(url)
        if not ok:
            print(f"skipped: {name} (probe failed: {why})")
            total_skipped += 1
            continue

        if args.dry_run:
            print(
                f"DRY  {name}: would fetch up to {feed['max_items']} items "
                f"from {url} (group={group}, tier={feed['trust_tier']}, probe={why})"
            )
            continue

        total_attempted += 1
        t0 = time.perf_counter()
        try:
            n, err = await _run_feed(feed)
        except Exception as exc:  # noqa: BLE001
            dur = time.perf_counter() - t0
            print(f"ERR  {name}: {type(exc).__name__}: {exc} ({dur:.2f}s)")
            continue
        dur = time.perf_counter() - t0

        if err:
            print(f"ERR  {name}: {err} ({dur:.2f}s)")
            continue

        print(f"OK   {name}: {n} source(s) ({dur:.2f}s)")
        total_persisted += n
        by_group_persisted[group] = by_group_persisted.get(group, 0) + n

    print()
    if args.dry_run:
        print(
            f"Dry run complete: {len(feeds)} feeds inspected, "
            f"{total_skipped} skipped, 0 persisted"
        )
        return 0

    for group in by_group_feeds:
        gp = by_group_persisted.get(group, 0)
        gf = by_group_feeds[group]
        print(f"  group {group}: {gp} source(s) across {gf} feed(s)")
    print(
        f"Roster complete: {total_persisted} sources persisted across "
        f"{total_attempted} feeds ({total_skipped} skipped)"
    )
    return 0


def main() -> int:
    args = _parse_args()
    try:
        return asyncio.run(_amain(args))
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
