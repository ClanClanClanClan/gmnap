"""
src/ml/router_dynamic.py
Drop-in dynamic router for Phase‑1 rules & Phase‑2 ML.
"""

from dataclasses import dataclass
from typing import Dict, Optional

# Regions where ML is consistently superior (non‑Latin, distinctive)
PHASE2_STRONG = {
    "E1",
    "E3",
    "E4",
    "B1",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7",
    "C8",
    "C9",
    "D1",
    "D2",
    "D3",
    "D5",
    "E2",
    "E5",
    "E6",
    "F1",
    "F2",
    "F3",
    "F4",
    "H1",
}

# Regions where Phase‑1 rules tend to be safer (Latin/ambiguous)
PHASE1_PREFERRED = {"A1", "A2", "A3", "A4", "A5", "G1", "D4", "E7"}

IBEROPHONE_AMBIGUOUS = ("G1", "A2", "E7", "A1")


@dataclass
class Result:
    region: str
    confidence: float
    distribution: Optional[Dict[str, float]] = None
    method: str = ""


def _merge_distributions(*dists: Dict[str, float]) -> Dict[str, float]:
    agg: Dict[str, float] = {}
    for d in dists:
        for k, v in (d or {}).items():
            agg[k] = agg.get(k, 0.0) + v
    s = sum(agg.values()) or 1.0
    return {k: v / s for k, v in agg.items()}


def route(
    name: str,
    phase1_fn,
    phase2_fn,
    phase1_calibration: Dict[str, float] = None,
    phase2_calibration: Dict[str, float] = None,
) -> Result:
    """
    phase1_fn, phase2_fn must return Result(region, confidence, distribution)
    phase*_calibration: optional per‑region expected accuracy in [0,1].
    """
    r1: Result = phase1_fn(name)
    r2: Result = phase2_fn(name)

    # High‑confidence short‑circuit
    if r2.confidence >= 0.95:
        return Result(
            r2.region, r2.confidence, r2.distribution, method="phase2_highconf"
        )
    if r1.confidence >= 0.95:
        return Result(
            r1.region, r1.confidence, r1.distribution, method="phase1_highconf"
        )

    # Prefer ML in strong regions
    if r2.region in PHASE2_STRONG:
        return Result(
            r2.region, r2.confidence, r2.distribution, method="phase2_region_pref"
        )

    # Prefer Phase‑1 where Latin ambiguity is common
    if r1.region in PHASE1_PREFERRED:
        # Special case: Iberophone ambiguity — emit multi‑label when disagreement persists
        if (
            r1.region in IBEROPHONE_AMBIGUOUS
            and r2.region in IBEROPHONE_AMBIGUOUS
            and r1.region != r2.region
        ):
            dist = _merge_distributions(
                {k: 0.25 for k in IBEROPHONE_AMBIGUOUS},  # prior
                r1.distribution or {},
                r2.distribution or {},
            )
            best = max(dist, key=dist.get)
            return Result(best, dist[best], dist, method="hybrid_ibero_multilabel")
        return Result(
            r1.region, r1.confidence, r1.distribution, method="phase1_region_pref"
        )

    # Agreement → pick higher confidence
    if r1.region == r2.region:
        if r2.confidence >= r1.confidence:
            return Result(
                r2.region, r2.confidence, r2.distribution, method="agree_phase2_higher"
            )
        return Result(
            r1.region, r1.confidence, r1.distribution, method="agree_phase1_higher"
        )

    # Fall back: weighted by per‑region calibration if provided
    if phase1_calibration or phase2_calibration:
        c1 = (phase1_calibration or {}).get(r1.region, 0.8) * r1.confidence
        c2 = (phase2_calibration or {}).get(r2.region, 0.8) * r2.confidence
        if c2 >= c1:
            return Result(
                r2.region, r2.confidence, r2.distribution, method="calibrated_phase2"
            )
        return Result(
            r1.region, r1.confidence, r1.distribution, method="calibrated_phase1"
        )

    # Default tie‑breaker → Phase‑1
    return Result(r1.region, r1.confidence, r1.distribution, method="fallback_phase1")
