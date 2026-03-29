import pytest

#!/usr/bin/env python3
"""Minimal test - just the idempotency function"""
import json
import hashlib

VOLATILE_KEYS = {"ProcessedAt", "ProcessingLatencyMs", "_debug", "_trace_id", "_meta"}


def _canonical_bytes(batch):
    def scrub(e):
        return {k: v for k, v in e.items() if k not in VOLATILE_KEYS}

    ordered = sorted(
        [scrub(dict(e)) for e in batch], key=lambda e: (e.get("GlobalID", ""), e.get("Source", ""))
    )
    return json.dumps(ordered, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


# Test it
test_batch = [{"GlobalID": "test-001", "Name": "Test"}]
canonical = _canonical_bytes(test_batch)
print(f"Success! Canonical form: {len(canonical)} bytes")
print(f"Hash: {hashlib.sha256(canonical).hexdigest()[:32]}...")
