from __future__ import annotations
from typing import Dict, Any, List
import asyncio
import logging

logger = logging.getLogger(__name__)

# Tier 0 — free, no auth
from .openalex_adapter import OpenAlexAdapter
from .crossref_adapter import CrossrefAdapter
from .crossref_thesis_adapter import CrossrefThesisAdapter
from .orcid_etd_adapter import ORCIDETDAdapter

# Tier 1 — free, rate-limited
from .wikidata_p184_adapter import WikidataP184Adapter
from .oai_university_adapter import OAIUniversityAdapter
from .hal_adapter import HALAdapter
from .gnd_adapter import GNDAdapter
from .zbmath_open_adapter import ZbMathOpenAdapter

try:
    from .merge_authority_data import merge_authority_fragments
except Exception:
    # Fallback simple merger
    def merge_authority_fragments(frags: List[Dict[str, Any]], _=None) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for f in frags:
            for k, v in f.items():
                if k == "_source":
                    continue
                if isinstance(v, list):
                    out.setdefault(k, [])
                    for x in v:
                        if x not in out[k]:
                            out[k].append(x)
                else:
                    out[k] = out.get(k, v)
        return out


# Tier 0: free, no auth — always run
TIER_0_ADAPTERS = [
    OpenAlexAdapter,
    CrossrefAdapter,
    CrossrefThesisAdapter,
    ORCIDETDAdapter,
]

# Tier 1: free, rate-limited — run in full/extreme mode
TIER_1_ADAPTERS = [
    WikidataP184Adapter,
    OAIUniversityAdapter,
    HALAdapter,
    GNDAdapter,
    ZbMathOpenAdapter,
]

# All adapters for quick dispatch
ALL_ADAPTERS = TIER_0_ADAPTERS + TIER_1_ADAPTERS


async def enrich_all(
    entry: Dict[str, Any],
    cfg: Dict[str, Any] | None = None,
    tiers: List[int] | None = None,
) -> Dict[str, Any]:
    """Enrich an entry using authority adapters.

    Args:
        entry: Entry dict with at least CanonicalLatin.
        cfg: Per-adapter config overrides.
        tiers: Which tiers to run (default [0]). Use [0,1] for full mode.
    """
    if tiers is None:
        tiers = [0]

    adapters = []
    if 0 in tiers:
        adapters.extend(TIER_0_ADAPTERS)
    if 1 in tiers:
        adapters.extend(TIER_1_ADAPTERS)

    if not adapters:
        return {}

    instances = [cls((cfg or {}).get(cls.__name__, {})) for cls in adapters]
    tasks = [inst.enrich(entry) for inst in instances]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    fragments = []
    for inst, r in zip(instances, results):
        if isinstance(r, Exception):
            logger.debug(f"Authority {inst.name} failed: {r}")
            continue
        if isinstance(r, dict):
            fragments.append(r)

    merged = merge_authority_fragments(fragments, None)
    merged["_sources"] = [
        f.get("_source", {}).get("service") for f in fragments if f.get("_source", {}).get("hit")
    ]

    # Synthesize AffiliationTimeline from Institution + country data
    # Schema requires 'country' (2-letter ISO) on each item — skip if unavailable
    if "Institution" in merged and "AffiliationTimeline" not in merged:
        cc = merged.get("InstitutionCountry", "")
        if cc:
            insts = merged.get("_InstitutionAll") or (
                [merged["Institution"]] if isinstance(merged.get("Institution"), str) else []
            )
            timeline = [{"institution": inst, "country": cc} for inst in insts if inst]
            if timeline:
                merged["AffiliationTimeline"] = timeline

    # Move alternative name forms to Variants.Synthesised (not NameEvents — schema requires 'year')
    if "AlternativeLatin" in merged:
        alts = merged.pop("AlternativeLatin", [])
        canonical = entry.get("CanonicalLatin", "")
        synth = [
            {"str": alt, "type": "authority-alias"} for alt in alts if alt and alt != canonical
        ]
        if synth:
            merged.setdefault("Variants", {}).setdefault("Synthesised", []).extend(synth)

    return merged
