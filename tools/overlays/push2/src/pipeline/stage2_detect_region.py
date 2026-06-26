from __future__ import annotations

from typing import Dict, List, Tuple

from ..regions.detector import detect_region


def stage2_detect_region(batch: List[Dict]) -> List[Dict]:
    out = []
    for e in batch:
        e2 = dict(e)
        e2["DetectedRegion"] = detect_region(e2)
        out.append(e2)
    return out
