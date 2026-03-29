from __future__ import annotations
from typing import Dict, Any, List
from .policy import ConflictPolicy

ARRAY_FIELDS = {
    "Institution",
    "Advisors",
    "Students",
    "Publications",
    "AlternativeLatin",
    "AlternativeNative",
}
SCALAR_PRIORITY = {"BirthYear", "DeathYear", "DegreeDate"}


def merge_authority_fragments(
    fragments: List[Dict[str, Any]], policy: ConflictPolicy | None = None
) -> Dict[str, Any]:
    policy = policy or ConflictPolicy.load()
    merged: Dict[str, Any] = {}
    # build field→source map
    field_sources: Dict[str, Dict[str, Any]] = {}
    for frag in fragments:
        src = (frag.get("_source") or {}).get("service", "Unknown")
        for k, v in frag.items():
            if k == "_source":
                continue
            field_sources.setdefault(k, {})[src] = v
    for field, by_src in field_sources.items():
        if field in ARRAY_FIELDS:
            # union with stable ordering
            seen = set()
            out = []
            for src, arr in sorted(by_src.items(), key=lambda kv: kv[0]):
                for x in arr or []:
                    if x not in seen:
                        out.append(x)
                        seen.add(x)
            merged[field] = out
        elif field in SCALAR_PRIORITY:
            choice = policy.pick_source(field, by_src)
            merged[field] = by_src[choice]
        else:
            # weighted pick if present, else max length
            best = None
            best_w = -1.0
            for src, val in by_src.items():
                w = policy.weights.get(src, 0.0)
                if w > best_w:
                    best, best_w = val, w
            merged[field] = best
    return merged
