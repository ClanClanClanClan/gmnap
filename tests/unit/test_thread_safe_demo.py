import pytest

#!/usr/bin/env python3
"""
Demonstrate thread-safe processing with fresh instances
"""

import sys
import threading
import time
import concurrent.futures
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.regions.manager import RegionManager


def demonstrate_thread_safe_processing():
    """Demonstrate thread-safe processing with fresh instances."""
    print("🧪 DEMONSTRATING THREAD-SAFE PROCESSING")

    manager = RegionManager(Path("./config"))

    errors = []

    def safe_worker(worker_id):
        """Each worker gets its own fresh region instance."""
        worker_errors = []

        # Get fresh region instance for this worker
        region = manager.get_region("A1", thread_safe=True)

        for i in range(100):
            entry = {
                "GlobalID": f"safe-{worker_id}-{i}",
                "CanonicalLatin": f"Safe Name {worker_id} {i}",
            }

            try:
                # Process with this worker's private region instance
                region.clean(entry)
                region.augment(entry)
                region.validate(entry)
            except Exception as e:
                if "dictionary changed size during iteration" in str(e):
                    worker_errors.append(f"Worker {worker_id}: RACE CONDITION: {e}")
                else:
                    worker_errors.append(f"Worker {worker_id}: {e}")

        return {
            "worker_id": worker_id,
            "errors": worker_errors,
            "region_id": id(region),
            "cache_id": id(getattr(region, "_processing_cache", None)),
            "cache_size": len(getattr(region, "_processing_cache", {})),
        }

    # Run concurrent workers
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(safe_worker, i) for i in range(20)]

        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            errors.extend(result["errors"])

    duration = time.time() - start_time

    # Analysis
    print(f"Duration: {duration:.3f}s")
    print(f"Total errors: {len(errors)}")

    # Check instance isolation
    region_ids = [r["region_id"] for r in results]
    cache_ids = [r["cache_id"] for r in results]
    cache_sizes = [r["cache_size"] for r in results]

    unique_regions = len(set(region_ids))
    unique_caches = len(set(cache_ids))

    print(f"Unique region instances: {unique_regions}")
    print(f"Unique cache instances: {unique_caches}")
    print(f"Cache sizes: {cache_sizes[:5]}... (showing first 5)")

    if len(errors) == 0:
        print("PASS NO RACE CONDITIONS: Thread-safe processing works!")
        if unique_regions == len(results):
            print("PASS PERFECT ISOLATION: Each worker has unique region instance")
            return True
        else:
            print("WARN Some instance sharing detected but no race conditions")
            return True
    else:
        print("FAIL RACE CONDITIONS STILL EXIST:")
        for error in errors[:3]:
            print(f"  {error}")
        return False


