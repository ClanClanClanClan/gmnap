from __future__ import annotations
import os, yaml
from typing import Any, Dict

SPEC_CANDIDATES = ("specs_v7.yaml", "v7.0.yaml")


class SpecError(RuntimeError):
    pass


def load_specs() -> Dict[str, Any]:
    for p in SPEC_CANDIDATES:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data
    return {}
