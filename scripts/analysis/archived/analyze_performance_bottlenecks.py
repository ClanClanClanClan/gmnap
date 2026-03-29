#!/usr/bin/env python3
"""
ULTRATHINK PERFORMANCE BOTTLENECK ANALYSIS
===========================================
Deep dive into GMNAP v7 performance issues to identify optimization opportunities
"""

import time
import json
import cProfile
import pstats
import io
import tracemalloc
import gc
from datetime import datetime
from typing import Dict, List, Any, Tuple
import numpy as np


def generate_test_entries(count: int) -> List[Dict]:
    """Generate realistic test entries for performance testing"""
    entries = []

    # Mix of different name types for realistic testing
    name_patterns = [
        ("김정은", "Korean"),
        ("王小明", "Chinese"),
        ("田中太郎", "Japanese"),
        ("Nguyễn Văn A", "Vietnamese"),
        ("Иван Петров", "Russian"),
        ("محمد علي", "Arabic"),
        ("John Smith", "English"),
        ("Jean-Pierre Dupont", "French"),
        ("Hans Müller", "German"),
        ("राज कुमार", "Hindi"),
    ]

    for i in range(count):
        pattern = name_patterns[i % len(name_patterns)]
        entries.append(
            {
                "id": f"test_{i:08d}",
                "CanonicalNative": pattern[0],
                "Region": pattern[1],
                "_metadata": {"source": "test_generator", "timestamp": datetime.now().isoformat()},
            }
        )

    return entries


def profile_pipeline_initialization():
    """Profile the initialization overhead of the pipeline"""
    print("\n📊 Profiling Pipeline Initialization...")

    profiler = cProfile.Profile()
    profiler.enable()

    start = time.time()
    from src.core.pipeline_v7 import V7Pipeline

    pipeline = V7Pipeline()
    init_time = time.time() - start

    profiler.disable()

    # Analyze profile results
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(20)

    print(f"  ⏱️  Initialization time: {init_time:.3f}s")
    print("\n  Top 20 time-consuming functions during init:")
    print(s.getvalue()[:2000])

    return init_time, pipeline


def profile_batch_processing(pipeline, batch_sizes: List[int]) -> Dict:
    """Profile processing for different batch sizes"""
    print("\n📊 Profiling Batch Processing...")

    results = {}

    for batch_size in batch_sizes:
        print(f"\n  Testing batch size: {batch_size}")

        # Generate test data
        entries = generate_test_entries(batch_size)

        # Start memory tracking
        tracemalloc.start()
        gc.collect()
        mem_before = tracemalloc.get_traced_memory()[0]

        # Profile processing
        profiler = cProfile.Profile()
        profiler.enable()

        start = time.time()
        try:
            processed = pipeline.process_batch(entries, mode="quick")
            process_time = time.time() - start
            success = True
            error = None
        except Exception as e:
            process_time = time.time() - start
            success = False
            error = str(e)
            processed = []

        profiler.disable()

        # Get memory usage
        mem_after = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        # Calculate metrics
        entries_per_sec = batch_size / process_time if process_time > 0 else 0
        time_per_entry = process_time / batch_size if batch_size > 0 else 0
        memory_per_entry = (mem_after - mem_before) / batch_size if batch_size > 0 else 0

        # Get profiling stats
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(10)
        profile_output = s.getvalue()

        results[batch_size] = {
            "batch_size": batch_size,
            "total_time": process_time,
            "entries_per_sec": entries_per_sec,
            "time_per_entry_ms": time_per_entry * 1000,
            "memory_used_mb": (mem_after - mem_before) / 1024 / 1024,
            "memory_per_entry_kb": memory_per_entry / 1024,
            "success": success,
            "error": error,
            "processed_count": len(processed) if success else 0,
            "profile_top10": profile_output[:1000],
        }

        print(f"    ✅ Success: {success}")
        print(f"    ⏱️  Time: {process_time:.3f}s")
        print(f"    🚀 Speed: {entries_per_sec:.1f} entries/sec")
        print(f"    💾 Memory: {(mem_after - mem_before) / 1024 / 1024:.1f} MB")

        if error:
            print(f"    ❌ Error: {error}")

    return results


