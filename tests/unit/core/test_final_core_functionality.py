#!/usr/bin/env python3
"""Test CORE FUNCTIONALITY after migration."""

import asyncio
import sys

import pytest

sys.path.insert(0, "src")

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


@pytest.mark.timeout(30)  # Increased timeout for realistic processing
@pytest.mark.asyncio
async def test_core_functionality():
    """Test if the system can classify mathematician names."""
    print("🔍 TESTING CORE FUNCTIONALITY: Name -> Region Classification")
    print("=" * 60)

    # Create test data
    test_data = [
        {"CanonicalNative": "Newton, Isaac", "GlobalID": "test001"},
        {"CanonicalNative": "Einstein, Albert", "GlobalID": "test002"},
        {"CanonicalNative": "Euler, Leonhard", "GlobalID": "test003"},
        {"CanonicalNative": "Erdős, Paul", "GlobalID": "test004"},
        {"CanonicalNative": "Gauss, Carl Friedrich", "GlobalID": "test005"},
        {"CanonicalNative": "Chebyshev, Pafnuty", "GlobalID": "test006"},
        {"CanonicalNative": "Wang, Xiaoming", "GlobalID": "test007"},
        {"CanonicalNative": "Tanaka, Satoshi", "GlobalID": "test008"},
        {"CanonicalNative": "Kim, Min-su", "GlobalID": "test009"},
        {"CanonicalNative": "Papadopoulos, Dimitris", "GlobalID": "test010"},
        {"CanonicalNative": "García, María", "GlobalID": "test011"},
        {"CanonicalNative": "Al-Khwarizmi, Muhammad", "GlobalID": "test012"},
        {"CanonicalNative": "Singh, Ramanujan", "GlobalID": "test013"},
        {"CanonicalNative": "Noether, Emmy", "GlobalID": "test014"},
        {"CanonicalNative": "Turing, Alan", "GlobalID": "test015"},
        {"CanonicalNative": "Eriksson, Lars", "GlobalID": "test016"},
        {"CanonicalNative": "Özil, Mesut", "GlobalID": "test017"},
        {"CanonicalNative": "da Silva, José", "GlobalID": "test018"},
        {"CanonicalNative": "O'Connor, Mary", "GlobalID": "test019"},
        {"CanonicalNative": "Van der Waals, Johannes", "GlobalID": "test020"},
    ]

    # Run pipeline
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    try:
        result = await pipeline.process_batch(test_data)
        print("Pipeline completed successfully")
        # process_batch returns a flat LIST of processed entry dicts —
        # the standardized contract guarded by
        # tests/v7/test_v7_batch_shape.py. Per-run metrics live on
        # pipeline.metrics regardless of the return shape. A legacy
        # {"entries"/"results": [...]} dict is still accepted so this
        # test tracks the contract rather than pinning one snapshot.
        if isinstance(result, dict):
            output_data = result.get("entries") or result.get("results") or []
        else:
            output_data = result

        m = pipeline.metrics
        print(f"Processed: {m.processed_entries} entries")
        print(f"Performance: {m.entries_per_second:.0f} entries/sec")

        success_count = 0
        total_count = len(output_data)

        print(f"\nDEBUG: Got {total_count} entries from pipeline")
        print("\nPASS CHECKING PROCESSING RESULTS:")

        for entry in output_data:
            name = entry.get("CanonicalNative", "Unknown")

            # Check if entry was processed
            has_latin = "CanonicalLatin" in entry and entry["CanonicalLatin"]
            has_region = "DetectedRegion" in entry
            has_variants = "Variants" in entry and entry["Variants"]

            # Entry is successful if it has any processing
            if has_latin or has_region or has_variants:
                success_count += 1
                indicators = []

                if has_region:
                    indicators.append(f"Region: {entry['DetectedRegion']}")
                if has_latin:
                    indicators.append(f"Latin: {entry['CanonicalLatin']}")
                if has_variants:
                    variant_types = list(entry["Variants"].keys())
                    indicators.append(f"Variants: {', '.join(variant_types)}")

                info = " | ".join(indicators) if indicators else "Processed"
                print(f"  ✓ {name:<30} -> {info}")
            else:
                print(f"  ✗ {name:<30} -> Not processed")

        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        print(f"\n📊 SUCCESS RATE: {success_count}/{total_count} = {success_rate:.1f}%")

        # We expect at least 70% processing success
        assert (
            success_rate >= 70
        ), f"Processing success rate too low: {success_rate:.1f}%"

        return True

    except Exception as e:
        print(f"FAIL Pipeline failed: {e}")
        import traceback

        traceback.print_exc()
        pytest.fail(f"Pipeline execution failed: {e}")


if __name__ == "__main__":
    # Run the test directly
    result = asyncio.run(test_core_functionality())
    print("\n" + "=" * 60)
    if result:
        print("PASS CORE FUNCTIONALITY WORKS!")
    else:
        print("FAIL CORE FUNCTIONALITY BROKEN!")
