from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def write_yaml_sorted(entries: List[Dict[str, Any]], out_path: str) -> None:
    Path(out_path).write_text(canonical_json(entries), encoding="utf-8")
