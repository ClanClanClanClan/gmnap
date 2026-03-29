from __future__ import annotations

import json
import math
from typing import Any

VOLATILE_KEYS = {"ProcessedAt", "ProcessingLatencyMs", "_debug", "_trace_id", "_meta"}


def _stable_float(x: float) -> float:
    if math.isnan(x) or math.isinf(x):
        return 0.0
    return float(f"{x:.6f}")


def _scrub(obj: Any) -> Any:
    if isinstance(obj, dict):
        # Drop volatile keys and sort keys deterministically
        return {k: _scrub(v) for k, v in sorted(obj.items()) if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, float):
        return _stable_float(obj)
    return obj


def to_canonical_bytes(obj: Any) -> bytes:
    """Deterministically serialise any JSON‑like object to bytes."""
    scrubbed = _scrub(obj)
    return json.dumps(
        scrubbed, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
