from __future__ import annotations
from typing import Dict, Any
from .base import RegionBase
from .regions_a1 import RegionA1
from .regions_e1 import RegionE1

_REGISTRY = {
    "A1": RegionA1,
    "E1": RegionE1,
}


def get_region(code: str) -> RegionBase:
    cls = _REGISTRY.get(code, RegionBase)
    return cls()
