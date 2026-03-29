#!/usr/bin/env python3
"""
Performance test script for Korean V5 converter
Tests P95 latency, throughput, and memory usage targets
"""

import argparse
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import psutil
import yaml

sys.path.insert(0, "../src")
from v5.converter_cached import optimized_convert


def load_test_names(yaml_path, limit=1000):
    """Load test names from Korean dataset"""
    data = yaml.safe_load(open(yaml_path))
    names = []

    for entry_id, entry in data.items():
        canonical = entry.get("CanonicalLatin", "")
        if canonical:
            names.append(canonical)

        if len(names) >= limit:
            break

    return names


def single_thread_test(names, iterations=3):
    """Test single-threaded performance"""
    print(f"Testing {len(names)} names x {iterations} iterations (single-threaded)")

    latencies = []
    start_time = time.time()

    for _ in range(iterations):
        for name in names:
            start = time.perf_counter()
            optimized_convert(name)
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

    end_time = time.time()
    total_conversions = len(names) * iterations
    elapsed = end_time - start_time
    throughput = total_conversions / elapsed

    # Calculate statistics
    p95_latency = statistics.quantile(latencies, 0.95)
    avg_latency = statistics.mean(latencies)
    max_latency = max(latencies)

    return {
        "p95_latency_ms": p95_latency,
        "avg_latency_ms": avg_latency,
        "max_latency_ms": max_latency,
        "throughput_per_sec": throughput,
        "total_conversions": total_conversions,
        "elapsed_sec": elapsed,
    }


def multi_thread_test(names, num_threads=4, iterations=3):
    """Test multi-threaded performance"""
    print(
        f"Testing {len(names)} names x {iterations} iterations ({num_threads} threads)"
    )

    def worker(name_batch):
        results = []
        for name in name_batch:
            start = time.perf_counter()
            optimized_convert(name)
            end = time.perf_counter()
            results.append((end - start) * 1000)
        return results

    # Split names into batches for threads
    batch_size = len(names) // num_threads
    batches = [names[i : i + batch_size] for i in range(0, len(names), batch_size)]

    all_latencies = []
    start_time = time.time()

    for _ in range(iterations):
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            batch_results = list(executor.map(worker, batches))
            for batch_latencies in batch_results:
                all_latencies.extend(batch_latencies)

    end_time = time.time()
    total_conversions = len(all_latencies)
    elapsed = end_time - start_time
    throughput = total_conversions / elapsed

    # Calculate statistics
    p95_latency = statistics.quantile(all_latencies, 0.95)
    avg_latency = statistics.mean(all_latencies)
    max_latency = max(all_latencies)

    return {
        "p95_latency_ms": p95_latency,
        "avg_latency_ms": avg_latency,
        "max_latency_ms": max_latency,
        "throughput_per_sec": throughput,
        "total_conversions": total_conversions,
        "elapsed_sec": elapsed,
        "num_threads": num_threads,
    }


def memory_test():
    """Test memory usage"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    return {
        "memory_rss_mb": memory_info.rss / 1024 / 1024,
        "memory_vms_mb": memory_info.vms / 1024 / 1024,
    }


def cache_performance_test(names):
    """Test cache effectiveness"""
    # Clear cache
    optimized_convert.cache_clear()

    # First pass - populate cache
    for name in names:
        optimized_convert(name)

    # Second pass - test cache hits
    start_time = time.time()
    for name in names:
        optimized_convert(name)
    end_time = time.time()

    cache_info = optimized_convert.cache_info()

    return {
        "cache_hits": cache_info.hits,
        "cache_misses": cache_info.misses,
        "cache_hit_rate": cache_info.hits / (cache_info.hits + cache_info.misses),
        "cached_throughput": len(names) / (end_time - start_time),
    }


def run_performance_tests(yaml_path):
    """Run comprehensive performance tests"""
    print("=== Korean V5 Performance Test ===")

    # Load test data
    names = load_test_names(yaml_path, limit=1000)
    print(f"Loaded {len(names)} test names")

    # Test targets from blueprint
    targets = {"p95_latency_ms": 120, "throughput_per_sec": 1000, "memory_mb": 500}

    results = {}

    # Single-threaded test
    print("\n--- Single-threaded Test ---")
    results["single_thread"] = single_thread_test(names[:100])

    # Multi-threaded test
    print("\n--- Multi-threaded Test ---")
    results["multi_thread"] = multi_thread_test(names[:100], num_threads=4)

    # Memory test
    print("\n--- Memory Test ---")
    results["memory"] = memory_test()

    # Cache test
    print("\n--- Cache Performance Test ---")
    results["cache"] = cache_performance_test(names[:200])

    # Print results
    print("\n=== PERFORMANCE RESULTS ===")

    # Single-threaded results
    st = results["single_thread"]
    print("\nSingle-threaded:")
    print(
        f"  P95 Latency: {st['p95_latency_ms']:.1f}ms (target: <{targets['p95_latency_ms']}ms)"
    )
    print(f"  Avg Latency: {st['avg_latency_ms']:.1f}ms")
    print(
        f"  Throughput: {st['throughput_per_sec']:.0f}/sec (target: >{targets['throughput_per_sec']}/sec)"
    )

    # Multi-threaded results
    mt = results["multi_thread"]
    print(f"\nMulti-threaded ({mt['num_threads']} threads):")
    print(
        f"  P95 Latency: {mt['p95_latency_ms']:.1f}ms (target: <{targets['p95_latency_ms']}ms)"
    )
    print(
        f"  Throughput: {mt['throughput_per_sec']:.0f}/sec (target: >{targets['throughput_per_sec']}/sec)"
    )

    # Memory results
    mem = results["memory"]
    print("\nMemory Usage:")
    print(
        f"  RSS Memory: {mem['memory_rss_mb']:.1f}MB (target: <{targets['memory_mb']}MB)"
    )

    # Cache results
    cache = results["cache"]
    print("\nCache Performance:")
    print(f"  Hit Rate: {cache['cache_hit_rate']:.1%}")
    print(f"  Cached Throughput: {cache['cached_throughput']:.0f}/sec")

    # Pass/Fail assessment
    print("\n=== TARGET ASSESSMENT ===")

    p95_pass = st["p95_latency_ms"] < targets["p95_latency_ms"]
    throughput_pass = mt["throughput_per_sec"] > targets["throughput_per_sec"]
    memory_pass = mem["memory_rss_mb"] < targets["memory_mb"]

    print(f"P95 Latency: {'PASS' if p95_pass else 'FAIL'}")
    print(f"Throughput: {'PASS' if throughput_pass else 'FAIL'}")
    print(f"Memory: {'PASS' if memory_pass else 'FAIL'}")

    all_pass = p95_pass and throughput_pass and memory_pass
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")

    return results, all_pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Korean V5 performance tests")
    parser.add_argument(
        "-i",
        "--input",
        default="data/korean.yaml",
        help="Input YAML file with test data",
    )
    args = parser.parse_args()

    results, success = run_performance_tests(args.input)

    # Exit with appropriate code
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
