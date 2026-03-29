import pytest

#!/usr/bin/env python3
"""Test idempotency of V7 pipeline."""

import asyncio
from src.core.pipeline_v7 import V7Pipeline, PipelineMode
import hashlib
import json


@pytest.mark.timeout(15)
def test_idempotency():
    """Test if pipeline produces identical results."""
    # Test idempotency
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    test_data = [{"CanonicalNative": "김민수", "GlobalID": "TEST-001"}]

    # Process twice
    result1 = asyncio.run(pipeline.process_batch(test_data.copy()))
    result2 = asyncio.run(pipeline.process_batch(test_data.copy()))

    # Remove non-deterministic fields
    def clean_result(result):
        entries = result.get("entries", [])
        for entry in entries:
            # Remove timing and random fields
            for field in [
                "_timing",
                "_cache_hit",
                "_processing_id",
                "_timestamp",
                "ProcessingTimestamp",
            ]:
                entry.pop(field, None)
        return entries

    clean1 = clean_result(result1)
    clean2 = clean_result(result2)

    # Compare
    json1 = json.dumps(clean1, sort_keys=True)
    json2 = json.dumps(clean2, sort_keys=True)

    hash1 = hashlib.sha256(json1.encode()).hexdigest()
    hash2 = hashlib.sha256(json2.encode()).hexdigest()

    print(f"Hash 1: {hash1}")
    print(f"Hash 2: {hash2}")
    print(f"Idempotent: {hash1 == hash2}")

    if hash1 != hash2:
        print("\nDifferences found:")
        # Find specific differences
        for i, (e1, e2) in enumerate(zip(clean1, clean2)):
            for key in set(e1.keys()) | set(e2.keys()):
                v1 = e1.get(key)
                v2 = e2.get(key)
                if v1 != v2:
                    print(f"  Entry {i}, field {key}: {repr(v1)} != {repr(v2)}")

    return hash1 == hash2


if __name__ == "__main__":
    test_idempotency()
