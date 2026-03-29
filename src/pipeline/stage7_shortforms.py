from __future__ import annotations
import re
from typing import Dict, List, Tuple

_INITIALS_ONLY = re.compile(r"^(?:[A-Z]\.\s*){1,}(?:[A-Z]\.)?$")
_HAS_ABBREV = re.compile(r"\b[A-Z]\.")
_GEN_SUFFIX = re.compile(r"\b(Jr|Sr|III|IV|II)\b", re.IGNORECASE)


def _unique(xs: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def annotate_short_forms(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    tags: List[str] = list(entry.get("tags", []))
    if _INITIALS_ONLY.fullmatch(name):
        tags.append("initials_only")
    if _HAS_ABBREV.search(name):
        tags.append("has_abbreviations")
    if _GEN_SUFFIX.search(name):
        tags.append("generational_suffix")
    entry["tags"] = _unique(tags)
    return entry


def _family_given(canonical_latin: str) -> Tuple[str, str]:
    if "," in canonical_latin:
        family, given = [t.strip() for t in canonical_latin.split(",", 1)]
    else:
        parts = canonical_latin.strip().split()
        if len(parts) >= 2:
            family = parts[-1]
            given = " ".join(parts[:-1])
        else:
            family = canonical_latin.strip()
            given = ""
    return family, given


def _to_short_form(canonical_latin: str) -> str | None:
    family, given = _family_given(canonical_latin)
    if not family or not given:
        return None
    initials = " ".join(f"{p[0]}." for p in re.split(r"[\s\-]+", given) if p and p[0].isalpha())
    if not initials:
        return None
    return f"{initials} {family}"


def compute_short_form_clusters(batch: List[Dict]) -> Tuple[List[Dict], Dict[str, int]]:
    clusters: Dict[str, int] = {}
    out: List[Dict] = []
    for e in batch:
        e2 = annotate_short_forms(dict(e))
        sf = _to_short_form(e2.get("CanonicalLatin", "") or "")
        if sf:
            clusters[sf] = clusters.get(sf, 0) + 1
        out.append(e2)
    return out, clusters
