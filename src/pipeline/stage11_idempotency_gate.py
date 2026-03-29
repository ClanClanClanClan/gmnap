from __future__ import annotations

import json
from typing import Callable, Dict, List, Tuple

VOLATILE_KEYS = {"ProcessedAt", "ProcessingLatencyMs", "_debug", "_trace_id", "_meta"}


def _canonical_bytes(batch: List[Dict]) -> bytes:
    def scrub(e: Dict) -> Dict:
        return {k: v for k, v in e.items() if k not in VOLATILE_KEYS}

    ordered = sorted(
        [scrub(dict(e)) for e in batch],
        key=lambda e: (e.get("GlobalID", ""), e.get("Source", "")),
    )
    return json.dumps(
        ordered, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def enforce_idempotency_gate(
    process_fn: Callable[[List[Dict]], List[Dict]], batch: List[Dict]
) -> Tuple[List[Dict], bytes]:
    first = process_fn(batch)
    second = process_fn(batch)
    a = _canonical_bytes(first)
    b = _canonical_bytes(second)
    if a != b:
        # find first byte diff for diagnostics
        idx = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
        where = f" at byte {idx}" if idx is not None else ""
        raise ValueError(f"Idempotency violation: outputs differ{where}")
    return first, a
