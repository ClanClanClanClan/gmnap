from __future__ import annotations
from typing import Dict, List, Any, Tuple
import os, json, yaml
from ..ops.unicode_norm import normalise_entry_strings


def _load_input(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    if path.endswith(".json"):
        data = json.loads(txt)
    else:
        data = yaml.safe_load(txt)
    if isinstance(data, dict):
        data = [data]
    return data or []


def ingest_and_normalise(path: str) -> List[Dict[str, Any]]:
    """Stage 1: load YAML/JSON and apply Unicode normalisation recursively."""
    batch = _load_input(path)
    return [normalise_entry_strings(e) for e in batch]
