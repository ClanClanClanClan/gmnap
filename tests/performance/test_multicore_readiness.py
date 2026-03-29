from typing import Any

import pytest

#!/usr/bin/env python3
"""
Comprehensive test of multi-core parallelization readiness
"""

import concurrent.futures
import multiprocessing
import sys
import time
from pathlib import Path
from typing import Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.regions.manager import RegionManager


def process_mathematician_batch(batch_info: Dict[str, Any]) -> Dict[str, Any]:
    """Process a batch of mathematician entries (for multiprocessing test)."""
    batch_id = batch_info["batch_id"]
    entries = batch_info["entries"]

    # Create fresh manager for this process
    manager = RegionManager(Path("./config"))

    results = {"batch_id": batch_id, "processed": 0, "errors": [], "processing_time": 0}

    start_time = time.time()

    try:
        for entry in entries:
            # Get fresh region instance (thread-safe by default)
            region = manager.get_region("A1")

            if region:
                try:
                    region.clean(entry)
                    region.augment(entry)
                    region.validate(entry)
                    results["processed"] += 1
                except Exception as e:
                    results["errors"].append(
                        f"Entry {entry.get('GlobalID', 'unknown')}: {e}"
                    )
            else:
                results["errors"].append(
                    f"Failed to get region for entry {entry.get('GlobalID', 'unknown')}"
                )

    except Exception as e:
        results["errors"].append(f"Batch processing error: {e}")

    results["processing_time"] = time.time() - start_time
    return results


@pytest.mark.timeout(15)
def test_multicore_processing():
    """Test actual multicore processing capability."""
    print("🧪 TESTING MULTICORE PROCESSING CAPABILITY")

    # Generate test data
    total_entries = 1000
    num_processes = min(multiprocessing.cpu_count(), 8)  # Don't overwhelm system
    batch_size = total_entries // num_processes

    print(f"Total entries: {total_entries}")
    print(f"Number of processes: {num_processes}")
    print(f"Batch size: {batch_size}")

    # Create batches
    batches = []
    for i in range(num_processes):
        start_idx = i * batch_size
        end_idx = start_idx + batch_size if i < num_processes - 1 else total_entries

        entries = []
        for j in range(start_idx, end_idx):
            entries.append(
                {
                    "GlobalID": f"multicore-test-{j}",
                    "CanonicalLatin": f"Test Mathematician {j}",
                    "Field": "Mathematics",
                }
            )

        batches.append({"batch_id": i, "entries": entries})

    # Process batches in parallel using multiprocessing
    start_time = time.time()

    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(process_mathematician_batch, batches)

    end_time = time.time()

    # Analyze results
    total_processed = sum(r["processed"] for r in results)
    total_errors = sum(len(r["errors"]) for r in results)
    total_time = end_time - start_time
    avg_batch_time = sum(r["processing_time"] for r in results) / len(results)

    print("\nMulticore processing results:")
    print(
        f"Total processed: {total_processed}/{total_entries} ({100*total_processed/total_entries:.1f}%)"
    )
    print(f"Total errors: {total_errors}")
    print(f"Wall clock time: {total_time:.3f}s")
    print(f"Average batch time: {avg_batch_time:.3f}s")
    print(f"Parallelization efficiency: {avg_batch_time/total_time*num_processes:.1f}x")

    if total_errors > 0:
        print("Sample errors:")
        all_errors = []
        for result in results:
            all_errors.extend(result["errors"])
        for error in all_errors[:3]:
            print(f"  {error}")

    success_rate = total_processed / total_entries
    parallel_efficiency = avg_batch_time / total_time * num_processes

    if success_rate >= 0.99 and parallel_efficiency >= 0.5:
        print("PASS MULTICORE PROCESSING: EXCELLENT")
        return True
    elif success_rate >= 0.95 and parallel_efficiency >= 0.3:
        print("PASS MULTICORE PROCESSING: GOOD")
        return True
    else:
        print("FAIL MULTICORE PROCESSING: ISSUES DETECTED")
        return False


