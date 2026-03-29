#!/usr/bin/env python3
"""Test all systematic fixes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
from src.core.pipeline_v7 import V7Pipeline, PipelineMode


async def test_fixes():
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    test_names = [
        {"CanonicalNative": "김민수", "GlobalID": "FIX-001"},
        {"CanonicalNative": "이순신", "GlobalID": "FIX-002"},
        {"CanonicalNative": "문재인", "GlobalID": "FIX-003"},
    ]

    result = await pipeline.process_batch(test_names)

    print("Korean Processing Fixed:")
    print("-" * 50)
    for entry in result["entries"]:
        native = entry.get("CanonicalNative", "")
        latin = entry.get("CanonicalLatin", "")
        print(f"{native:10} → {latin:20}")

    print(
        "\nQuality Gates:", "PASSED" if result["quality_gates"]["passed"] else "FAILED"
    )
    print("Metrics:")
    print(f"  Processed: {result['metrics']['processed_entries']}")
    print(f"  Duplicates: {result['metrics'].get('duplicate_global_ids', 0)}")
    print(f"  Performance: {result['metrics']['entries_per_second']:.0f} entries/sec")


if __name__ == "__main__":
    asyncio.run(test_fixes())
