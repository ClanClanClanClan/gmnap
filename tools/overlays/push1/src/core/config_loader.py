from __future__ import annotations
import os, yaml, json
from typing import Dict, Any


def load_specs(paths=("specs_v7.yaml", "v7.0.yaml")) -> Dict[str, Any]:
    """Load the first available spec file (machine-readable)."""
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                if p.endswith(".yaml") or p.endswith(".yml"):
                    return yaml.safe_load(f) or {}
                return json.load(f)
    return {}


def runtime_profile(specs: Dict[str, Any], mode: str = "Quick") -> Dict[str, Any]:
    profiles = specs.get("runtime_profiles") or []
    for prof in profiles:
        if str(prof.get("mode")).lower() == mode.lower():
            return prof
    return {}
