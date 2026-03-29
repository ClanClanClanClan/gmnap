#!/usr/bin/env python3
"""Debug quality gates issue"""

import asyncio
import json
from src.core.pipeline_v7 import V7Pipeline, PipelineMode


async def test_quality_gates():
    """Test quality gates functionality"""
    print("Testing quality gates...")

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    # Test duplicate detection
    entries = [
        {"CanonicalNative": "Same Name", "GlobalID": "DUP-001"},
        {"CanonicalNative": "Same Name", "GlobalID": "DUP-001"},  # Duplicate ID
    ]

    result = await pipeline.process_batch(entries)

    print("\n=== RESULT STRUCTURE ===")
    print(json.dumps(result, indent=2, default=str))

    print("\n=== CHECKING FOR EXPECTED KEYS ===")

    # Check metrics
    if "metrics" in result:
        print(f"✅ 'metrics' found")
        dup_count = result["metrics"].get("duplicate_global_ids", 0)
        print(f"  duplicate_global_ids = {dup_count}")
        if dup_count == 1:
            print(f"  ✅ Correct duplicate count (expected 1)")
        else:
            print(f"  ❌ Wrong duplicate count (expected 1, got {dup_count})")
    else:
        print("❌ 'metrics' not found")

    # Check quality gates
    if "quality_gates" in result:
        print(f"✅ 'quality_gates' found")
        qg_results = result["quality_gates"].get("results", {})
        print(f"  results keys: {list(qg_results.keys())}")

        if "duplicate_global_ids" in qg_results:
            print(f"  ✅ 'duplicate_global_ids' gate found")
        else:
            print(f"  ❌ 'duplicate_global_ids' gate not found")

        if "performance" in qg_results:
            print(f"  ✅ 'performance' gate found")
        else:
            print(f"  ❌ 'performance' gate not found")
    else:
        print("❌ 'quality_gates' not found")

    return result


if __name__ == "__main__":
    asyncio.run(test_quality_gates())
