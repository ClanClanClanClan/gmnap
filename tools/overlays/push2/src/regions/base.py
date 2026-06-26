from __future__ import annotations

from typing import Any, Dict


class RegionBase:
    code = "R0"

    def clean(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        return entry

    def augment(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        return entry

    def validate(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        return entry
