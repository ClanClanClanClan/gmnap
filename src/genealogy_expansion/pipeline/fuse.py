from __future__ import annotations
import yaml, hashlib
from typing import Dict, Any, List


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


SCORING = None


def init(config_dir: str = "config"):
    global SCORING
    SCORING = load_yaml(f"{config_dir}/scoring.yml")


def provenance_hash(edge: Dict[str, Any]) -> str:
    h = hashlib.sha1()
    h.update(str(sorted(edge.get("sources", []))).encode("utf-8"))
    h.update(
        (edge.get("student_global_id", "") + edge.get("advisor_global_id", "")).encode("utf-8")
    )
    return h.hexdigest().upper()


def score_edge(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        return None
    weights = SCORING["source_weights"]
    base = 0.0
    srcs = set()
    best = None
    for c in candidates:
        sw = max((weights.get(s, 0.0) for s in c.get("sources", [])), default=0.0)
        if sw > base:
            base = sw
            best = c
        srcs.update(c.get("sources", []))

    # If no source matched scoring weights, use first candidate
    if best is None:
        best = candidates[0]
        base = 0.1  # Minimal score for unscored sources

    bonus = min(0.06, SCORING["bonuses"]["multi_source_agreement"] * max(0, len(srcs) - 1))
    conf = max(0.0, min(0.99, base + bonus))
    best = dict(best)
    best["confidence"] = conf
    best["provenance_hash"] = provenance_hash(best)
    best["verified"] = conf >= SCORING["thresholds"]["auto_verified_min"]
    return best
