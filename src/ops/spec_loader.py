from __future__ import annotations
import os
import yaml
from typing import Any, Dict

SPEC_CANDIDATES = ("docs/specs_v7_clean.yaml", "specs_v7.yaml", "v7.0.yaml")


class SpecError(RuntimeError):
    pass


def load_specs() -> Dict[str, Any]:
    """Load the V7 machine-readable spec (specs_v7_clean.yaml preferred)."""
    for p in SPEC_CANDIDATES:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise SpecError(f"Spec {p} is not a mapping")
            return data
    raise SpecError(f"No V7 spec file found (tried {', '.join(SPEC_CANDIDATES)})")


def get_quality_gates(spec: Dict[str, Any]) -> Dict[str, Any]:
    return spec.get("quality_gates", {}) if isinstance(spec, dict) else {}


def get_region_groups(spec: Dict[str, Any]) -> list[dict]:
    return spec.get("region_groups", []) if isinstance(spec, dict) else []
