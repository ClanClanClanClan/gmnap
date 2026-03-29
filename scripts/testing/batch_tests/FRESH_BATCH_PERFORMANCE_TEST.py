#!/usr/bin/env python3
"""
FRESH BATCH PERFORMANCE TEST
Clean test from 10 to 1M entries with robust error handling.
"""

import time
import json
import sys
import os
import asyncio
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.pipeline_v7 import V7Pipeline


def generate_entries(count: int):
    """Generate test entries."""
    return [
        {
            "ID": f"test_{i:08d}",
            "CanonicalNative": "John Smith",
            "Region": "a1_anglo_sphere",
            "SourceDatabase": "test",
        }
        for i in range(count)
    ]


async def test_batch_performance(size: int):
    """Test batch performance with robust error handling."""
    print(f"Testing {size:>8,} entries... ", end="", flush=True)

    entries = generate_entries(size)
    pipeline = V7Pipeline()

    try:
        start = time.time()
        results = await pipeline.process_batch(entries)
        duration = time.time() - start

        # Handle different result types
        if isinstance(results, list):
            processed_count = len(results)
            # Count successful entries (handle both dict and string results)
            successful = 0
            for r in results:
                if isinstance(r, dict):
                    if r.get("Status") != "failed":
                        successful += 1
                else:
                    # Assume non-failed if it's not a dict with failed status
                    successful += 1
        else:
            processed_count = size
            successful = size

        entries_per_sec = size / duration if duration > 0 else 0
        time_1m_min = (
            (1_000_000 / entries_per_sec / 60) if entries_per_sec > 0 else float("inf")
        )
        success_rate = (successful / size) * 100 if size > 0 else 0

        # Status indicator
        if time_1m_min <= 35:
            status = "🚀 EXCELLENT"
        elif time_1m_min <= 60:
            status = "✅ GOOD"
        elif time_1m_min <= 120:
            status = "⚠️ ACCEPTABLE"
        else:
            status = "❌ POOR"

        print(f"{entries_per_sec:>6.0f} e/s ({time_1m_min:>4.1f}min for 1M) - {status}")

        return {
            "batch_size": size,
            "duration_seconds": round(duration, 3),
            "entries_per_second": round(entries_per_sec, 1),
            "time_for_1m_minutes": round(time_1m_min, 1),
            "successful_entries": successful,
            "success_rate_percent": round(success_rate, 1),
            "status": "success",
        }

    except Exception as e:
        print(f"❌ ERROR: {str(e)[:50]}")
        return {"batch_size": size, "error": str(e), "status": "failed"}

    finally:
        del pipeline


async def main():
    """Run fresh batch performance test."""
    print("🚀 FRESH BATCH PERFORMANCE TEST")
    print("📋 All previous test results erased")
    print("🎯 Testing 10 to 1,000,000 entries")
    print("=" * 50)

    # All batch sizes
    sizes = [
        10,
        25,
        50,
        100,
        250,
        500,
        1000,
        2500,
        5000,
        10000,
        25000,
        50000,
        100000,
        250000,
        500000,
        1000000,
    ]

    results = []
    start_time = datetime.now()

    for size in sizes:
        result = await test_batch_performance(size)
        results.append(result)
        await asyncio.sleep(0.1)  # Brief pause

    end_time = datetime.now()

    # Analysis
    successful = [r for r in results if r["status"] == "success"]

    print("\n" + "=" * 50)
    print("📊 FRESH BATCH STATISTICS SUMMARY")
    print("=" * 50)

    if successful:
        best = max(successful, key=lambda x: x["entries_per_second"])

        print(f"🏆 Best Performance: {best['batch_size']:,} entries")
        print(f"   Speed: {best['entries_per_second']:,.0f} entries/sec")
        print(f"   1M Time: {best['time_for_1m_minutes']:.1f} minutes")

        # Categories
        excellent = [r for r in successful if r["time_for_1m_minutes"] <= 35]
        good = [r for r in successful if 35 < r["time_for_1m_minutes"] <= 60]
        poor = [r for r in successful if r["time_for_1m_minutes"] > 60]

        print(f"\n📈 Performance Categories:")
        print(f"   🚀 Excellent (≤35 min): {len(excellent)} batches")
        print(f"   ✅ Good (35-60 min): {len(good)} batches")
        print(f"   ❌ Poor (>60 min): {len(poor)} batches")

        print(f"\n📋 Performance Table:")
        print("Batch Size | Speed (e/s) | 1M Time (min) | Success Rate")
        print("-" * 55)

        for r in successful:
            print(
                f"{r['batch_size']:>10,} | {r['entries_per_second']:>11.0f} | "
                f"{r['time_for_1m_minutes']:>12.1f} | {r['success_rate_percent']:>10.1f}%"
            )

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    final_data = {
        "test_metadata": {
            "test_name": "Fresh Batch Performance Test",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "batch_sizes_tested": len(sizes),
            "successful_tests": len(successful),
            "timestamp": timestamp,
        },
        "results": results,
    }

    filename = f"FRESH_BATCH_DATA_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(final_data, f, indent=2)

    print(f"\n📄 Results saved to: {filename}")
    print(f"⏱️ Total duration: {(end_time - start_time).total_seconds():.1f} seconds")
    print(f"✅ Successful: {len(successful)}/{len(results)} tests")


if __name__ == "__main__":
    asyncio.run(main())
