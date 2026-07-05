"""GDPR compliance utilities.

V7 spec section 11 calls for four operations:

1. **Field marking** — flag every entry that contains personal data
   (BirthYear, BirthDate, DeathYear, DeathDate, Email, ORCID, …) so
   downstream consumers can apply policies.
2. **Birth-year privacy** — when fewer than ``MIN_COHORT_SIZE``
   mathematicians share a (region, decade) cohort, mask the exact
   birth year to a decade label so individual identification is
   harder. Larger cohorts pass through.
3. **Source scrubbing** — drop ToS-incompatible authority sources
   (GoogleScholar, ProQuest, CNKI) from any record before it hits
   public output.
4. **ShadowNode conversion** (``--drop-personal``) — replace the
   record with a structural skeleton: GlobalID + DetectedRegion +
   Advisors/Students/OrderKey + a deterministic ShadowHash, and drop
   every personal field. Used for archival shares with stricter
   privacy obligations than even cohort-masked output.

The end-to-end ``gdpr_pipeline`` runs (1)→(2)→(3)→(4) in order.

This module previously exposed only ``shadow_node`` (a hand-built
ShadowNode constructor). Tests for the full API existed but failed
to import. Restored here against the test contract pinned in
``tests/unit/test_gdpr.py`` and ``tests/unit/test_gdpr_comprehensive.py``.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any, Dict, List, Set

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fields that contain personal information about a living or recently-
# deceased individual. Presence triggers ``GDPR_DATA: True``.
PERSONAL_DATA_FIELDS: Set[str] = frozenset(
    {
        "BirthYear",
        "BirthDate",
        "DeathYear",
        "DeathDate",
        "Email",
        "ORCID",
        "AffiliationTimeline",
        "Country",
        "Institution",
    }
)

# Minimum cohort size before exact birth-year is preserved. Smaller
# cohorts get decade-masked. Conservative default per V7 §11.
MIN_COHORT_SIZE: int = 5

# Authority sources whose Terms of Service forbid public re-distribution
# of harvested fields. Records carrying these in ``_sources`` /
# ``AuthorityIDs`` get them stripped before hitting public output.
SCRUBBED_SOURCES: Set[str] = frozenset({"GoogleScholar", "ProQuest", "CNKI"})


# ---------------------------------------------------------------------------
# 1. Field marking
# ---------------------------------------------------------------------------


def mark_gdpr_fields(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Mark ``entry`` with ``GDPR_DATA: True`` iff it carries any
    field in ``PERSONAL_DATA_FIELDS``.

    Mutates and returns the entry.
    """
    entry["GDPR_DATA"] = any(
        field in entry and entry[field] not in (None, "")
        for field in PERSONAL_DATA_FIELDS
    )
    return entry


# ---------------------------------------------------------------------------
# 2. Birth-year privacy (decade masking for small cohorts)
# ---------------------------------------------------------------------------