def identify_bottlenecks(results: Dict) -> Dict:
    """Analyze results to identify specific bottlenecks"""
    print("\n🔍 Analyzing Bottlenecks...")

    analysis = {
        "fixed_overhead": None,
        "scaling_factor": None,
        "memory_scaling": None,
        "bottleneck_functions": [],
        "recommendations": [],
    }

    # Calculate fixed overhead vs variable cost
    if len(results) >= 2:
        batch_sizes = sorted(results.keys())
        times = [results[bs]["total_time"] for bs in batch_sizes]

        # Simple linear regression to find fixed + variable components
        # time = fixed_overhead + per_entry_time * batch_size
        if len(batch_sizes) >= 2:
            # Use numpy for linear regression
            x = np.array(batch_sizes)
            y = np.array(times)
            A = np.vstack([x, np.ones(len(x))]).T
            m, c = np.linalg.lstsq(A, y, rcond=None)[0]

            analysis["fixed_overhead"] = c
            analysis["scaling_factor"] = m

            print(f"  📈 Fixed overhead: {c:.3f}s")
            print(f"  📈 Per-entry time: {m*1000:.3f}ms")

            # Calculate theoretical maximum throughput
            if m > 0:
                max_throughput = 1 / m
                print(f"  📈 Theoretical max throughput: {max_throughput:.0f} entries/sec")

    # Identify common bottleneck functions
    all_profiles = []
    for result in results.values():
        if "profile_top10" in result:
            all_profiles.append(result["profile_top10"])

    # Extract function names that appear frequently
    function_counts = {}
    for profile in all_profiles:
        lines = profile.split("\n")
        for line in lines:
            if "(" in line and ")" in line:
                # Extract function name
                parts = line.split()
                if len(parts) > 5:
                    func = parts[-1]
                    function_counts[func] = function_counts.get(func, 0) + 1

    # Sort by frequency
    top_bottlenecks = sorted(function_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    analysis["bottleneck_functions"] = [f[0] for f in top_bottlenecks]

    print("\n  🔥 Top bottleneck functions:")
    for func, count in top_bottlenecks:
        print(f"    - {func}")

    # Generate recommendations based on findings
    if analysis["fixed_overhead"] and analysis["fixed_overhead"] > 0.5:
        analysis["recommendations"].append(
            "HIGH FIXED OVERHEAD: Consider lazy initialization, connection pooling, or pre-warming"
        )

    if analysis["scaling_factor"] and analysis["scaling_factor"] > 0.001:
        analysis["recommendations"].append(
            "HIGH PER-ENTRY COST: Optimize core processing algorithms, use vectorization"
        )

    # Check for memory issues
    mem_scalings = [results[bs]["memory_per_entry_kb"] for bs in sorted(results.keys())]
    if mem_scalings and max(mem_scalings) > 10:
        analysis["recommendations"].append(
            "HIGH MEMORY USAGE: Implement streaming processing, reduce object copies"
        )

    # Small batch specific recommendations
    small_batch_speeds = [
        results[bs]["entries_per_sec"] for bs in sorted(results.keys()) if bs <= 50
    ]
    if small_batch_speeds and max(small_batch_speeds) < 100:
        analysis["recommendations"].append(
            "POOR SMALL BATCH PERFORMANCE: Implement batch aggregation, reduce per-batch overhead"
        )

    print("\n  💡 Recommendations:")
    for rec in analysis["recommendations"]:
        print(f"    • {rec}")

    return analysis


def test_optimization_strategies(pipeline) -> Dict:
    """Test various optimization strategies"""
    print("\n🧪 Testing Optimization Strategies...")

    strategies = {}
    test_size = 100
    entries = generate_test_entries(test_size)

    # Strategy 1: Batch aggregation for small batches
    print("\n  Strategy 1: Batch Aggregation")
    small_batches = [entries[i : i + 10] for i in range(0, len(entries), 10)]

    # Test without aggregation
    start = time.time()
    for batch in small_batches:
        try:
            pipeline.process_batch(batch, mode="quick")
        except:
            pass
    no_agg_time = time.time() - start

    # Test with aggregation (process as single batch)
    start = time.time()
    try:
        pipeline.process_batch(entries, mode="quick")
    except:
        pass
    agg_time = time.time() - start

    improvement = (no_agg_time - agg_time) / no_agg_time * 100 if no_agg_time > 0 else 0
    strategies["batch_aggregation"] = {
        "no_aggregation_time": no_agg_time,
        "aggregation_time": agg_time,
        "improvement_percent": improvement,
    }
    print(f"    Without aggregation: {no_agg_time:.3f}s")
    print(f"    With aggregation: {agg_time:.3f}s")
    print(f"    Improvement: {improvement:.1f}%")

    # Strategy 2: Test different processing modes
    print("\n  Strategy 2: Processing Modes")
    modes = ["quick", "full", "extreme"]
    for mode in modes:
        start = time.time()
        try:
            pipeline.process_batch(entries[:50], mode=mode)
            mode_time = time.time() - start
            success = True
        except Exception as e:
            mode_time = time.time() - start
            success = False

        strategies[f"mode_{mode}"] = {
            "time": mode_time,
            "entries_per_sec": 50 / mode_time if mode_time > 0 else 0,
            "success": success,
        }
        print(f"    {mode} mode: {mode_time:.3f}s ({50/mode_time:.1f} entries/sec)")

    return strategies


def prepare_1m_test_data() -> str:
    """Prepare 1M test entries for realistic testing"""
    print("\n📦 Preparing 1M Test Dataset...")

    output_file = "1m_test_dataset.json"
    batch_size = 10000
    total_batches = 100

    all_entries = []
    for i in range(total_batches):
        if i % 10 == 0:
            print(f"  Generating batch {i+1}/{total_batches}...")
        batch = generate_test_entries(batch_size)
        all_entries.extend(batch)

    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"  ✅ Saved 1M entries to {output_file}")
    return output_file


