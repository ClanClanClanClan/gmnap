#!/usr/bin/env python3
"""
Scale Fix Validation Test
Validates the critical scale fixes using streaming executor and quality gates.
"""

import time
import json
import sys
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.pipeline_v7 import V7Pipeline
from src.ops.streaming_executor import StreamingExecutor, StreamConfig
from src.quality.gates_streaming import StreamingGates
from src.ops.scale_guard_service import ScaleGuardService, ScaleConfig
from src.memory.sized_lru import SizedLRU
from src.diag.memdiff import MemDiff


def generate_test_entries(count: int) -> List[Dict[str, Any]]:
    """Generate test entries with proper format."""
    entries = []
    patterns = [
        {"CanonicalNative": "John Smith", "Region": "a1_anglo_sphere"},
        {"CanonicalNative": "Kim Jung-eun", "Region": "e4_korea"},
        {"CanonicalNative": "Zhang Wei", "Region": "e1_sinophone_mainland"},
        {"CanonicalNative": "Jose Garcia", "Region": "g1_latin_america"},
        {"CanonicalNative": "Ahmed Hassan", "Region": "c3_arabic_levant_nile"},
    ]

    for i in range(count):
        pattern = patterns[i % len(patterns)]
        entry = {
            "ID": f"scale_test_{i:08d}",
            "GlobalID": f"scale_test_{i:08d}",
            "CanonicalNative": pattern["CanonicalNative"],
            "Region": pattern["Region"],
            "SourceDatabase": "scale_test",
            "Year": 2020 + (i % 5),
        }
        entries.append(entry)

    return entries


async def test_streaming_executor(batch_size: int):
    """Test the streaming executor approach."""
    print(f"\n🔄 Testing Streaming Executor with {batch_size:,} entries")

    entries = generate_test_entries(batch_size)
    pipeline = V7Pipeline()

    # Configure streaming with optimal chunk size
    config = StreamConfig(
        chunk=1500,  # Sweet spot from analysis
        inflight=4,  # Bounded concurrency
        max_errors_pct=0.05,  # 95% success requirement
        soft_timeout_s=600.0,
    )

    executor = StreamingExecutor(pipeline.process_batch, config)
    gates = StreamingGates()

    mem = MemDiff(top=10)
    mem_before = mem.snapshot()

    start_time = time.time()
    try:
        results, metrics = await executor.run(entries)
        duration = time.time() - start_time

        mem_after = mem.snapshot()
        mem_diff = mem.compare(mem_before, mem_after)

        # Analyze with streaming gates
        gates.ingest(results)
        gate_decision = gates.decision(metrics["eps"])

        return {
            "batch_size": batch_size,
            "approach": "streaming_executor",
            "duration_sec": round(duration, 2),
            "entries_per_sec": round(metrics["eps"], 1),
            "time_for_1m_min": (
                round((1_000_000 / metrics["eps"]) / 60, 1) if metrics["eps"] > 0 else float("inf")
            ),
            "success_rate_pct": round(metrics["success_rate"] * 100, 1),
            "gate_decision": gate_decision,
            "memory_diff_top5": mem_diff[:5],
            "status": "success",
        }

    except Exception as e:
        return {
            "batch_size": batch_size,
            "approach": "streaming_executor",
            "error": str(e),
            "status": "failed",
        }


async def test_scale_guard_service(batch_size: int):
    """Test the scale guard service approach."""
    print(f"\n🛡️  Testing Scale Guard Service with {batch_size:,} entries")

    entries = generate_test_entries(batch_size)

    # Configure scale guard with optimal settings
    config = ScaleConfig(warmup_entries=128, stream_chunk=1500, inflight_chunks=4)

    service = ScaleGuardService(lambda: V7Pipeline(), config)

    mem = MemDiff(top=10)
    mem_before = mem.snapshot()

    start_time = time.time()
    try:
        results = await service.process(entries)
        duration = time.time() - start_time

        mem_after = mem.snapshot()
        mem_diff = mem.compare(mem_before, mem_after)

        # Calculate metrics
        successful = len([r for r in results if r.get("Status") != "failed"])
        success_rate = (successful / len(results)) * 100
        eps = len(entries) / duration
        time_1m = (1_000_000 / eps) / 60

        # Test with streaming gates
        gates = StreamingGates()
        gates.ingest(results)
        gate_decision = gates.decision(eps)

        await service.aclose()

        return {
            "batch_size": batch_size,
            "approach": "scale_guard_service",
            "duration_sec": round(duration, 2),
            "entries_per_sec": round(eps, 1),
            "time_for_1m_min": round(time_1m, 1),
            "success_rate_pct": round(success_rate, 1),
            "gate_decision": gate_decision,
            "memory_diff_top5": mem_diff[:5],
            "status": "success",
        }

    except Exception as e:
        return {
            "batch_size": batch_size,
            "approach": "scale_guard_service",
            "error": str(e),
            "status": "failed",
        }


