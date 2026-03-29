#!/usr/bin/env python3
"""
FRESH BATCH STATISTICS TEST
Complete clean test from 10 to 1M entries with perfect documentation.
All previous test results have been erased.
"""

import time
import json
import sys
import os
import asyncio
from datetime import datetime
import psutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.pipeline_v7 import V7Pipeline


def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process()
    return round(process.memory_info().rss / 1024 / 1024, 1)


def generate_test_entries(count: int):
    """Generate safe test entries."""
    return [
        {
            "ID": f"fresh_test_{i:08d}",
            "CanonicalNative": "John Smith",
            "Region": "a1_anglo_sphere",
            "SourceDatabase": "fresh_test",
            "Year": 2024,
        }
        for i in range(count)
    ]


async def test_batch_size(size: int):
    """Test a single batch size and return complete statistics."""
    print(f"Testing {size:>8,} entries... ", end="", flush=True)

    # Generate test data
    entries = generate_test_entries(size)

    # Get initial memory
    memory_start = get_memory_usage()

    # Initialize pipeline
    pipeline = V7Pipeline()

    try:
        # Run the test
        start_time = time.time()
        results = await pipeline.process_batch(entries)
        end_time = time.time()

        # Calculate metrics
        duration = end_time - start_time
        entries_per_sec = size / duration if duration > 0 else 0
        time_for_1m_min = (
            (1_000_000 / entries_per_sec / 60) if entries_per_sec > 0 else float("inf")
        )

        # Count successes
        successful = len([r for r in results if r.get("Status") != "failed"])
        success_rate = (successful / size) * 100 if size > 0 else 0

        # Get final memory
        memory_end = get_memory_usage()

        # Create result record
        result = {
            "batch_size": size,
            "duration_seconds": round(duration, 3),
            "entries_per_second": round(entries_per_sec, 1),
            "time_for_1m_minutes": round(time_for_1m_min, 1),
            "successful_entries": successful,
            "total_entries": size,
            "success_rate_percent": round(success_rate, 1),
            "memory_start_mb": memory_start,
            "memory_end_mb": memory_end,
            "memory_delta_mb": round(memory_end - memory_start, 1),
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }

        # Performance status
        if time_for_1m_min <= 35:
            status_emoji = "🚀"
            status_text = "EXCELLENT"
        elif time_for_1m_min <= 60:
            status_emoji = "✅"
            status_text = "GOOD"
        elif time_for_1m_min <= 120:
            status_emoji = "⚠️"
            status_text = "ACCEPTABLE"
        else:
            status_emoji = "❌"
            status_text = "POOR"

        print(
            f"{status_emoji} {entries_per_sec:>6.0f} e/s ({time_for_1m_min:>4.1f}min for 1M) - {status_text}"
        )

        return result

    except Exception as e:
        print(f"❌ ERROR: {str(e)[:50]}")
        return {
            "batch_size": size,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "status": "failed",
        }

    finally:
        del pipeline


