#!/usr/bin/env python3
"""Debug script to test pipeline processing."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("."))

from src.core.pipeline_v7 import V7Pipeline, PipelineMode


async def debug_pipeline():
    """Debug pipeline processing."""
    print("🔍 DEBUGGING PIPELINE PROCESSING")
    print("=" * 50)

    # Simple test data
    test_data = [
        {"CanonicalNative": "Newton, Isaac", "GlobalID": "test001"},
        {"CanonicalNative": "김정은", "GlobalID": "test002"},
        {"CanonicalNative": "Einstein, Albert", "GlobalID": "test003"},
    ]

    # Create pipeline
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    try:
        print("Processing batch...")
        result = await pipeline.process_batch(test_data)

        print(f"\nResult keys: {list(result.keys())}")
        print(f"Processed entries: {result['metrics']['processed_entries']}")

        entries = result.get("entries", [])
        print(f"\nOutput entries count: {len(entries)}")

        for i, entry in enumerate(entries):
            print(f"\nEntry {i+1}:")
            print(f"  Input: {entry.get('CanonicalNative', 'N/A')}")
            print(f"  CanonicalLatin: {entry.get('CanonicalLatin', 'NOT SET')}")
            print(f"  DetectedRegion: {entry.get('DetectedRegion', 'NOT SET')}")
            print(f"  Variants: {entry.get('Variants', 'NOT SET')}")
            print(f"  All keys: {list(entry.keys())}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_pipeline())