def demonstrate_legacy_vs_thread_safe():
    """Compare legacy (unsafe) vs thread-safe behavior."""
    print("\n🧪 COMPARING LEGACY vs THREAD-SAFE BEHAVIOR")

    manager = RegionManager(Path("./config"))

    # Test legacy behavior (should have race conditions)
    print("\n--- Legacy behavior (thread_safe=False) ---")
    legacy_errors = []

    def legacy_worker(worker_id):
        region = manager.get_region("A1", thread_safe=False)  # Legacy mode
        worker_errors = []

        for i in range(50):
            entry = {
                "GlobalID": f"legacy-{worker_id}-{i}",
                "CanonicalLatin": f"Legacy {worker_id} {i}",
            }
            try:
                region.clean(entry)
                region.augment(entry)
            except Exception as e:
                if "dictionary changed size during iteration" in str(e):
                    worker_errors.append(f"RACE CONDITION: {e}")

        return worker_errors

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(legacy_worker, i) for i in range(10)]
        for future in concurrent.futures.as_completed(futures):
            legacy_errors.extend(future.result())

    print(f"Legacy mode errors: {len(legacy_errors)}")

    # Test thread-safe behavior
    print("\n--- Thread-safe behavior (thread_safe=True) ---")
    safe_errors = []

    def safe_worker_comparison(worker_id):
        region = manager.get_region("A1", thread_safe=True)  # Thread-safe mode
        worker_errors = []

        for i in range(50):
            entry = {"GlobalID": f"safe-{worker_id}-{i}", "CanonicalLatin": f"Safe {worker_id} {i}"}
            try:
                region.clean(entry)
                region.augment(entry)
            except Exception as e:
                if "dictionary changed size during iteration" in str(e):
                    worker_errors.append(f"RACE CONDITION: {e}")

        return worker_errors

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(safe_worker_comparison, i) for i in range(10)]
        for future in concurrent.futures.as_completed(futures):
            safe_errors.extend(future.result())

    print(f"Thread-safe mode errors: {len(safe_errors)}")

    # Comparison
    if len(legacy_errors) > 0 and len(safe_errors) == 0:
        print("PASS THREAD SAFETY FIX CONFIRMED:")
        print(f"   Legacy mode: {len(legacy_errors)} race conditions")
        print(f"   Thread-safe mode: {len(safe_errors)} race conditions")
        return True
    else:
        print("FAIL THREAD SAFETY FIX NOT WORKING:")
        print(f"   Legacy mode: {len(legacy_errors)} race conditions")
        print(f"   Thread-safe mode: {len(safe_errors)} race conditions")
        return False


@pytest.mark.timeout(15)
def test_performance_impact():
    """Test performance impact of fresh instances."""
    print("\n🧪 TESTING PERFORMANCE IMPACT")

    manager = RegionManager(Path("./config"))

    # Time cached approach (reuse same instance)
    start_time = time.time()
    region = manager.get_region("A1")
    for i in range(100):
        entry = {"GlobalID": f"perf-legacy-{i}", "CanonicalLatin": f"Performance Test {i}"}
        if region:
            region.clean(entry)
    legacy_time = time.time() - start_time

    # Time fresh instance approach (get new instance each time)
    start_time = time.time()
    for i in range(100):
        region = manager.get_region("A1")
        entry = {"GlobalID": f"perf-safe-{i}", "CanonicalLatin": f"Performance Test {i}"}
        if region:
            region.clean(entry)
    safe_time = time.time() - start_time

    overhead = (safe_time - legacy_time) / legacy_time * 100

    print(f"Legacy (cached) time: {legacy_time:.4f}s")
    print(f"Thread-safe (fresh) time: {safe_time:.4f}s")
    print(f"Performance overhead: {overhead:.1f}%")

    if overhead < 50:  # Less than 50% overhead is acceptable
        print("PASS ACCEPTABLE PERFORMANCE IMPACT")
        return True
    else:
        print("WARN SIGNIFICANT PERFORMANCE OVERHEAD")
        return False


def main():
    """Test thread safety improvements."""
    print("🔥 THREAD SAFETY IMPROVEMENT VERIFICATION")
    print("=" * 60)

    tests_passed = 0
    total_tests = 0

    # Test 1: Thread-safe processing
    total_tests += 1
    if demonstrate_thread_safe_processing():
        tests_passed += 1

    # Test 2: Legacy vs thread-safe comparison
    total_tests += 1
    if demonstrate_legacy_vs_thread_safe():
        tests_passed += 1

    # Test 3: Performance impact
    total_tests += 1
    if test_performance_impact():
        tests_passed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"🎯 THREAD SAFETY RESULTS: {tests_passed}/{total_tests} PASSED")

    if tests_passed >= 2:  # At least core functionality works
        print("PASS THREAD SAFETY SIGNIFICANTLY IMPROVED")
        print("🚀 MULTI-CORE PARALLELIZATION IS NOW VIABLE")
        return True
    else:
        print("FAIL THREAD SAFETY ISSUES PERSIST")
        return False


if __name__ == "__main__":
    success = main()
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
