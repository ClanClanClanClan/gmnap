from __future__ import annotations
from typing import List, Dict, Any
import json
from pathlib import Path


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def write_yaml_sorted(entries: List[Dict[str, Any]], out_path: str) -> None:
    Path(out_path).write_text(canonical_json(entries), encoding="utf-8")
