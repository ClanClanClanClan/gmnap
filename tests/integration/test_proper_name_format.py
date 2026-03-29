import pytest

#!/usr/bin/env python3
"""Test with proper name format."""

import sys

sys.path.insert(0, "src")

from src.core.pipeline import GMNAPPipeline

pipeline = GMNAPPipeline({"database_path": ":memory:"})

# Test with proper "Family, Given" format
test_cases = [
    "Smithﬃ, John",  # ligature in family name
    "Smith, John№",  # numero sign in given name
    "Smith½, John",  # fraction in family name
    "SmithⅢ, John",  # Roman numeral in family name
    "Smith㎡, John",  # squared unit in family name
]

for original in test_cases:
    print(f"\nTesting: '{original}'")

    try:
        test_entry = {"CanonicalLatin": original}
        result = pipeline.process_entry(test_entry)
        print(f"  ✓ SUCCESS - {result['GlobalID'][:10]}...")
        print(f"    Final: '{result['CanonicalLatin']}'")
    except Exception as e:
        print(f"  ✗ FAILED - {e}")

        # Debug the specific steps
        try:
            # Step 1: Ingest stage
            ingested = pipeline._stage_ingest(test_entry.copy())
            print(f"    After ingest: '{ingested['CanonicalLatin']}'")

            # Step 2: Region detection
            region = pipeline._stage_detect_region(ingested)
            print(f"    Detected region: {region}")

            # Step 3: Regional processing
            if region in pipeline.v7_manager.list_regions():
                processed = pipeline._stage_region_hooks(ingested, region)
                print(f"    After regional: SUCCESS")
            else:
                print(f"    No processor for {region}")

        except Exception as debug_e:
            print(f"    Debug failed: {debug_e}")
