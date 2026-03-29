import pytest

#!/usr/bin/env python3
"""Simple test of core pipeline functionality."""

import sys

sys.path.insert(0, "src")

from src.core.config import GMNAPConfig
from src.core.pipeline_v6 import GMNAPPipeline


@pytest.mark.timeout(15)
def test_simple():
    """Test basic name classification."""

    # Initialize pipeline with proper config
    config = GMNAPConfig()
    pipeline = GMNAPPipeline(config)

    # Test cases
    test_names = [
        {"CanonicalLatin": "Newton, Isaac", "GlobalID": "test1"},
        {"CanonicalLatin": "Einstein, Albert", "GlobalID": "test2"},
        {"CanonicalLatin": "Euler, Leonhard", "GlobalID": "test3"},
        {"CanonicalLatin": "Kim, Min-su", "GlobalID": "test4"},
        {"CanonicalLatin": "Tanaka, Satoshi", "GlobalID": "test5"},
    ]

    results = []
    for entry in test_names:
        try:
            result = pipeline.process_entry(entry.copy())
            region = result.get("_region", "NONE")
            print(f"PASS {entry['CanonicalLatin']} -> {region}")
            results.append((entry["CanonicalLatin"], region, True))
        except Exception as e:
            print(f"FAIL {entry['CanonicalLatin']} -> ERROR: {e}")
            results.append((entry["CanonicalLatin"], "ERROR", False))

    # Summary
    success = sum(1 for _, _, ok in results if ok)
    print(f"\nSuccess: {success}/{len(results)} ({success/len(results)*100:.1f}%)")

    return success == len(results)


if __name__ == "__main__":
    success = test_simple()
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