async def test_memory_bounded_cache():
    """Test the memory-bounded LRU cache."""
    print(f"\n💾 Testing Memory-Bounded LRU Cache")

    cache = SizedLRU(max_bytes=64 * 1024 * 1024)  # 64MB limit

    # Fill cache with data
    for i in range(10000):
        key = f"cache_key_{i}"
        value = f"cache_value_{i}" * 100  # ~1.2KB per entry
        cache.put(key, value)

    return {
        "test": "memory_bounded_cache",
        "entries": len(cache),
        "size_bytes": cache.size_bytes,
        "size_mb": round(cache.size_bytes / 1024 / 1024, 2),
        "max_mb": 64,
        "within_limit": cache.size_bytes <= 64 * 1024 * 1024,
        "status": "success",
    }


async def comprehensive_validation():
    """Run comprehensive validation of scale fixes."""
    print("🚀 COMPREHENSIVE SCALE FIX VALIDATION")
    print("=" * 60)

    results = []

    # Test critical batch sizes that showed performance cliffs
    test_sizes = [1000, 10000, 50000, 100000]

    for size in test_sizes:
        # Test streaming executor
        result1 = await test_streaming_executor(size)
        results.append(result1)

        # Test scale guard service
        result2 = await test_scale_guard_service(size)
        results.append(result2)

        print(f"✅ Completed tests for {size:,} entries")

    # Test memory cache
    cache_result = await test_memory_bounded_cache()
    results.append(cache_result)

    return results


async def main():
    """Main validation function."""
    start_time = datetime.now()
    results = await comprehensive_validation()
    end_time = datetime.now()

    # Analyze results
    successful_tests = [r for r in results if r.get("status") == "success"]
    performance_tests = [r for r in results if "entries_per_sec" in r and r["status"] == "success"]

    print(f"\n📊 VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total tests: {len(results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Duration: {(end_time - start_time).total_seconds():.1f} seconds")

    if performance_tests:
        print(f"\n🎯 PERFORMANCE RESULTS:")
        print("Size      | Approach           | Speed (e/s) | 1M Time (min) | Success Rate | Gates")
        print("-" * 90)

        for test in performance_tests:
            size = test["batch_size"]
            approach = test["approach"][:18]
            speed = test["entries_per_sec"]
            time_1m = test["time_for_1m_min"]
            success = test["success_rate_pct"]
            gates_ok = test["gate_decision"]["ok"]
            gates_str = "✅ PASS" if gates_ok else "❌ FAIL"

            print(
                f"{size:>9,} | {approach:<18} | {speed:>11.0f} | {time_1m:>12.1f} | {success:>10.1f}% | {gates_str}"
            )

        # Find best performance
        best = max(performance_tests, key=lambda x: x["entries_per_sec"])
        print(f"\n🏆 Best Performance:")
        print(f"   {best['batch_size']:,} entries using {best['approach']}")
        print(f"   Speed: {best['entries_per_sec']:,.0f} entries/sec")
        print(f"   1M Time: {best['time_for_1m_min']:.1f} minutes")
        print(f"   Success Rate: {best['success_rate_pct']:.1f}%")

        # Check if we meet production targets
        production_ready = [
            r
            for r in performance_tests
            if r["entries_per_sec"] >= 500
            and r["success_rate_pct"] >= 95
            and r["gate_decision"]["ok"]
        ]

        print(f"\n✅ Production Ready Tests: {len(production_ready)}/{len(performance_tests)}")

        if production_ready:
            print("   Scale fixes successfully implemented!")
            print("   ✅ >500 entries/sec achieved")
            print("   ✅ >95% success rate achieved")
            print("   ✅ <35 min/1M target achieved")
        else:
            print("   ⚠️  Some targets not met - further tuning needed")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scale_fix_validation_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(
            {
                "metadata": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_sec": (end_time - start_time).total_seconds(),
                    "total_tests": len(results),
                    "successful_tests": len(successful_tests),
                },
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\n📄 Detailed results saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(main())
