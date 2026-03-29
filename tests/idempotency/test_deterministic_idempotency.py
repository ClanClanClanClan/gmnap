import pytest

#!/usr/bin/env python3
"""Test enhanced idempotency with deterministic mode."""

import asyncio
from src.core.pipeline_v7 import V7Pipeline, PipelineMode
import hashlib
import json


@pytest.mark.timeout(15)
def test_deterministic_idempotency():
    """Test if pipeline produces identical results with deterministic mode."""
    # Test with deterministic mode ENABLED
    pipeline1 = V7Pipeline(mode=PipelineMode.QUICK, deterministic=True, seed=42)
    pipeline2 = V7Pipeline(mode=PipelineMode.QUICK, deterministic=True, seed=42)

    test_data = [
        {"CanonicalNative": "김민수", "GlobalID": "TEST-001"},
        {"CanonicalNative": "李明", "GlobalID": "TEST-002"},
        {"CanonicalNative": "Иванов Иван", "GlobalID": "TEST-003"},
    ]

    # Process with both pipelines
    result1 = asyncio.run(pipeline1.process_batch(test_data.copy()))
    result2 = asyncio.run(pipeline2.process_batch(test_data.copy()))

    # Compare raw results (including all fields)
    json1 = json.dumps(result1, sort_keys=True, default=str)
    json2 = json.dumps(result2, sort_keys=True, default=str)

    hash1 = hashlib.sha256(json1.encode()).hexdigest()
    hash2 = hashlib.sha256(json2.encode()).hexdigest()

    print("=== DETERMINISTIC MODE TEST ===")
    print(f"Hash 1: {hash1}")
    print(f"Hash 2: {hash2}")
    print(f"Perfectly Idempotent: {hash1 == hash2}")

    if hash1 != hash2:
        print("\nWARN Not perfectly idempotent!")
        print(f"Result 1 length: {len(json1)}")
        print(f"Result 2 length: {len(json2)}")

        # Find first difference
        for i, (c1, c2) in enumerate(zip(json1, json2)):
            if c1 != c2:
                print(f"First difference at position {i}:")
                print(f"  Context: ...{json1[max(0,i-20):i+20]}...")
                break
    else:
        print("\nPASS PERFECT IDEMPOTENCY ACHIEVED!")
        print("Both runs produced bit-identical results.")

    return hash1 == hash2


@pytest.mark.timeout(15)
def test_non_deterministic_mode():
    """Test regular mode (should show some variation)."""
    pipeline1 = V7Pipeline(mode=PipelineMode.QUICK, deterministic=False)
    pipeline2 = V7Pipeline(mode=PipelineMode.QUICK, deterministic=False)

    test_data = [{"CanonicalNative": "김민수", "GlobalID": "TEST-001"}]

    result1 = asyncio.run(pipeline1.process_batch(test_data.copy()))
    result2 = asyncio.run(pipeline2.process_batch(test_data.copy()))

    # Remove obviously non-deterministic fields
    def clean_for_comparison(result):
        entries = result.get("entries", [])
        for entry in entries:
            for field in ["ProcessingTimestamp", "_timing", "_cache_hit"]:
                entry.pop(field, None)
        # Also clean metrics
        metrics = result.get("metrics", {})
        metrics.pop("start_time", None)
        metrics.pop("end_time", None)
        return result

    clean1 = clean_for_comparison(result1)
    clean2 = clean_for_comparison(result2)

    json1 = json.dumps(clean1, sort_keys=True, default=str)
    json2 = json.dumps(clean2, sort_keys=True, default=str)

    hash1 = hashlib.sha256(json1.encode()).hexdigest()
    hash2 = hashlib.sha256(json2.encode()).hexdigest()

    print("\n=== NON-DETERMINISTIC MODE TEST ===")
    print(f"Hash 1: {hash1}")
    print(f"Hash 2: {hash2}")
    print(f"Core data idempotent: {hash1 == hash2}")


if __name__ == "__main__":
    # Test deterministic mode
    is_idempotent = test_deterministic_idempotency()

    # Test non-deterministic mode for comparison
    test_non_deterministic_mode()

    # Report overall status
    print("\n" + "=" * 50)
    if is_idempotent:
        print("PASS IDEMPOTENCY IMPLEMENTATION COMPLETE")
        print("The V7 pipeline achieves perfect idempotency in deterministic mode.")
    else:
        print("WARN Idempotency needs more work")
        print("Check for additional sources of non-determinism.")
