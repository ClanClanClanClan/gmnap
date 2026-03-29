from __future__ import annotations

import re
from typing import Dict, List


def _unique(xs: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def tag_short_forms(entry: Dict) -> Dict:
    tags: List[str] = list(entry.get("tags", []))
    name = entry.get("CanonicalLatin", "") or ""

    # Initials‑only (e.g., "A. B. C.")
    if re.fullmatch(r"(?:[A-Z]\.\s*){1,}(?:[A-Z]\.)?", name):
        tags.append("initials_only")

    # Generational suffix (Jr, Sr, III, IV)
    if re.search(r"\b(Jr|Sr|III|IV)\b", name):
        tags.append("generational_suffix")

    # Contains abbreviations (at least one period in uppercase token)
    if re.search(r"\b[A-Z]\.", name):
        tags.append("has_abbreviations")

    entry["tags"] = _unique(tags)
    return entry
