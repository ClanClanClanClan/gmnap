#!/usr/bin/env python3
import hashlib
import json
import sys

VOLATILE_KEYS = {"ProcessedAt", "ProcessingLatencyMs", "_debug", "_trace_id", "_meta"}


def canonical_bytes(batch):
    def scrub(e):
        return {k: v for k, v in e.items() if k not in VOLATILE_KEYS}

    ordered = sorted(
        [scrub(dict(e)) for e in batch],
        key=lambda e: (e.get("GlobalID", ""), e.get("Source", "")),
    )
    return json.dumps(
        ordered, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


if __name__ == "__main__":
    data_path = sys.argv[1]
    with open(data_path, "r", encoding="utf-8") as f:
        batch = json.load(f)
    b = canonical_bytes(batch)
    print(hashlib.sha256(b).hexdigest())
