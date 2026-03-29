from __future__ import annotations
from typing import Dict, List
from ..regions.manager import get_region


def stage3_region_hooks(batch: List[Dict]) -> List[Dict]:
    out = []
    for e in batch:
        code = e.get("DetectedRegion", "R0")
        region = get_region(code)
        e2 = region.clean(dict(e))
        e2 = region.augment(e2)
        e2 = region.validate(e2)
        out.append(e2)
    return out
