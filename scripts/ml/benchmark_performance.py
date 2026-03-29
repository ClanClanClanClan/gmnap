#!/usr/bin/env python3
"""
ML Classifier Performance Benchmarking

Measures:
- Latency (single prediction, batch)
- Throughput (predictions/second)
- Memory usage
- Model loading time

Based on integration contract requirements:
- Single prediction: ~1-3ms target
- Batch (1000): ~0.5s target
- Model size: 766MB
"""

import sys
import time
import json
import psutil
from pathlib import Path
from statistics import mean, median, stdev
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.regional_classifier_v5 import RegionalClassifierV5, detect_region_v5
from src.regions.hybrid_classifier import HybridRegionClassifier


def benchmark_model_loading():
    """Benchmark model loading time"""
    print("=" * 80)
    print("BENCHMARK 1: MODEL LOADING TIME")
    print("=" * 80)

    # Measure memory before
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    print(f"\nMemory before loading: {mem_before:.1f} MB")

    # Time model loading
    start = time.time()
    classifier = RegionalClassifierV5()
    load_time = time.time() - start

    # Measure memory after
    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    mem_increase = mem_after - mem_before

    print(f"Memory after loading: {mem_after:.1f} MB")
    print(f"Memory increase: {mem_increase:.1f} MB")
    print(f"Loading time: {load_time:.3f} seconds")

    model_file_size = (
        Path("data/ml_training/regional_classifier_v5_etymology.bin").stat().st_size / 1024 / 1024
    )
    print(f"Model file size: {model_file_size:.1f} MB")

    return {
        "loading_time_seconds": load_time,
        "memory_increase_mb": mem_increase,
        "model_file_size_mb": model_file_size,
    }


def benchmark_single_prediction():
    """Benchmark single prediction latency"""
    print("\n" + "=" * 80)
    print("BENCHMARK 2: SINGLE PREDICTION LATENCY")
    print("=" * 80)

    classifier = RegionalClassifierV5()

    test_names = [
        "John Smith",
        "José García",
        "Michel Ferin",
        "Zhang Wei",
        "Vladimir Putin",
    ]

    print(f"\nTesting {len(test_names)} names, 100 iterations each...")

    all_times = []
    for name in test_names:
        times = []
        for _ in range(100):
            start = time.perf_counter()
            result = classifier.predict(name, k=3)
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms

        all_times.extend(times)

        print(f"\n  {name:20}")
        print(f"    Mean: {mean(times):.2f} ms")
        print(f"    Median: {median(times):.2f} ms")
        print(f"    Min: {min(times):.2f} ms")
        print(f"    Max: {max(times):.2f} ms")
        print(f"    Stdev: {stdev(times):.2f} ms")

    print(f"\nOverall Statistics (500 predictions):")
    print(f"  Mean latency: {mean(all_times):.2f} ms")
    print(f"  Median latency: {median(all_times):.2f} ms")
    print(f"  95th percentile: {sorted(all_times)[int(len(all_times) * 0.95)]:.2f} ms")
    print(f"  99th percentile: {sorted(all_times)[int(len(all_times) * 0.99)]:.2f} ms")

    # Check against target
    target_latency_ms = 3.0
    status = "✅ PASS" if mean(all_times) <= target_latency_ms else "⚠️ SLOW"
    print(f"\n  Target: ≤{target_latency_ms}ms")
    print(f"  Status: {status}")

    return {
        "mean_latency_ms": mean(all_times),
        "median_latency_ms": median(all_times),
        "p95_latency_ms": sorted(all_times)[int(len(all_times) * 0.95)],
        "p99_latency_ms": sorted(all_times)[int(len(all_times) * 0.99)],
        "min_latency_ms": min(all_times),
        "max_latency_ms": max(all_times),
        "total_predictions": len(all_times),
    }


def benchmark_batch_prediction():
    """Benchmark batch prediction throughput"""
    print("\n" + "=" * 80)
    print("BENCHMARK 3: BATCH PREDICTION THROUGHPUT")
    print("=" * 80)

    classifier = RegionalClassifierV5()

    # Generate test names
    test_names = [
        "John Smith",
        "Jane Doe",
        "José García",
        "Michel Ferin",
        "Luigi Ferrucci",
        "Zhang Wei",
        "Li Ming",
        "Vladimir Putin",
        "Anna Kowalski",
        "Hans Müller",
        "François Dubois",
        "María González",
    ]

    batch_sizes = [10, 100, 1000]

    results = []
    for batch_size in batch_sizes:
        # Create batch (repeat test names to fill)
        batch = [test_names[i % len(test_names)] for i in range(batch_size)]

        # Time batch prediction
        start = time.time()
        predictions = classifier.predict_batch(batch, k=3)
        elapsed = time.time() - start

        throughput = batch_size / elapsed

        print(f"\nBatch size: {batch_size}")
        print(f"  Time: {elapsed:.3f} seconds")
        print(f"  Throughput: {throughput:.1f} predictions/second")
        print(f"  Avg latency: {elapsed/batch_size*1000:.2f} ms per prediction")

        results.append(
            {
                "batch_size": batch_size,
                "time_seconds": elapsed,
                "throughput_per_second": throughput,
                "avg_latency_ms": elapsed / batch_size * 1000,
            }
        )

    # Check against target (1000 in 0.5s = 2000/s)
    target_throughput = 2000
    large_batch = results[-1]
    status = "✅ PASS" if large_batch["throughput_per_second"] >= target_throughput else "⚠️ SLOW"

    print(f"\n  Target: ≥{target_throughput} predictions/second")
    print(f"  Achieved (batch=1000): {large_batch['throughput_per_second']:.1f}/s")
    print(f"  Status: {status}")

    return results


