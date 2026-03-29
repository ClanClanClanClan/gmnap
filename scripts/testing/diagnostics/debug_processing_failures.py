#!/usr/bin/env python3
"""
Debug what's causing 0% success rate in pipeline processing.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ops.scale_guard_service import ScaleGuardService, ScaleConfig
from src.core.pipeline_v7 import V7Pipeline


async def debug_small_batch():
    """Test with just 5 entries to see exactly what goes wrong."""

    # Create test entries
    entries = [
        {
            "ID": f"test_{i:04d}",
            "CanonicalNative": "John Smith",
            "Region": "a1_anglo_sphere",
            "SourceDatabase": "test",
        }
        for i in range(5)
    ]

    print("🔍 Testing 5 entries to debug processing failures...")
    print(f"Input entries: {entries}")

    # Test with scale guard service
    svc = ScaleGuardService(lambda: V7Pipeline(), ScaleConfig())
    await svc.warmup()

    try:
        results = await svc.process(entries)
        print(f"\n📊 Results received: {len(results)} entries")

        for i, result in enumerate(results):
            print(f"\nEntry {i+1}:")
            print(f"  Input:  {entries[i]}")
            print(f"  Output: {result}")
            print(f"  Type:   {type(result)}")

            if isinstance(result, dict):
                status = result.get("Status") or result.get("status")
                print(f"  Status: {status}")

                if status == "failed" or status == "processing_error":
                    error = result.get("error") or result.get("Error")
                    print(f"  Error:  {error}")
            else:
                print(f"  Raw:    {result}")

    except Exception as e:
        print(f"❌ Exception during processing: {e}")
        import traceback

        traceback.print_exc()

    await svc.aclose()


async def test_direct_pipeline():
    """Test direct pipeline without scale guard service."""

    print("\n🔍 Testing direct V7Pipeline without scale guard...")

    entries = [
        {
            "ID": "test_0001",
            "CanonicalNative": "John Smith",
            "Region": "a1_anglo_sphere",
            "SourceDatabase": "test",
        }
    ]

    pipeline = V7Pipeline(enable_quality_gates=False)

    try:
        results = await pipeline.process_batch(entries)
        print(f"Direct pipeline results: {results}")

        for result in results:
            print(f"  Result type: {type(result)}")
            print(f"  Result: {result}")

    except Exception as e:
        print(f"❌ Direct pipeline error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_small_batch())
    asyncio.run(test_direct_pipeline())
