#!/usr/bin/env python3
"""
COMPREHENSIVE PERFORMANCE BENCHMARK
Tests batch sizes from 10 to 1,000,000 entries
"""

import asyncio
import time
import json
import psutil
import gc
from datetime import datetime
from typing import Dict, Any, List
import traceback

# Suppress warnings
import warnings

warnings.filterwarnings("ignore")


class PerformanceBenchmark:
    """Comprehensive performance benchmarking"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_count": psutil.cpu_count(),
                "memory_gb": psutil.virtual_memory().total / (1024**3),
            },
            "benchmarks": [],
        }

    def generate_test_entries(self, count: int) -> List[Dict[str, Any]]:
        """Generate test entries with realistic data"""
        entries = []

        # Mix of different name types
        name_patterns = [
            ("김정은", "Korean"),
            ("山田太郎", "Japanese"),
            ("王小明", "Chinese"),
            ("Muhammad Ali", "Arabic"),
            ("Ivan Petrov", "Russian"),
            ("Jean-Pierre Dupont", "French"),
            ("Hans Müller", "German"),
            ("José García", "Spanish"),
            ("राज कुमार", "Hindi"),
            ("John Smith", "English"),
        ]

        for i in range(count):
            pattern = name_patterns[i % len(name_patterns)]
            entries.append(
                {
                    "CanonicalNative": f"{pattern[0]} {i}",
                    "GlobalID": f"PERF-{i:08d}",
                    "Language": pattern[1],
                }
            )

        return entries

    async def benchmark_batch(self, batch_size: int) -> Dict[str, Any]:
        """Run benchmark for a specific batch size"""
        try:
            from src.core.pipeline_v7 import V7Pipeline, PipelineMode

            print(f"\n🔬 Testing batch size: {batch_size:,}")

            # Create pipeline
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)

            # Generate test data
            entries = self.generate_test_entries(batch_size)

            # Memory before
            gc.collect()
            mem_before = psutil.Process().memory_info().rss / (1024**2)  # MB

            # Run benchmark
            start_time = time.time()
            result = await pipeline.process_batch(entries)
            duration = time.time() - start_time

            # Memory after
            mem_after = psutil.Process().memory_info().rss / (1024**2)  # MB
            mem_used = mem_after - mem_before

            # Calculate metrics
            entries_per_sec = batch_size / duration if duration > 0 else 0
            time_for_1m = (
                (1_000_000 / entries_per_sec / 60) if entries_per_sec > 0 else float("inf")
            )

            metrics = result.get("metrics", {})

            benchmark = {
                "batch_size": batch_size,
                "duration_sec": round(duration, 2),
                "entries_per_sec": round(entries_per_sec, 2),
                "time_for_1m_min": round(time_for_1m, 2),
                "memory_used_mb": round(mem_used, 2),
                "success_rate": metrics.get("success_rate", 0),
                "duplicate_count": metrics.get("duplicate_global_ids", 0),
                "status": "✅ PASS" if time_for_1m <= 35 else "❌ FAIL",
            }

            print(f"  ⏱️ Duration: {duration:.2f}s")
            print(f"  🚀 Speed: {entries_per_sec:.0f} entries/sec")
            print(f"  📊 Projected 1M time: {time_for_1m:.1f} min")
            print(f"  💾 Memory used: {mem_used:.1f} MB")
            print(f"  ✅ Success rate: {metrics.get('success_rate', 0)*100:.1f}%")
            print(f"  📈 Status: {benchmark['status']}")

            return benchmark

        except Exception as e:
            print(f"  ❌ Error: {e}")
            return {"batch_size": batch_size, "error": str(e), "status": "❌ ERROR"}

    async def run_comprehensive_benchmark(self):
        """Run full benchmark suite"""
        print("=" * 80)
        print("COMPREHENSIVE PERFORMANCE BENCHMARK")
        print("=" * 80)
        print(f"Timestamp: {self.results['timestamp']}")
        print(
            f"System: {self.results['system']['cpu_count']} CPUs, {self.results['system']['memory_gb']:.1f} GB RAM"
        )

        # Test batch sizes from 10 to 1M
        batch_sizes = [
            10,  # Very small
            50,  # Small
            100,  # Medium-small
            500,  # Medium
            1_000,  # Medium-large
            5_000,  # Large
            10_000,  # Very large
            50_000,  # Huge
            100_000,  # Massive
            500_000,  # Near 1M
            1_000_000,  # Full 1M
        ]

        for batch_size in batch_sizes:
            benchmark = await self.benchmark_batch(batch_size)
            self.results["benchmarks"].append(benchmark)

            # Small delay between tests
            await asyncio.sleep(1)

            # Force garbage collection
            gc.collect()

        # Summary
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        print("\n📊 Performance Table:")
        print(
            f"{'Batch Size':>12} | {'Speed (e/s)':>12} | {'1M Time (min)':>14} | {'Memory (MB)':>12} | {'Status':>10}"
        )
        print("-" * 80)

        for b in self.results["benchmarks"]:
            if "error" not in b:
                print(
                    f"{b['batch_size']:>12,} | {b['entries_per_sec']:>12,.0f} | {b['time_for_1m_min']:>14,.1f} | {b['memory_used_mb']:>12,.1f} | {b['status']:>10}"
                )
            else:
                print(
                    f"{b['batch_size']:>12,} | {'ERROR':>12} | {'N/A':>14} | {'N/A':>12} | {b['status']:>10}"
                )

        # Analysis
        passing = [b for b in self.results["benchmarks"] if b.get("status") == "✅ PASS"]
        failing = [b for b in self.results["benchmarks"] if "❌" in b.get("status", "")]

        print(f"\n✅ Passing: {len(passing)}/{len(self.results['benchmarks'])}")
        print(f"❌ Failing: {len(failing)}/{len(self.results['benchmarks'])}")

        if passing:
            min_passing_batch = min(b["batch_size"] for b in passing)
            print(f"📈 Minimum batch size for 35-min target: {min_passing_batch:,}")

            optimal = min(passing, key=lambda x: x["time_for_1m_min"])
            print(
                f"🎯 Optimal batch size: {optimal['batch_size']:,} ({optimal['entries_per_sec']:,.0f} entries/sec)"
            )

        # Save results
        output_file = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Full results saved to: {output_file}")

        return self.results


async def main():
    """Run the comprehensive benchmark"""
    benchmark = PerformanceBenchmark()
    results = await benchmark.run_comprehensive_benchmark()

    # Return status code based on results
    passing_count = len([b for b in results["benchmarks"] if b.get("status") == "✅ PASS"])
    return 0 if passing_count >= 5 else 1  # Need at least 5 passing sizes


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