def benchmark_hybrid_classifier():
    """Benchmark hybrid classifier (Phase 1 + Phase 2)"""
    print("\n" + "=" * 80)
    print("BENCHMARK 4: HYBRID CLASSIFIER")
    print("=" * 80)

    print("\nInitializing HybridRegionClassifier...")
    start = time.time()
    classifier = HybridRegionClassifier()
    init_time = time.time() - start
    print(f"  Initialization time: {init_time:.3f} seconds")

    test_cases = [
        ("John Smith", "Phase 1 rules"),
        ("José García", "Phase 1 rules"),
        ("Vladimir Putin", "Phase 2 ML"),
        ("Zhang Wei", "Phase 2 ML"),
        ("Michel Ferin", "Phase 2 ML"),
    ]

    print(f"\nTesting {len(test_cases)} cases, 50 iterations each...")

    all_times = []
    for name, expected_method in test_cases:
        times = []
        for _ in range(50):
            entry = {"CanonicalNative": name}
            start = time.perf_counter()
            result = classifier.detect_region(entry)
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)

        all_times.extend(times)

        method_match = (
            "✅"
            if expected_method.lower().replace(" ", "_") in result.detection_method.lower()
            else "❌"
        )
        print(f"\n  {name:20} {method_match}")
        print(f"    Mean: {mean(times):.2f} ms")
        print(f"    Method: {result.detection_method}")

    print(f"\nOverall Hybrid Statistics ({len(all_times)} predictions):")
    print(f"  Mean latency: {mean(all_times):.2f} ms")
    print(f"  Median latency: {median(all_times):.2f} ms")

    return {
        "initialization_time_seconds": init_time,
        "mean_latency_ms": mean(all_times),
        "median_latency_ms": median(all_times),
        "total_predictions": len(all_times),
    }


def benchmark_calibration_overhead():
    """Measure calibration overhead"""
    print("\n" + "=" * 80)
    print("BENCHMARK 5: CALIBRATION OVERHEAD")
    print("=" * 80)

    # Create classifier with and without calibration
    print("\nComparing uncalibrated vs calibrated predictions...")

    # Simulate uncalibrated (T=1.0)
    classifier_uncalibrated = RegionalClassifierV5(temperature=1.0)
    classifier_calibrated = RegionalClassifierV5(temperature=2.817)

    test_name = "John Smith"
    iterations = 1000

    # Uncalibrated
    times_uncal = []
    for _ in range(iterations):
        start = time.perf_counter()
        classifier_uncalibrated.predict(test_name, k=3)
        elapsed = time.perf_counter() - start
        times_uncal.append(elapsed * 1000)

    # Calibrated
    times_cal = []
    for _ in range(iterations):
        start = time.perf_counter()
        classifier_calibrated.predict(test_name, k=3)
        elapsed = time.perf_counter() - start
        times_cal.append(elapsed * 1000)

    overhead_ms = mean(times_cal) - mean(times_uncal)
    overhead_pct = (overhead_ms / mean(times_uncal)) * 100

    print(f"\nUncalibrated (T=1.0):")
    print(f"  Mean: {mean(times_uncal):.2f} ms")

    print(f"\nCalibrated (T=2.817):")
    print(f"  Mean: {mean(times_cal):.2f} ms")

    print(f"\nCalibration Overhead:")
    print(f"  Absolute: {overhead_ms:.3f} ms")
    print(f"  Relative: {overhead_pct:.1f}%")

    status = "✅ NEGLIGIBLE" if overhead_pct < 5 else "⚠️ SIGNIFICANT"
    print(f"  Status: {status}")

    return {
        "uncalibrated_mean_ms": mean(times_uncal),
        "calibrated_mean_ms": mean(times_cal),
        "overhead_ms": overhead_ms,
        "overhead_percent": overhead_pct,
    }


def main():
    """Run all benchmarks and generate report"""
    print("=" * 80)
    print("ML CLASSIFIER PERFORMANCE BENCHMARKS")
    print("=" * 80)
    print(f"\nStarting at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    try:
        # Run benchmarks
        results["model_loading"] = benchmark_model_loading()
        results["single_prediction"] = benchmark_single_prediction()
        results["batch_prediction"] = benchmark_batch_prediction()
        results["hybrid_classifier"] = benchmark_hybrid_classifier()
        results["calibration_overhead"] = benchmark_calibration_overhead()

        # Summary
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        print(f"\n✅ Model Loading:")
        print(f"   Time: {results['model_loading']['loading_time_seconds']:.3f}s")
        print(f"   Memory: {results['model_loading']['memory_increase_mb']:.1f} MB")

        print(f"\n✅ Single Prediction:")
        print(f"   Mean latency: {results['single_prediction']['mean_latency_ms']:.2f} ms")
        print(f"   P95 latency: {results['single_prediction']['p95_latency_ms']:.2f} ms")

        print(f"\n✅ Batch Throughput (1000):")
        large_batch = results["batch_prediction"][-1]
        print(f"   Throughput: {large_batch['throughput_per_second']:.1f} predictions/second")

        print(f"\n✅ Hybrid Classifier:")
        print(f"   Init time: {results['hybrid_classifier']['initialization_time_seconds']:.3f}s")
        print(f"   Mean latency: {results['hybrid_classifier']['mean_latency_ms']:.2f} ms")

        print(f"\n✅ Calibration:")
        print(
            f"   Overhead: {results['calibration_overhead']['overhead_ms']:.3f} ms ({results['calibration_overhead']['overhead_percent']:.1f}%)"
        )

        # Save report
        report_path = Path("reports/performance_benchmark_v5.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "benchmark_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_version": "v5-etymology",
            "results": results,
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n✅ Report saved to: {report_path}")

        print("\n" + "=" * 80)
        print("ALL BENCHMARKS COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
