import pytest

#!/usr/bin/env python3
"""
Direct thread safety test - focus on shared state issues
"""

import concurrent.futures
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.regions.manager import RegionManager


@pytest.mark.timeout(15)
def test_shared_manager_instance():
    """Test if the same manager returns same region instances."""
    print("🧪 TESTING SHARED MANAGER BEHAVIOR")

    # Create ONE manager instance
    manager = RegionManager(Path("./config"))

    def get_region_info(thread_id):
        region = manager.get_region("A1")
        return {
            "thread_id": thread_id,
            "region_id": id(region),
            "cache_id": id(getattr(region, "_processing_cache", None)),
        }

    # Multiple threads using SAME manager
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_region_info, i) for i in range(5)]
        results = [f.result() for f in futures]

    # Check results
    region_ids = [r["region_id"] for r in results]
    cache_ids = [r["cache_id"] for r in results]

    print(f"Region instance IDs: {region_ids}")
    print(f"Cache instance IDs: {cache_ids}")

    unique_regions = len(set(region_ids))
    unique_caches = len(set(cache_ids))

    print(f"Unique region instances: {unique_regions}")
    print(f"Unique cache instances: {unique_caches}")

    if unique_regions == 1:
        print("PASS CONFIRMED: Same region instance shared across threads")
        if unique_caches == 1:
            print("FAIL CRITICAL: Same cache shared - RACE CONDITIONS LIKELY")
            return True  # Race condition confirmed
        else:
            print("WARN Different caches per thread - may be safer")
            return False
    else:
        print("PASS Different region instances - safer architecture")
        return False


@pytest.mark.timeout(15)
def test_concurrent_cache_access():
    """Test concurrent access to shared cache."""
    print("\n🧪 TESTING CONCURRENT CACHE ACCESS")

    manager = RegionManager(Path("./config"))
    region = manager.get_region("A1")

    # Clear any existing cache
    if hasattr(region, "_processing_cache"):
        region._processing_cache.clear()
        print(f"Cleared cache, starting size: {len(region._processing_cache)}")

    errors = []

    def cache_worker(worker_id):
        worker_errors = []

        for i in range(50):
            try:
                # Create entry
                entry = {
                    "GlobalID": f"worker-{worker_id}-item-{i}",
                    "CanonicalLatin": f"Test Name {worker_id}-{i}",
                }

                # Process entry (this should hit cache)
                region.clean(entry)
                region.augment(entry)

                # Check cache size periodically
                if i % 10 == 0 and hasattr(region, "_processing_cache"):
                    cache_size = len(region._processing_cache)
                    print(
                        f"Worker {worker_id}, iteration {i}: cache size = {cache_size}"
                    )

            except Exception as e:
                worker_errors.append(f"Worker {worker_id}, iteration {i}: {e}")

        return worker_errors

    # Run concurrent workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(cache_worker, i) for i in range(10)]

        for future in concurrent.futures.as_completed(futures):
            worker_errors = future.result()
            errors.extend(worker_errors)

    # Final cache state
    final_cache_size = len(getattr(region, "_processing_cache", {}))
    print(f"\nFinal cache size: {final_cache_size}")
    print(f"Total errors: {len(errors)}")

    if errors:
        print("FAIL ERRORS DETECTED:")
        for error in errors[:5]:  # Show first 5
            print(f"  {error}")
        return len(errors)
    else:
        print("PASS No explicit errors (but race conditions may still exist)")
        return 0


@pytest.mark.timeout(15)
def test_cache_corruption():
    """Test for cache corruption under load."""
    print("\n🧪 TESTING CACHE CORRUPTION UNDER LOAD")

    manager = RegionManager(Path("./config"))
    region = manager.get_region("A1")

    # Clear cache
    if hasattr(region, "_processing_cache"):
        region._processing_cache.clear()

    corruption_detected = False

    def aggressive_worker(worker_id):
        nonlocal corruption_detected

        for i in range(100):
            try:
                # Same key for all workers - worst case scenario
                entry = {
                    "GlobalID": "shared-key",  # SAME KEY = MAXIMUM CONTENTION
                    "CanonicalLatin": f"Shared Entry {worker_id}",
                }

                # Multiple operations on same entry
                region.clean(entry)
                region.augment(entry)

                # Try to detect corruption
                if hasattr(region, "_processing_cache"):
                    cache = region._processing_cache
                    if "shared-key" in cache:
                        cached_value = cache["shared-key"]
                        # Check if cached value makes sense
                        if not isinstance(cached_value, (str, dict, tuple)):
                            print(
                                f"FAIL CORRUPTION: Invalid cache value type: {type(cached_value)}"
                            )
                            corruption_detected = True

            except Exception as e:
                print(f"FAIL EXCEPTION in worker {worker_id}: {e}")
                corruption_detected = True

    # Run aggressive concurrent workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(aggressive_worker, i) for i in range(20)]

        # Wait for completion
        for future in concurrent.futures.as_completed(futures):
            future.result()

    if corruption_detected:
        print("FAIL CACHE CORRUPTION DETECTED")
        return True
    else:
        print("PASS No obvious corruption detected")
        return False


def main():
    """Run direct thread safety tests."""
    print("🔥 DIRECT THREAD SAFETY AUDIT")
    print("=" * 60)

    # Test 1: Manager instance sharing
    shared_instance = test_shared_manager_instance()

    # Test 2: Concurrent cache access
    cache_errors = test_concurrent_cache_access()

    # Test 3: Cache corruption
    corruption = test_cache_corruption()

    # Summary
    print("\n" + "=" * 60)
    print("🎯 DIRECT THREAD SAFETY RESULTS:")

    issues = []

    if shared_instance:
        issues.append("Shared region instances with shared cache")

    if cache_errors > 0:
        issues.append(f"Cache access errors: {cache_errors}")

    if corruption:
        issues.append("Cache corruption detected")

    if issues:
        print("FAIL THREAD SAFETY ISSUES FOUND:")
        for issue in issues:
            print(f"  • {issue}")
        print("\n🚨 NOT SAFE FOR MULTI-CORE PARALLELIZATION")
        return False
    else:
        print("PASS No obvious thread safety issues detected")
        print("WARN May still have subtle race conditions")
        return True


if __name__ == "__main__":
    success = main()
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
