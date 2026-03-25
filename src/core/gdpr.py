"""GDPR compliance module for GMNAP V7.

Implements:
- GDPR_DATA field marking on entries containing personal data
- Birth year privacy: decade-granular when local cohort < 5
- Scrubber configuration for sources requiring consent
- --drop-personal flag support (ShadowNode insertion)
"""

from __future__ import annotations
import hashlib
import logging
from collections import Counter
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Fields that constitute personal data under GDPR
PERSONAL_DATA_FIELDS = {
    "BirthYear",
    "DeathYear",
    "Gender",
    "Institution",
    "Email",
    "ORCID",
    "Affiliation",
    "Nationality",
}

# Sources requiring GDPR scrubbing (subscription / scraper-based)
SCRUBBER_SOURCES = {"GoogleScholar", "ProQuest", "CNKI"}

# Minimum cohort size for full birth year disclosure
MIN_COHORT_SIZE = 5


def mark_gdpr_fields(entry: Dict[str, Any]) -> None:
    """Mark entry with GDPR_DATA flag if it contains personal data."""
    has_personal = any(entry.get(f) for f in PERSONAL_DATA_FIELDS)
    entry["GDPR_DATA"] = has_personal


def apply_birth_year_privacy(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply decade-granular birth year when local cohort < MIN_COHORT_SIZE.

    Per V7 spec: if fewer than 5 people share the same birth year in the
    same detected region, replace exact birth year with decade (e.g. 1970s).
    """
    # Count (region, birth_year) cohorts
    cohort_counts: Counter = Counter()
    for e in batch:
        region = e.get("DetectedRegion", "R0")
        birth = e.get("BirthYear")
        if birth and isinstance(birth, (int, float)):
            cohort_counts[(region, int(birth))] += 1

    # Apply privacy masking
    for e in batch:
        region = e.get("DetectedRegion", "R0")
        birth = e.get("BirthYear")
        if birth and isinstance(birth, (int, float)):
            birth_int = int(birth)
            count = cohort_counts.get((region, birth_int), 0)
            if count < MIN_COHORT_SIZE:
                decade = (birth_int // 10) * 10
                e["BirthYear_Original"] = birth_int
                e["BirthYear"] = f"{decade}s"
                e["BirthYear_Privacy"] = "decade_masked"

    return batch


def scrub_sources(entry: Dict[str, Any]) -> None:
    """Remove data from sources requiring explicit consent (GDPR Art. 6)."""
    sources = entry.get("_sources", [])
    for src in SCRUBBER_SOURCES:
        if src in sources:
            # Remove source-specific data
            ext_ids = entry.get("AuthorityIDs", entry.get("ExternalIDs", {}))
            ext_ids.pop(src, None)
            sources = [s for s in sources if s != src]
            entry["_sources"] = sources
            logger.debug(f"Scrubbed {src} data from {entry.get('GlobalID', '?')}")


def apply_drop_personal(
    batch: List[Dict[str, Any]], drop_personal: bool = False
) -> List[Dict[str, Any]]:
    """If --drop-personal is set, replace personal data with ShadowNodes.

    A ShadowNode retains the GlobalID and structural relationships but
    strips all personal data fields, replacing them with a hash.
    """
    if not drop_personal:
        return batch

    out = []
    for e in batch:
        shadow = {
            "GlobalID": e.get("GlobalID"),
            "DetectedRegion": e.get("DetectedRegion"),
            "ShadowNode": True,
            "ShadowHash": hashlib.sha256(
                str(e.get("CanonicalLatin", "")).encode("utf-8")
            ).hexdigest()[:16],
        }
        # Preserve structural relationships (non-personal)
        if e.get("Advisors"):
            shadow["Advisors"] = e["Advisors"]
        if e.get("Students"):
            shadow["Students"] = e["Students"]
        if e.get("OrderKey"):
            shadow["OrderKey"] = e["OrderKey"]
        out.append(shadow)

    logger.info(f"Applied --drop-personal: {len(out)} entries converted to ShadowNodes")
    return out


def gdpr_pipeline(batch: List[Dict[str, Any]], drop_personal: bool = False) -> List[Dict[str, Any]]:
    """Full GDPR compliance pass on a batch.

    Steps:
    1. Mark GDPR_DATA fields
    2. Scrub consent-required sources
    3. Apply birth year privacy (decade masking)
    4. Optionally convert to ShadowNodes
    """
    for e in batch:
        mark_gdpr_fields(e)
        scrub_sources(e)

    batch = apply_birth_year_privacy(batch)
    batch = apply_drop_personal(batch, drop_personal=drop_personal)

    return batch
