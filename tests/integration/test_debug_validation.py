#!/usr/bin/env python3
"""Debug validation failures in regional processors."""

import pytest

pytest.skip("Test needs major refactoring", allow_module_level=True)

import sys

# sys.path.insert(0, 'src')

# from src.core.pipeline import GMNAPPipeline
# from src.v7_compat import v7_manager, load_working_processors

# Load processors
# if not v7_manager.list_regions():
#     load_working_processors()

# Test cases that are failing validation
test_cases = [
    {"name": "Čížek, Pavel", "expected_region": "B2"},
    {"name": "Wang, Ming", "native": "王明", "expected_region": "E1"},
    {"name": "Test, Name", "region": "B1"},
    {"name": "Test, Name", "territory": "CN"},
]

pipeline = GMNAPPipeline({"database_path": ":memory:"})

for test in test_cases:
    entry = {"CanonicalLatin": test["name"]}
    if "native" in test:
        entry["CanonicalNative"] = test["native"]
    if "region" in test:
        entry["RegionCode"] = test["region"]
    if "territory" in test:
        entry["TerritoryCode"] = test["territory"]

    print(f"\nTesting: {entry}")

    try:
        # First test region detection
        region_code = pipeline._stage_detect_region(entry.copy())
        print(f"  Detected region: {region_code}")

        # Then test processing
        result = pipeline.process_entry(entry)
        print(f"  ✓ Success - GlobalID: {result['GlobalID'][:20]}...")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

        # Try direct adapter test
        if region_code and region_code in v7_manager.list_regions():
            adapter = v7_manager.get_adapter(region_code)
            try:
                adapter_result = adapter.process_entry(entry)
                print(f"  ? Adapter succeeded but pipeline failed")
            except Exception as ae:
                print(f"  ✗ Adapter also failed: {ae}")