def run_1m_performance_test(pipeline, data_file: str) -> Dict:
    """Run actual 1M entry performance test"""
    print("\n🚀 Running 1M Entry Performance Test...")

    # Load test data
    print("  Loading test data...")
    with open(data_file, "r", encoding="utf-8") as f:
        entries = json.load(f)

    print(f"  Loaded {len(entries):,} entries")

    # Test with different batch sizes
    batch_configs = [
        (1000, 1000),  # 1K batches, 1000 total batches
        (10000, 100),  # 10K batches, 100 total batches
        (50000, 20),  # 50K batches, 20 total batches
        (100000, 10),  # 100K batches, 10 total batches
    ]

    results = {}

    for batch_size, num_batches in batch_configs:
        print(f"\n  Testing with {batch_size:,} entry batches ({num_batches} batches)...")

        gc.collect()
        tracemalloc.start()
        mem_start = tracemalloc.get_traced_memory()[0]

        start_time = time.time()
        processed_total = 0
        errors = []

        for i in range(num_batches):
            batch_start = i * batch_size
            batch_end = min(batch_start + batch_size, len(entries))
            batch = entries[batch_start:batch_end]

            try:
                result = pipeline.process_batch(batch, mode="quick")
                processed_total += len(result)

                if i % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = processed_total / elapsed if elapsed > 0 else 0
                    eta = (len(entries) - processed_total) / rate if rate > 0 else 0
                    print(
                        f"    Progress: {processed_total:,}/{len(entries):,} "
                        f"({rate:.0f} entries/sec, ETA: {eta:.0f}s)"
                    )
            except Exception as e:
                errors.append(f"Batch {i}: {str(e)}")
                if len(errors) > 5:
                    print(f"    ❌ Too many errors, aborting test")
                    break

        total_time = time.time() - start_time
        mem_end = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        results[batch_size] = {
            "batch_size": batch_size,
            "num_batches": num_batches,
            "total_entries": len(entries),
            "processed_entries": processed_total,
            "total_time_sec": total_time,
            "total_time_min": total_time / 60,
            "entries_per_sec": processed_total / total_time if total_time > 0 else 0,
            "memory_used_mb": (mem_end - mem_start) / 1024 / 1024,
            "errors": errors[:5],  # First 5 errors
            "success": len(errors) == 0,
        }

        print(f"    ✅ Processed: {processed_total:,}/{len(entries):,}")
        print(f"    ⏱️  Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        print(f"    🚀 Speed: {processed_total/total_time:.0f} entries/sec")
        print(f"    💾 Memory: {(mem_end - mem_start) / 1024 / 1024:.1f} MB")

        if errors:
            print(f"    ❌ Errors: {len(errors)}")

    return results


def main():
    """Main analysis workflow"""
    print("=" * 80)
    print("ULTRATHINK PERFORMANCE BOTTLENECK ANALYSIS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Initialize pipeline
    init_time, pipeline = profile_pipeline_initialization()

    # Test various batch sizes
    batch_sizes = [1, 10, 50, 100, 500, 1000, 5000]
    batch_results = profile_batch_processing(pipeline, batch_sizes)

    # Analyze bottlenecks
    bottleneck_analysis = identify_bottlenecks(batch_results)

    # Test optimization strategies
    optimization_results = test_optimization_strategies(pipeline)

    # Prepare test data
    test_data_file = prepare_1m_test_data()

    # Run 1M entry test
    one_million_results = run_1m_performance_test(pipeline, test_data_file)

    # Save all results
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "initialization_time": init_time,
        "batch_performance": batch_results,
        "bottleneck_analysis": bottleneck_analysis,
        "optimization_strategies": optimization_results,
        "one_million_test": one_million_results,
    }

    output_file = f"performance_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    # Summary
    print("\n📊 SUMMARY:")
    print(f"  • Pipeline initialization: {init_time:.3f}s")
    print(f"  • Fixed overhead: {bottleneck_analysis.get('fixed_overhead', 'N/A'):.3f}s")
    print(
        f"  • Scaling factor: {bottleneck_analysis.get('scaling_factor', 0)*1000:.3f}ms per entry"
    )

    # Check if we meet targets
    best_1m_result = (
        min(one_million_results.values(), key=lambda x: x["total_time_sec"])
        if one_million_results
        else None
    )

    if best_1m_result:
        print(f"\n  🎯 1M ENTRY TEST RESULTS:")
        print(f"    • Best time: {best_1m_result['total_time_min']:.1f} minutes")
        print(f"    • Best speed: {best_1m_result['entries_per_sec']:.0f} entries/sec")
        print(f"    • Target: 35 minutes (476 entries/sec)")

        if best_1m_result["total_time_min"] <= 35:
            print(f"    ✅ MEETS TARGET!")
        else:
            print(
                f"    ❌ DOES NOT MEET TARGET (off by {best_1m_result['total_time_min'] - 35:.1f} minutes)"
            )

    # Small batch performance
    small_batch_results = {k: v for k, v in batch_results.items() if k <= 50}
    if small_batch_results:
        worst_small = min(small_batch_results.values(), key=lambda x: x["entries_per_sec"])
        print(f"\n  📦 SMALL BATCH PERFORMANCE:")
        print(
            f"    • Worst case: {worst_small['entries_per_sec']:.0f} entries/sec (batch size {worst_small['batch_size']})"
        )
        print(f"    • Target: >100 entries/sec")

        if worst_small["entries_per_sec"] >= 100:
            print(f"    ✅ MEETS TARGET!")
        else:
            print(f"    ❌ DOES NOT MEET TARGET")

    print(f"\n📄 Full results saved to: {output_file}")

    return all_results


if __name__ == "__main__":
    main()
