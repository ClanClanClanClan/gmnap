from __future__ import annotations
from typing import List, Dict, Any
import hashlib
from .canonical_json import to_canonical_bytes


def canonical_batch_bytes(entries: List[Dict[str, Any]]) -> bytes:
    """Order‑insensitive canonical bytes for a batch (sort by GlobalID, Source)."""
    ordered = sorted(entries, key=lambda e: (e.get("GlobalID", ""), e.get("Source", "")))
    return to_canonical_bytes(ordered)


def batch_hash(entries: List[Dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_batch_bytes(entries)).hexdigest()


def assert_identical(output_a: List[Dict[str, Any]], output_b: List[Dict[str, Any]]) -> None:
    if batch_hash(output_a) != batch_hash(output_b):
        raise AssertionError("Idempotency violated: canonical batch hashes differ")


class IdempotencyChecker:
    """Stub for IdempotencyChecker"""

    def __init__(self, *args, **kwargs):
        pass


def validate_v7_idempotency_compliance(entry):
    """Validate V7 idempotency compliance (stub)"""
    # TODO: Implement actual validation
    return True
