from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from argus_core.settings import get_settings


class TrustTier(BaseModel):
    tier: int = Field(ge=1, le=4)
    label: str
    description: str
    weight: float = Field(ge=0.0, le=1.0)
    examples: list[str] = []


class TrustConfig(BaseModel):
    tiers: list[TrustTier]
    domain_overrides: dict[str, int] = Field(
        default_factory=dict,
        description="Map of domain (e.g. 'reuters.com') -> tier int",
    )

    def tier_for_domain(self, domain: str) -> int:
        domain = domain.lower().lstrip("www.")
        if domain in self.domain_overrides:
            return self.domain_overrides[domain]
        return 4

    def weight_for_tier(self, tier: int) -> float:
        for t in self.tiers:
            if t.tier == tier:
                return t.weight
        return 0.0


@lru_cache(maxsize=1)
def load_trust_config(path: Path | None = None) -> TrustConfig:
    settings = get_settings()
    target = path or settings.trust_tiers_path
    if not target.exists():
        return TrustConfig(tiers=_default_tiers())
    raw = yaml.safe_load(target.read_text())
    return TrustConfig.model_validate(raw)


def _default_tiers() -> list[TrustTier]:
    return [
        TrustTier(tier=1, label="primary", description="Official records, peer-reviewed, primary docs", weight=1.0),
        TrustTier(tier=2, label="established", description="Major news wires, established outlets", weight=0.8),
        TrustTier(tier=3, label="secondary", description="Regional/specialist outlets, vetted blogs", weight=0.5),
        TrustTier(tier=4, label="unvetted", description="Unknown or unvetted sources", weight=0.2),
    ]
