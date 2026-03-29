import pytest

#!/usr/bin/env python3
"""
Test manager caching behavior to understand instance sharing
"""

import sys
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.regions.manager import RegionManager


@pytest.mark.timeout(15)
def test_single_manager_multiple_calls():
    """Test if one manager instance returns same region on multiple calls"""
    print("🧪 TESTING SINGLE MANAGER MULTIPLE CALLS")

    manager = RegionManager(Path("./config"))

    # Call get_region multiple times
    region1 = manager.get_region("A1")
    region2 = manager.get_region("A1")
    region3 = manager.get_region("A1")

    print(f"Region 1 ID: {id(region1)}")
    print(f"Region 2 ID: {id(region2)}")
    print(f"Region 3 ID: {id(region3)}")

    print(f"All same instance: {region1 is region2 is region3}")

    if region1:
        cache1 = getattr(region1, "_processing_cache", None)
        cache2 = getattr(region2, "_processing_cache", None)
        cache3 = getattr(region3, "_processing_cache", None)

        print(f"Cache 1 ID: {id(cache1)}")
        print(f"Cache 2 ID: {id(cache2)}")
        print(f"Cache 3 ID: {id(cache3)}")
        print(f"All same cache: {cache1 is cache2 is cache3}")


@pytest.mark.timeout(15)
def test_multiple_managers():
    """Test if different manager instances return different regions"""
    print("\n🧪 TESTING MULTIPLE MANAGERS")

    manager1 = RegionManager(Path("./config"))
    manager2 = RegionManager(Path("./config"))

    region1 = manager1.get_region("A1")
    region2 = manager2.get_region("A1")

    print(f"Manager 1 region ID: {id(region1)}")
    print(f"Manager 2 region ID: {id(region2)}")
    print(f"Same region instance: {region1 is region2}")

    if region1 and region2:
        cache1 = getattr(region1, "_processing_cache", None)
        cache2 = getattr(region2, "_processing_cache", None)

        print(f"Manager 1 cache ID: {id(cache1)}")
        print(f"Manager 2 cache ID: {id(cache2)}")
        print(f"Same cache instance: {cache1 is cache2}")


@pytest.mark.timeout(15)
def test_thread_local_manager():
    """Test if threads with same manager get same region"""
    print("\n🧪 TESTING THREAD LOCAL WITH SHARED MANAGER")

    manager = RegionManager(Path("./config"))  # SHARED manager
    results = {}

    def get_region_in_thread(thread_id):
        region = manager.get_region("A1")
        cache = getattr(region, "_processing_cache", None) if region else None
        results[thread_id] = {
            "region_id": id(region),
            "cache_id": id(cache) if cache is not None else None,
            "thread_id": threading.get_ident(),
        }

    threads = []
    for i in range(3):
        thread = threading.Thread(target=get_region_in_thread, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("Thread results:")
    for tid, result in results.items():
        print(
            f"Thread {tid}: region={result['region_id']}, cache={result['cache_id']}, native_thread={result['thread_id']}"
        )

    region_ids = [r["region_id"] for r in results.values()]
    cache_ids = [r["cache_id"] for r in results.values() if r["cache_id"] is not None]

    print(f"Unique regions: {len(set(region_ids))}")
    print(f"Unique caches: {len(set(cache_ids))}")


@pytest.mark.timeout(15)
def test_manager_caching_internals():
    """Look at manager's internal cache"""
    print("\n🧪 TESTING MANAGER INTERNAL CACHE")

    manager = RegionManager(Path("./config"))

    print(f"Manager cache before: {list(manager._regions.keys())}")

    # Get region
    region = manager.get_region("A1")

    print(f"Manager cache after A1: {list(manager._regions.keys())}")
    print(f"A1 in cache: {'A1' in manager._regions}")
    print(f"Cached A1 ID: {id(manager._regions.get('A1'))}")
    print(f"Returned A1 ID: {id(region)}")
    print(f"Same instance: {manager._regions.get('A1') is region}")

    # Get different region
    region_a2 = manager.get_region("A2")
    print(f"Manager cache after A2: {list(manager._regions.keys())}")

    # Get A1 again
    region_a1_again = manager.get_region("A1")
    print(f"A1 again ID: {id(region_a1_again)}")
    print(f"Same as first A1: {region is region_a1_again}")


def main():
    """Run all manager caching tests"""
    print("🔥 MANAGER CACHING ANALYSIS")
    print("=" * 60)

    test_single_manager_multiple_calls()
    test_multiple_managers()
    test_thread_local_manager()
    test_manager_caching_internals()


if __name__ == "__main__":
    main()
