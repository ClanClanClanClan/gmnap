#!/usr/bin/env python3
"""Debug what the pipeline is actually returning."""

import asyncio
import json
from src.core.pipeline_v7 import V7Pipeline


async def main():
    # Create small test batch
    test_data = [
        {"id": "test_001", "CanonicalNative": "김정은"},
        {"id": "test_002", "CanonicalNative": "John Smith"},
    ]

    print("Testing pipeline output...")
    print(f"Input data: {json.dumps(test_data, indent=2, ensure_ascii=False)}")

    pipeline = V7Pipeline()
    results = await pipeline.process_batch(test_data)

    print(f"\nResults type: {type(results)}")
    print(f"Results length: {len(results) if hasattr(results, '__len__') else 'N/A'}")

    if isinstance(results, dict):
        print(f"\nResults keys: {list(results.keys())}")
        print(f"\nFull results: {json.dumps(results, indent=2, ensure_ascii=False)}")
    elif isinstance(results, list) and results:
        print(f"\nFirst result type: {type(results[0])}")
        print(f"First result: {results[0]}")

        if isinstance(results[0], dict):
            print(f"\nFirst result keys: {list(results[0].keys())}")


if __name__ == "__main__":
    asyncio.run(main())