async def main():
    """Run complete fresh batch test from 10 to 1M entries."""
    print("🚀 FRESH BATCH STATISTICS TEST")
    print("📋 All previous test results have been erased")
    print("🎯 Testing batches from 10 to 1,000,000 entries")
    print("=" * 60)

    # Define all batch sizes to test
    batch_sizes = [
        # Very small batches
        10,
        25,
        50,
        75,
        100,
        # Small batches
        250,
        500,
        750,
        1000,
        # Medium batches
        2500,
        5000,
        7500,
        10000,
        # Large batches
        25000,
        50000,
        75000,
        100000,
        # Very large batches
        250000,
        500000,
        750000,
        1000000,
    ]

    results = []
    test_start_time = datetime.now()

    print(f"📅 Test started: {test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🧪 Total batch sizes to test: {len(batch_sizes)}")
    print()

    # Run tests for each batch size
    for i, size in enumerate(batch_sizes, 1):
        print(f"[{i:>2}/{len(batch_sizes)}] ", end="")

        result = await test_batch_size(size)
        results.append(result)

        # Small delay between tests
        await asyncio.sleep(0.5)

    test_end_time = datetime.now()
    total_duration = test_end_time - test_start_time

    print()
    print("=" * 60)
    print("📊 FRESH BATCH STATISTICS COMPLETE")
    print("=" * 60)

    # Analyze results
    successful_tests = [r for r in results if r["status"] == "success"]
    failed_tests = [r for r in results if r["status"] == "failed"]

    print(f"⏱️  Total test duration: {total_duration.total_seconds():.1f} seconds")
    print(f"✅ Successful tests: {len(successful_tests)}/{len(results)}")
    print(f"❌ Failed tests: {len(failed_tests)}")

    if successful_tests:
        # Find best performance
        best = max(successful_tests, key=lambda x: x["entries_per_second"])

        print(f"\n🏆 BEST PERFORMANCE:")
        print(f"   Batch Size: {best['batch_size']:,} entries")
        print(f"   Speed: {best['entries_per_second']:,.0f} entries/sec")
        print(f"   Time for 1M: {best['time_for_1m_minutes']:.1f} minutes")
        print(f"   Success Rate: {best['success_rate_percent']:.1f}%")

        # Performance categories
        excellent = [r for r in successful_tests if r["time_for_1m_minutes"] <= 35]
        good = [r for r in successful_tests if 35 < r["time_for_1m_minutes"] <= 60]
        acceptable = [
            r for r in successful_tests if 60 < r["time_for_1m_minutes"] <= 120
        ]
        poor = [r for r in successful_tests if r["time_for_1m_minutes"] > 120]

        print(f"\n📈 PERFORMANCE CATEGORIES:")
        print(f"   🚀 Excellent (≤35 min/1M): {len(excellent)} batches")
        print(f"   ✅ Good (35-60 min/1M): {len(good)} batches")
        print(f"   ⚠️  Acceptable (60-120 min/1M): {len(acceptable)} batches")
        print(f"   ❌ Poor (>120 min/1M): {len(poor)} batches")

        # Detailed results table
        print(f"\n📋 COMPLETE PERFORMANCE TABLE:")
        print("Batch Size | Speed (e/s) | 1M Time (min) | Success Rate | Memory (MB)")
        print("-" * 75)

        for result in successful_tests:
            size = result["batch_size"]
            speed = result["entries_per_second"]
            time_1m = result["time_for_1m_minutes"]
            success = result["success_rate_percent"]
            memory = result["memory_delta_mb"]

            print(
                f"{size:>10,} | {speed:>11.0f} | {time_1m:>12.1f} | {success:>10.1f}% | {memory:>9.1f}"
            )

    # Create comprehensive statistics document
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    final_statistics = {
        "test_metadata": {
            "test_name": "Fresh Batch Statistics Test",
            "description": "Complete clean test from 10 to 1M entries",
            "start_time": test_start_time.isoformat(),
            "end_time": test_end_time.isoformat(),
            "total_duration_seconds": total_duration.total_seconds(),
            "batch_sizes_tested": len(batch_sizes),
            "successful_tests": len(successful_tests),
            "failed_tests": len(failed_tests),
            "timestamp": timestamp,
        },
        "performance_summary": {
            "best_performance": best if successful_tests else None,
            "performance_categories": {
                "excellent_batches": len(excellent) if successful_tests else 0,
                "good_batches": len(good) if successful_tests else 0,
                "acceptable_batches": len(acceptable) if successful_tests else 0,
                "poor_batches": len(poor) if successful_tests else 0,
            },
        },
        "detailed_results": results,
    }

    # Save results
    results_filename = f"FRESH_BATCH_STATISTICS_DATA_{timestamp}.json"

    with open(results_filename, "w") as f:
        json.dump(final_statistics, f, indent=2)

    print(f"\n📄 Complete statistics saved to: {results_filename}")

    # Production recommendations
    if successful_tests:
        production_ready = [
            r
            for r in successful_tests
            if r["time_for_1m_minutes"] <= 35 and r["success_rate_percent"] >= 95
        ]

        if production_ready:
            optimal = max(production_ready, key=lambda x: x["entries_per_second"])
            print(f"\n🎯 PRODUCTION RECOMMENDATION:")
            print(f"   Optimal Batch Size: {optimal['batch_size']:,} entries")
            print(
                f"   Expected Performance: {optimal['entries_per_second']:,.0f} entries/sec"
            )
            print(
                f"   1M Processing Time: {optimal['time_for_1m_minutes']:.1f} minutes"
            )
            print(f"   ✅ READY FOR PRODUCTION")
        else:
            print(
                f"\n⚠️  PRODUCTION CAUTION: No batches meet production criteria (≤35 min + ≥95% success)"
            )

    print(f"\n🏁 FRESH BATCH STATISTICS TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
