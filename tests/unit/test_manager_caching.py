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

# Migrated 2026-05-01 from `src.regions.manager` (legacy, 2851 LOC,
# imported by no production code) to `src.regions.manager_optimized`
# (the active V7 path). Both classes expose the same `get_region`,
# `_regions`, and `__init__(config_dir)` surface this test exercises.
from src.regions.manager_optimized import RegionManager


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
    manager.get_region("A2")
    print(f"Manager cache after A2: {list(manager._regions.keys())}")

    # Get A1 again
    region_a1_again = manager.get_region("A1")
    print(f"A1 again ID: {id(region_a1_again)}")
    print(f"Same as first A1: {region is region_a1_again}")


@pytest.mark.timeout(20)
def test_detect_region_async_context_uses_sync_path_only():
    """In a running event loop, detect_region must use ONLY the
    synchronous detection path — it must NOT also spawn a fire-and-forget
    ``create_task(_detect_region_uncached_async(...))`` whose result is
    discarded. That orphan task doubled the full detection work on every
    hot-path call (stage 2 runs detect_region for every entry from the
    async pipeline) and swallowed any exception it raised. Regression for
    the R38 audit finding.
    """
    import asyncio
    from unittest.mock import AsyncMock, patch

    manager = RegionManager(Path("./config"))
    entry = {
        "CanonicalLatin": "Euler, Leonhard",
        "OriginalScript": "Euler, Leonhard",
    }

    async def _run():
        # A fresh manager has an empty detection cache, so this call
        # reaches the real detection path. Spy on the async detector:
        # inside an event loop it must never be invoked.
        with patch.object(
            manager, "_detect_region_uncached_async", new=AsyncMock()
        ) as async_spy:
            result = manager.detect_region(entry)
            # Let any (erroneously) scheduled task run before asserting.
            await asyncio.sleep(0)
            return result, async_spy

    result, async_spy = asyncio.run(_run())
    assert result is not None
    async_spy.assert_not_called()


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


@pytest.mark.timeout(20)
def test_detect_region_never_uses_async_path():
    """detect_region must ALWAYS use the synchronous detection path —
    never asyncio.run() the async one — so the same entry isn't routed
    through different authority logic depending on event-loop context.

    Regression (R39): detect_region picked sync-vs-async by whether a loop
    was running; the sync path does cache-only authority while the async
    path does live _detect_by_external_authority, so the API (async) and
    CLI (sync) could detect the same entry differently at OFFLINE=0.
    """
    from unittest.mock import AsyncMock, patch

    manager = RegionManager(Path("./config"))  # fresh -> empty detection cache
    entry = {"CanonicalLatin": "Müller, Hans", "OriginalScript": "Müller, Hans"}
    with patch.object(
        manager, "_detect_region_uncached_async", new=AsyncMock()
    ) as async_spy:
        result = manager.detect_region(entry)
    assert result is not None
    async_spy.assert_not_called()
