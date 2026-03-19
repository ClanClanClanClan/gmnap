"""Stage 7: TagShortForms - Populate ShortFormClusters."""
from __future__ import annotations
import re, logging
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Patterns for short-form detection
_INITIALS_RE = re.compile(r"^[A-Z]\.$|^[A-Z]\.\s*[A-Z]\.$")
_ABBREV_RE = re.compile(r"\b[A-Z][a-z]?\.\s")
_GEN_SUFFIX_RE = re.compile(r"\b(Jr|Sr|II|III|IV|V)\b\.?$")


def tag_short_forms(batch: List[Dict]) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Stage 7: Annotate entries with short-form tags and compute ShortFormClusters.

    Per V7 spec: ShortFormClusters = Map {short_form -> count} where count =
    number of distinct external occurrences.

    Returns (annotated_batch, shortform_clusters).
    """
    clusters: Dict[str, int] = Counter()
    out = []

    for e in batch:
        tags = []
        canonical = e.get("CanonicalLatin", "")
        parts = canonical.split(",", 1)
        family = parts[0].strip() if parts else ""
        given = parts[1].strip() if len(parts) > 1 else ""

        # Check for initials-only given name
        if given and _INITIALS_RE.match(given):
            tags.append("initials_only")

        # Check for abbreviations in name
        if _ABBREV_RE.search(canonical):
            tags.append("has_abbreviations")

        # Check for generational suffix
        if _GEN_SUFFIX_RE.search(canonical):
            tags.append("generational_suffix")

        # Build short forms for clustering
        short_forms = _generate_short_forms(family, given)
        for sf in short_forms:
            clusters[sf] += 1

        # Collect observed variants from external sources
        variants_observed = e.get("VariantsObserved", [])
        for v in variants_observed:
            vstr = v.get("str", v) if isinstance(v, dict) else str(v)
            if vstr and vstr != canonical:
                clusters[vstr] += 1

        if tags:
            e["ShortFormTags"] = tags
        e["ShortFormClusters"] = {sf: clusters[sf] for sf in short_forms if clusters[sf] > 0}
        out.append(e)

    return out, dict(clusters)


def _generate_short_forms(family: str, given: str) -> List[str]:
    """Generate plausible short forms for a name."""
    forms = []
    if not family:
        return forms

    # Family only
    forms.append(family)

    if given:
        # Initial + Family
        initial = given[0] if given else ""
        if initial:
            forms.append(f"{family}, {initial}.")

        # Given Family (western order)
        forms.append(f"{given} {family}")

        # Multi-part given: first initial only
        given_parts = given.split()
        if len(given_parts) > 1:
            initials = " ".join(p[0] + "." for p in given_parts if p)
            forms.append(f"{family}, {initials}")

    return forms
