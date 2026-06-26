from __future__ import annotations

from typing import Any, Dict

from .base import RegionBase


class RegionE1(RegionBase):
    code = "E1"

    def clean(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder for CJK: keep CanonicalLatin as-is; Stage 8 ensures round-trip
        return entry
