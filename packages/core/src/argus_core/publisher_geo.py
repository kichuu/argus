"""Domain -> publisher HQ coordinates for source-level map pins.

Loader for config/publisher_locations.yaml. Used by the world endpoint
so Sources can be pinned without a per-source DB column or runtime
geocoding round-trip.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field

from argus_core.settings import get_settings


class PublisherLocation(BaseModel):
    city: str
    country: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class PublisherGeoConfig(BaseModel):
    publishers: dict[str, PublisherLocation] = Field(default_factory=dict)

    def lookup(self, host_or_url: str) -> PublisherLocation | None:
        host = _extract_host(host_or_url).lower()
        if not host:
            return None
        if host in self.publishers:
            return self.publishers[host]
        # Try without www. prefix
        bare = host.removeprefix("www.")
        if bare in self.publishers:
            return self.publishers[bare]
        # Try matching parent domain (one level up). Cheap subdomain fallback.
        parts = bare.split(".")
        if len(parts) >= 2:
            parent = ".".join(parts[-2:])
            if parent in self.publishers:
                return self.publishers[parent]
        return None


def _extract_host(value: str) -> str:
    if not value:
        return ""
    if "://" in value:
        return urlparse(value).hostname or ""
    return value.split("/", 1)[0]


@lru_cache(maxsize=1)
def load_publisher_geo(path: Path | None = None) -> PublisherGeoConfig:
    settings = get_settings()
    target = path or (Path(__file__).resolve().parents[3] / "config" / "publisher_locations.yaml")
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    if not target.exists():
        # also try project root resolution via settings.trust_tiers_path's parent
        candidate = settings.trust_tiers_path.parent / "publisher_locations.yaml"
        if candidate.exists():
            target = candidate
        else:
            return PublisherGeoConfig()
    raw = yaml.safe_load(target.read_text()) or {}
    return PublisherGeoConfig.model_validate(raw)