def _decade_label(year: int) -> str:
    """1985 → "1980s". Negative or non-int input returns "unknown"."""
    try:
        decade = (int(year) // 10) * 10
        return f"{decade}s"
    except (TypeError, ValueError):
        return "unknown"


def apply_birth_year_privacy(
    batch: List[Dict[str, Any]],
    *,
    min_cohort_size: int = MIN_COHORT_SIZE,
) -> List[Dict[str, Any]]:
    """Mask exact ``BirthYear`` to a decade label when the
    (DetectedRegion, decade) cohort has fewer than ``min_cohort_size``
    members in this batch.

    Mutates each entry in place; also returns the list so the call
    site reads naturally.

    Behaviour:
      - Entries lacking ``BirthYear`` are untouched.
      - Cohort key is ``(DetectedRegion, decade)``. Different regions
        with the same decade are independent cohorts.
      - When masked, set ``BirthYear`` to e.g. ``"1980s"`` and stash
        the original under ``BirthYear_Original``; mark
        ``BirthYear_Privacy = "decade_masked"``.
      - When NOT masked (cohort large enough), leave the entry alone.
    """
    cohort_counts: Counter = Counter()
    for e in batch:
        by = e.get("BirthYear")
        if by in (None, ""):
            continue
        key = (e.get("DetectedRegion"), _decade_label(by))
        cohort_counts[key] += 1

    for e in batch:
        by = e.get("BirthYear")
        if by in (None, ""):
            continue
        key = (e.get("DetectedRegion"), _decade_label(by))
        if cohort_counts[key] < min_cohort_size:
            e["BirthYear_Original"] = by
            e["BirthYear"] = _decade_label(by)
            e["BirthYear_Privacy"] = "decade_masked"
        # else: cohort large enough, exact year survives
    return batch


# ---------------------------------------------------------------------------
# 3. Source scrubbing (ToS-incompatible sources)
# ---------------------------------------------------------------------------


def scrub_sources(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Strip every entry in ``SCRUBBED_SOURCES`` from this record's
    ``_sources`` list and ``AuthorityIDs`` dict (both optional).

    Idempotent. Mutates the entry in place.
    """
    sources = entry.get("_sources")
    if isinstance(sources, list):
        entry["_sources"] = [s for s in sources if s not in SCRUBBED_SOURCES]
    auth = entry.get("AuthorityIDs")
    if isinstance(auth, dict):
        entry["AuthorityIDs"] = {
            k: v for k, v in auth.items() if k not in SCRUBBED_SOURCES
        }
    # Defense-in-depth: the legacy manager / external inputs carry
    # ``AuthoritySources`` as a list of {"source": name, ...} dicts (or
    # plain names). The live tier orchestrator writes ``_sources``, but a
    # ToS-scrubbed source must not survive in EITHER shape (R47 §3.1).
    auth_sources = entry.get("AuthoritySources")
    if isinstance(auth_sources, list):
        entry["AuthoritySources"] = [
            s
            for s in auth_sources
            if (s.get("source") if isinstance(s, dict) else s) not in SCRUBBED_SOURCES
        ]
    return entry


# ---------------------------------------------------------------------------
# 4. ShadowNode conversion
# ---------------------------------------------------------------------------

# Fields preserved in a ShadowNode. Every other field is dropped.
_SHADOW_PRESERVE: Set[str] = frozenset(
    {
        "GlobalID",
        "DetectedRegion",
        "Advisors",
        "Students",
        "OrderKey",
    }
)


def _shadow_hash(entry: Dict[str, Any]) -> str:
    """Deterministic 16-char hex hash of the entry's CanonicalLatin
    (or empty string if absent). Used so that two records for the
    same person produce the same ShadowHash, which lets downstream
    consumers de-dupe across snapshots without retaining the name.
    """
    payload = (entry.get("CanonicalLatin") or "").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def shadow_node(global_id: str) -> Dict[str, Any]:
    """Hand-built ShadowNode for a known GlobalID.

    Used by the legacy CLI ``--drop-personal`` flag for entries the
    pipeline never saw (e.g. an erasure request for a GlobalID that
    doesn't exist in the current run). Kept for back-compat; the
    real ShadowNode conversion in ``apply_drop_personal`` is what
    most callers want.
    """
    return {
        "GlobalID": global_id,
        "CanonicalLatin": "GDPR-ERASED",
        "Field": "Mathematics",
        "Source": "GDPR",
        "LastUpdated": "1970-01-01T00:00:00Z",
        "ValidationStatus": "verified",
        "GDPR": True,
    }


def apply_drop_personal(
    batch: List[Dict[str, Any]], *, drop_personal: bool = False
) -> List[Dict[str, Any]]:
    """Convert each entry to a ShadowNode when ``drop_personal=True``.

    A ShadowNode preserves only the structural fields needed for
    downstream graph operations (advisor chain, region clustering)
    and replaces personal data with a deterministic hash.

    When ``drop_personal=False`` the batch is returned unchanged.
    """
    if not drop_personal:
        return batch
    out: List[Dict[str, Any]] = []
    for entry in batch:
        shadow: Dict[str, Any] = {
            "ShadowNode": True,
            "ShadowHash": _shadow_hash(entry),
        }
        for f in _SHADOW_PRESERVE:
            if f in entry:
                shadow[f] = entry[f]
        out.append(shadow)
    return out


# ---------------------------------------------------------------------------
# End-to-end pipeline
# ---------------------------------------------------------------------------


def gdpr_pipeline(
    batch: List[Dict[str, Any]], *, drop_personal: bool = False
) -> List[Dict[str, Any]]:
    """Run all four GDPR operations in V7-spec order.

    1. Mark ``GDPR_DATA`` on every entry
    2. Scrub ToS-incompatible sources (GoogleScholar / ProQuest / CNKI)
    3. Apply birth-year cohort masking
    4. Optionally collapse to ShadowNodes (``--drop-personal``)

    The order matters: scrub before mask so the privacy operations
    can't accidentally leak through a soon-to-be-stripped source
    field; ShadowNode conversion last so the structural fields it
    preserves have already been cleaned up.
    """
    for e in batch:
        mark_gdpr_fields(e)
        scrub_sources(e)
    apply_birth_year_privacy(batch)
    return apply_drop_personal(batch, drop_personal=drop_personal)
