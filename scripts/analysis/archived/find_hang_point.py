#!/usr/bin/env python3

import asyncio
import time
from src.core.pipeline_v7 import V7Pipeline, PipelineMode


async def test_size(size):
    print(f"\nTesting {size} entries...")
    p = V7Pipeline(mode=PipelineMode.QUICK)
    p.quality_gates = None

    entries = [{"CanonicalNative": f"N{i}", "GlobalID": f"ID{i}"} for i in range(size)]

    start = time.time()
    try:
        # Set a timeout for the operation
        result = await asyncio.wait_for(p.process_batch(entries), timeout=10.0)
        duration = time.time() - start
        print(f"  ✅ Success in {duration:.2f}s ({size/duration:.0f} entries/sec)")
        return True
    except asyncio.TimeoutError:
        print(f"  ❌ TIMEOUT after 10 seconds!")
        return False
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


async def main():
    print("Finding hang point...")

    # Test progressively larger sizes
    sizes = [10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000]

    for size in sizes:
        success = await test_size(size)
        if not success:
            print(f"\nPipeline hangs at {size} entries or above")
            break


asyncio.run(main())
