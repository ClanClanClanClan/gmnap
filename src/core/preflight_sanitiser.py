from __future__ import annotations
from typing import Dict, Any

_REGION_ALIAS = {"A1": "a1_anglo_sphere", "E4": "e4_korea"}


def sanitise_entry(e: Dict[str, Any]) -> Dict[str, Any]:
    if "GlobalID" not in e and "ID" in e:
        e["GlobalID"] = e["ID"]
    if "Region" in e and e["Region"] in _REGION_ALIAS:
        e["Region"] = _REGION_ALIAS[e["Region"]]
    return e
