"""Spec §10 licence tiers (R50 — MASTERPLAN §5 'BUILD MISSING').

Maps every authority source to one of the spec's three redistribution
tiers, from its spec §9 ``licence`` value:

- ``public_cc0``            — CC0 sources; freely redistributable
- ``redistributable_cc-by`` — CC-BY sources; redistributable w/ attribution
- ``non-redistributable``   — everything else (Mixed / Subscription /
  Elsevier / DigitalScience / Commercial / Scraping)

Consumers filter output per tier (e.g. a public CC0 export drops fields
whose only provenance is a non-redistributable source).
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict

from src.ops.spec_loader import load_specs

PUBLIC_CC0 = "public_cc0"
REDISTRIBUTABLE_CC_BY = "redistributable_cc-by"
NON_REDISTRIBUTABLE = "non-redistributable"

_LICENCE_TO_TIER = {
    "CC0": PUBLIC_CC0,
    "CC-BY": REDISTRIBUTABLE_CC_BY,
}


def _norm(s: str) -> str:
    """Collapse the spec's U+2011 hyphens / U+00A0 spaces to ASCII."""
    return re.sub(r"[\s\u00a0]+", "_", str(s).replace("\u2011", "-"))


@lru_cache(maxsize=1)
def source_tiers() -> Dict[str, str]:
    """Source name -> tier, for all spec §9 sources (both the raw and the
    underscore-normalised spellings, matching the orchestrator's names)."""
    tiers: Dict[str, str] = {}
    for src in load_specs().get("authority_sources", []) or []:
        service = src.get("service")
        if not service:
            continue
        licence = _norm(src.get("licence", "")).replace("_", "-")
        tier = _LICENCE_TO_TIER.get(licence.replace("-", ""), None)
        if tier is None:
            tier = _LICENCE_TO_TIER.get(licence, NON_REDISTRIBUTABLE)
        tiers[str(service)] = tier
        tiers[_norm(service)] = tier
    return tiers


def tier_for_source(source: str) -> str:
    """Tier for a source name; unknown sources are conservatively
    non-redistributable."""
    t = source_tiers()
    return t.get(source) or t.get(_norm(source)) or NON_REDISTRIBUTABLE
