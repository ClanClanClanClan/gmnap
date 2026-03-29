from __future__ import annotations
from typing import Dict, Any
from .base import RegionBase


class RegionA1(RegionBase):
    code = "A1"

    def clean(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure "Family, Given" order for Latin ASCII
        name = entry.get("CanonicalLatin", "")
        if "," not in name and name:
            parts = name.split()
            if len(parts) >= 2:
                entry["CanonicalLatin"] = f"{parts[-1]}, {' '.join(parts[:-1])}"
        return entry
