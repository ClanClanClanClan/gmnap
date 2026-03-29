#!/usr/bin/env python3
"""Fresh batch test from 10 to 1M entries - current results only."""

import time
import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.core.pipeline_v7 import V7Pipeline


async def test_batch(size):
    """Test a single batch size and return actual results."""
    entries = [
        {
            "ID": f"fresh_test_{i:08d}",
            "CanonicalNative": "Test Name",
            "Region": "a1_anglo_sphere",
        }
        for i in range(size)
    ]

    pipeline = V7Pipeline()
    start = time.time()

    try:
        results = await pipeline.process_batch(entries)
        end = time.time()

        duration = end - start
        eps = size / duration if duration > 0 else 0
        time_1m = (1_000_000 / eps / 60) if eps > 0 else float("inf")

        return {
            "size": size,
            "duration": round(duration, 2),
            "entries_per_sec": round(eps, 1),
            "time_for_1m_min": round(time_1m, 1),
            "status": "success",
        }
    except Exception as e:
        return {"size": size, "error": str(e)[:100], "status": "failed"}
    finally:
        del pipeline


async def main():
    """Run fresh tests from 10 to 1M."""
    print("🔄 Fresh Batch Test - 10 to 1M entries")
    print("=" * 50)

    sizes = [10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000]

    for size in sizes:
        print(f"Testing {size:>7,} entries... ", end="", flush=True)

        result = await test_batch(size)

        if result["status"] == "success":
            print(
                f"✅ {result['entries_per_sec']:>6.0f} e/s ({result['time_for_1m_min']:>4.1f}min)"
            )
        else:
            print(f"❌ {result['error']}")

        # Save result immediately
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"fresh_result_{size}_{timestamp}.txt", "w") as f:
            f.write(str(result))


if __name__ == "__main__":
    asyncio.run(main())
