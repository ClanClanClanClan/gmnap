from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

# docs/specs_v7_clean.yaml is the actual ground-truth spec shipped in the
# repo; the two legacy root-level names never existed here, so every
# spec_loader consumer (attribution, licence checks) raised SpecError
# until R48 added the real path.
SPEC_CANDIDATES = ("docs/specs_v7_clean.yaml", "specs_v7.yaml", "v7.0.yaml")

# R56.4 (real-data pilot): the candidates used to be tried against the
# CURRENT WORKING DIRECTORY only, so any run from outside the repo root
# (CLI invoked from a data directory, installed package, benchmark harness)
# silently lost ATTRIBUTION.txt and licence-tier resolution. Anchor to the
# repo root (this file lives at src/ops/spec_loader.py) first; keep the cwd
# as a fallback for vendored/relocated spec files.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class SpecError(RuntimeError):
    pass


def load_specs() -> Dict[str, Any]:
    """Load the V7 machine-readable spec (specs_v7.yaml preferred, falling back to v7.0.yaml)."""
    for cand in SPEC_CANDIDATES:
        for p in (str(_REPO_ROOT / cand), cand):
            if not os.path.exists(p):
                continue
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise SpecError(f"Spec {p} is not a mapping")
            # sanity checks
            if str(data.get("schema_version", "")).startswith("7"):
                return data
            # If it's a reduced v7.0.yaml, still accept.
            return data
    raise SpecError("No V7 spec file found (tried specs_v7.yaml, v7.0.yaml)")


def get_quality_gates(spec: Dict[str, Any]) -> Dict[str, Any]:
    return spec.get("quality_gates", {}) if isinstance(spec, dict) else {}


def get_region_groups(spec: Dict[str, Any]) -> list[dict]:
    return spec.get("region_groups", []) if isinstance(spec, dict) else []