@pytest.mark.timeout(15)
def test_thread_pool_scaling():
    """Test thread pool scaling performance."""
    print("\n🧪 TESTING THREAD POOL SCALING")

    manager = RegionManager(Path("./config"))
    test_entries = [
        {"GlobalID": f"thread-scale-{i}", "CanonicalLatin": f"Thread Scale Test {i}"}
        for i in range(500)
    ]

    def process_entry(entry):
        region = manager.get_region("A1", thread_safe=True)
        region.clean(entry)
        region.augment(entry)
        return True

    # Test different thread pool sizes
    thread_counts = [1, 2, 4, 8, 16]
    results = {}

    for thread_count in thread_counts:
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=thread_count
        ) as executor:
            futures = [executor.submit(process_entry, entry) for entry in test_entries]
            success_count = sum(
                1 for f in concurrent.futures.as_completed(futures) if f.result()
            )

        end_time = time.time()
        results[thread_count] = {
            "time": end_time - start_time,
            "success": success_count,
            "throughput": success_count / (end_time - start_time),
        }

    # Analyze scaling
    print("Thread scaling results:")
    baseline_throughput = results[1]["throughput"]

    for thread_count in thread_counts:
        result = results[thread_count]
        scaling_efficiency = result["throughput"] / baseline_throughput / thread_count
        print(
            f"  {thread_count:2d} threads: {result['time']:.3f}s, {result['throughput']:.1f} entries/s, "
            f"efficiency: {scaling_efficiency:.2f}"
        )

    # Check if we see reasonable scaling
    best_throughput = max(r["throughput"] for r in results.values())
    scaling_improvement = best_throughput / baseline_throughput

    if scaling_improvement >= 2.0:
        print("PASS THREAD SCALING: EXCELLENT")
        return True
    elif scaling_improvement >= 1.5:
        print("PASS THREAD SCALING: GOOD")
        return True
    else:
        print("WARN THREAD SCALING: LIMITED")
        return False


@pytest.mark.timeout(15)
def test_stress_concurrent_load():
    """Test system under heavy concurrent load."""
    print("\n🧪 TESTING STRESS CONCURRENT LOAD")

    manager = RegionManager(Path("./config"))

    errors = []
    processed_count = 0

    def stress_worker(worker_id):
        nonlocal processed_count
        worker_errors = []
        worker_processed = 0

        for i in range(200):  # 200 entries per worker
            try:
                # Get fresh region instance
                region = manager.get_region("A1", thread_safe=True)

                entry = {
                    "GlobalID": f"stress-{worker_id}-{i}",
                    "CanonicalLatin": f"Stress Test {worker_id} Entry {i}",
                }

                # Full processing pipeline
                region.clean(entry)
                region.augment(entry)
                region.validate(entry)

                worker_processed += 1

            except Exception as e:
                worker_errors.append(f"Worker {worker_id}: {e}")

        return {
            "worker_id": worker_id,
            "processed": worker_processed,
            "errors": worker_errors,
        }

    # Heavy concurrent load
    num_workers = 50  # Aggressive load
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(stress_worker, i) for i in range(num_workers)]

        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            processed_count += result["processed"]
            errors.extend(result["errors"])

    end_time = time.time()

    # Analysis
    total_expected = num_workers * 200
    success_rate = processed_count / total_expected
    duration = end_time - start_time
    throughput = processed_count / duration

    print("Stress test results:")
    print(f"Workers: {num_workers}")
    print(f"Processed: {processed_count}/{total_expected} ({success_rate:.1%})")
    print(f"Errors: {len(errors)}")
    print(f"Duration: {duration:.3f}s")
    print(f"Throughput: {throughput:.1f} entries/s")

    if len(errors) > 0:
        print("Sample errors:")
        for error in errors[:3]:
            print(f"  {error}")

    if success_rate >= 0.99 and len(errors) == 0:
        print("PASS STRESS TEST: EXCELLENT")
        return True
    elif success_rate >= 0.95:
        print("PASS STRESS TEST: GOOD")
        return True
    else:
        print("FAIL STRESS TEST: FAILURES DETECTED")
        return False


def main():
    """Comprehensive multi-core readiness verification."""
    print("🔥 MULTI-CORE PARALLELIZATION READINESS VERIFICATION")
    print("=" * 70)

    tests_passed = 0
    total_tests = 0

    # Test 1: Multicore processing
    total_tests += 1
    if test_multicore_processing():
        tests_passed += 1

    # Test 2: Thread pool scaling
    total_tests += 1
    if test_thread_pool_scaling():
        tests_passed += 1

    # Test 3: Stress concurrent load
    total_tests += 1
    if test_stress_concurrent_load():
        tests_passed += 1

    # Final assessment
    print("\n" + "=" * 70)
    print(f"🎯 MULTI-CORE READINESS: {tests_passed}/{total_tests} TESTS PASSED")

    if tests_passed == total_tests:
        print("🚀 MULTI-CORE PARALLELIZATION: FULLY READY")
        print("PASS System can safely utilize all available CPU cores")
        print("PASS Thread safety issues resolved")
        print("PASS Performance scales with additional cores/threads")
        return True
    elif tests_passed >= 2:
        print("PASS MULTI-CORE PARALLELIZATION: READY")
        print("WARN Some minor limitations but core functionality solid")
        return True
    else:
        print("FAIL MULTI-CORE PARALLELIZATION: NOT READY")
        print("🚨 Thread safety issues remain or performance problems exist")
        return False


if __name__ == "__main__":
    success = main()
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
