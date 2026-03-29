#!/usr/bin/env python3
"""
ULTRATHINK Performance Profiler
Identifies bottlenecks in the V7 pipeline
"""

import asyncio
import cProfile
import pstats
import io
import time
from src.core.pipeline_v7 import V7Pipeline, PipelineMode


async def profile_pipeline():
    """Profile the pipeline with test data."""
    # Generate test data
    test_data = []
    for i in range(100):  # Test with 100 entries
        test_data.append(
            {
                "CanonicalNative": f"Test Name {i}",
                "GlobalID": f"TEST-{i:04d}",
                "BirthYear": 1950 + (i % 50),
            }
        )

    print(f"Testing with {len(test_data)} entries...")

    # Time the pipeline
    start = time.time()
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    result = await pipeline.process_batch(test_data)
    duration = time.time() - start

    print(f"\nResults:")
    print(f"  Duration: {duration:.2f} seconds")
    print(f"  Entries/sec: {len(test_data)/duration:.1f}")
    print(f"  Projected 1M time: {(1000000 * duration / len(test_data) / 60):.1f} minutes")
    print(f"  Success rate: {result['metrics']['success_rate']:.1%}")

    # Show stage timings
    print(f"\nStage Timings:")
    for stage, timing in result["metrics"]["stage_timings"].items():
        print(f"  {stage}: {timing:.3f}s")

    return result


def main():
    """Run profiling."""
    print("=" * 60)
    print("ULTRATHINK PERFORMANCE PROFILER")
    print("=" * 60)

    # Create profiler
    profiler = cProfile.Profile()

    # Run with profiling
    profiler.enable()
    result = asyncio.run(profile_pipeline())
    profiler.disable()

    # Generate stats
    print("\n" + "=" * 60)
    print("TOP 20 TIME-CONSUMING FUNCTIONS")
    print("=" * 60)

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(20)

    # Parse and display nicely
    lines = s.getvalue().split("\n")
    for line in lines:
        if "function calls" in line or "ncalls" in line:
            print(line)
        elif line.strip() and not line.startswith("   "):
            parts = line.split()
            if len(parts) >= 6:
                try:
                    ncalls = parts[0]
                    tottime = float(parts[1])
                    percall = float(parts[2])
                    cumtime = float(parts[3])

                    # Only show significant functions (>0.1s cumulative)
                    if cumtime > 0.1:
                        func_name = " ".join(parts[5:])
                        # Simplify function names
                        if "/" in func_name:
                            func_name = "..." + func_name.split("/")[-1]
                        if len(func_name) > 60:
                            func_name = func_name[:57] + "..."

                        print(f"  {cumtime:6.2f}s  {tottime:6.2f}s  {ncalls:>8}  {func_name}")
                except (ValueError, IndexError):
                    pass

    # Identify bottlenecks
    print("\n" + "=" * 60)
    print("BOTTLENECK ANALYSIS")
    print("=" * 60)

    stage_timings = result["metrics"]["stage_timings"]
    total_stage_time = sum(stage_timings.values())

    # Sort stages by time
    sorted_stages = sorted(stage_timings.items(), key=lambda x: x[1], reverse=True)

    print(f"Total stage time: {total_stage_time:.2f}s")
    print(f"\nSlowest stages:")
    for stage, timing in sorted_stages[:5]:
        percent = (timing / total_stage_time * 100) if total_stage_time > 0 else 0
        print(f"  {stage}: {timing:.2f}s ({percent:.1f}%)")

    # Performance recommendations
    print("\n" + "=" * 60)
    print("PERFORMANCE RECOMMENDATIONS")
    print("=" * 60)

    entries_per_sec = result["metrics"]["entries_per_second"]
    target_rate = 1000000 / (35 * 60)  # 35 min for 1M

    if entries_per_sec < target_rate:
        speedup_needed = target_rate / entries_per_sec
        print(f"❌ Current: {entries_per_sec:.1f} entries/sec")
        print(f"❌ Target: {target_rate:.1f} entries/sec")
        print(f"❌ Need {speedup_needed:.1f}x speedup")

        print("\nRecommended optimizations:")
        print("1. Enable parallel processing for regional detection")
        print("2. Batch database operations")
        print("3. Cache authority API responses")
        print("4. Use memory-mapped files for large datasets")
        print("5. Optimize regex compilations")
        print("6. Reduce quality gate check frequency")
    else:
        print(f"✅ Performance target met: {entries_per_sec:.1f} entries/sec")


if __name__ == "__main__":
    main()
