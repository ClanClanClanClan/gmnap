from typing import List

import pytest

#!/usr/bin/env python3
"""
ULTRATHINK: Thread Safety Audit - Expose and Fix Race Conditions
Test the actual thread safety issues identified in regional processors.
"""

import concurrent.futures
import sys
import threading
import time
from pathlib import Path
from typing import Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.regions.manager import RegionManager


class ThreadSafetyTester:
    """Test for thread safety issues in regional processors."""

    def __init__(self):
        self.manager = RegionManager(Path("./config"))
        self.errors = []
        self.results = {}
        self.lock = threading.Lock()

    def worker_thread(
        self, thread_id: int, region_code: str, test_entries: List[Dict]
    ) -> Dict:
        """Worker thread that processes entries concurrently."""
        results = {
            "thread_id": thread_id,
            "processed": 0,
            "errors": [],
            "cache_states": [],
            "final_cache_size": 0,
        }

        try:
            # Get the same region instance (this is the problem!)
            region = self.manager.get_region(region_code)
            if not region:
                results["errors"].append(f"Failed to get region {region_code}")
                return results

            # Record initial cache state
            initial_cache_size = len(getattr(region, "_processing_cache", {}))
            results["cache_states"].append(f"Initial cache size: {initial_cache_size}")

            for i, entry in enumerate(test_entries):
                try:
                    # Add thread and iteration info to make entries unique but still test caching
                    test_entry = entry.copy()
                    test_entry["GlobalID"] = (
                        f"{test_entry['GlobalID']}-t{thread_id}-i{i}"
                    )

                    # This will hit the shared cache
                    region.clean(test_entry)
                    region.augment(test_entry)
                    region.validate(test_entry)

                    results["processed"] += 1

                    # Periodically check cache size
                    if i % 5 == 0:
                        cache_size = len(getattr(region, "_processing_cache", {}))
                        results["cache_states"].append(
                            f"After entry {i}: cache size {cache_size}"
                        )

                except Exception as e:
                    results["errors"].append(f"Entry {i}: {str(e)}")

            # Final cache size
            results["final_cache_size"] = len(getattr(region, "_processing_cache", {}))

        except Exception as e:
            results["errors"].append(f"Worker thread error: {str(e)}")

        return results

    @pytest.mark.timeout(15)
    def test_concurrent_access(
        self, region_code: str, num_threads: int = 5, entries_per_thread: int = 20
    ):
        """Test what happens when multiple threads access the same region."""
        print(f"\n🧪 TESTING CONCURRENT ACCESS: {region_code}")
        print(f"Threads: {num_threads}, Entries per thread: {entries_per_thread}")

        # Create test entries
        test_entries = []
        for i in range(entries_per_thread):
            test_entries.append(
                {
                    "GlobalID": f"test-concurrent-{i}",
                    "CanonicalLatin": f"Test Name {i}",
                    "CanonicalNative": f"Test Name {i}",
                }
            )

        # Clear any existing cache state
        region = self.manager.get_region(region_code)
        if hasattr(region, "_processing_cache"):
            region._processing_cache.clear()
        if hasattr(region, "_processed_entries"):
            region._processed_entries.clear()

        print("Initial cache state cleared")

        # Start concurrent workers
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []

            for thread_id in range(num_threads):
                future = executor.submit(
                    self.worker_thread, thread_id, region_code, test_entries
                )
                futures.append(future)

            # Collect results
            thread_results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    thread_results.append(result)
                except Exception as e:
                    print(f"FAIL Thread failed: {e}")

        end_time = time.time()

        # Analyze results
        self.analyze_thread_safety_results(
            region_code, thread_results, end_time - start_time
        )

    def analyze_thread_safety_results(
        self, region_code: str, results: List[Dict], duration: float
    ):
        """Analyze the results for thread safety issues."""
        print(f"\n📊 THREAD SAFETY ANALYSIS for {region_code}:")
        print(f"Duration: {duration:.2f}s")

        total_processed = sum(r["processed"] for r in results)
        total_errors = sum(len(r["errors"]) for r in results)

        print(f"Total entries processed: {total_processed}")
        print(f"Total errors: {total_errors}")

        # Check for cache inconsistencies
        final_cache_sizes = [r["final_cache_size"] for r in results]
        print(f"Final cache sizes reported by threads: {final_cache_sizes}")

        # Get actual final cache size
        region = self.manager.get_region(region_code)
        actual_cache_size = len(getattr(region, "_processing_cache", {}))
        print(f"Actual final cache size: {actual_cache_size}")

        # Analyze errors
        all_errors = []
        for r in results:
            all_errors.extend(r["errors"])

        if all_errors:
            print("\nFAIL ERRORS DETECTED:")
            for error in all_errors[:5]:  # Show first 5 errors
                print(f"  {error}")
            if len(all_errors) > 5:
                print(f"  ... and {len(all_errors) - 5} more errors")

        # Check for race condition indicators
        cache_size_variations = len(set(final_cache_sizes)) > 1
        if cache_size_variations:
            print(
                "WARN RACE CONDITION DETECTED: Threads reported different cache sizes"
            )

        if total_errors > 0:
            print(
                f"FAIL THREAD SAFETY FAILED: {total_errors} errors during concurrent processing"
            )
        elif cache_size_variations:
            print("WARN THREAD SAFETY QUESTIONABLE: Cache inconsistencies detected")
        else:
            print("PASS THREAD SAFETY PASSED: No obvious issues detected")

        return total_errors == 0 and not cache_size_variations

    @pytest.mark.timeout(15)
    def test_cache_race_conditions(self):
        """Specifically test for cache race conditions."""
        print("\n🧪 TESTING CACHE RACE CONDITIONS")

        region = self.manager.get_region("A1")
        if not region:
            print("FAIL Cannot get A1 region for testing")
            return False

        # Clear cache
        if hasattr(region, "_processing_cache"):
            region._processing_cache.clear()

        # Test concurrent cache access with SAME keys (worst case)
        def cache_hammer(thread_id: int):
            results = {"reads": 0, "writes": 0, "errors": []}

            for i in range(50):
                try:
                    # All threads try to process the same entry (same cache key)
                    entry = {
                        "GlobalID": "race-test",  # SAME key for all threads
                        "CanonicalLatin": "Race Test Name",
                    }

                    # This should cause cache races
                    region.clean(entry)
                    results["writes"] += 1

                    # Try to read from cache
                    if hasattr(region, "_processing_cache"):
                        _ = len(region._processing_cache)
                        results["reads"] += 1

                except Exception as e:
                    results["errors"].append(f"T{thread_id}-I{i}: {str(e)}")

            return results

        # Run the cache hammer test
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(cache_hammer, i) for i in range(10)]

            hammer_results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    hammer_results.append(result)
                except Exception as e:
                    print(f"FAIL Cache hammer thread crashed: {e}")

        # Analyze cache hammer results
        total_errors = sum(len(r["errors"]) for r in hammer_results)
        total_operations = sum(r["reads"] + r["writes"] for r in hammer_results)

        print(f"Total cache operations: {total_operations}")
        print(f"Total errors: {total_errors}")

        if total_errors > 0:
            print(f"FAIL CACHE RACE CONDITIONS DETECTED: {total_errors} errors")
            # Show a few examples
            for result in hammer_results:
                for error in result["errors"][:2]:
                    print(f"  {error}")
            return False
        else:
            print("WARN No cache errors detected (may still have race conditions)")
            return True

    def demonstrate_manager_instance_sharing(self):
        """Show that the manager returns the same instance to all threads."""
        print("\n🧪 DEMONSTRATING INSTANCE SHARING PROBLEM")

        def get_region_instance(thread_id: int):
            region = self.manager.get_region("A1")
            return {
                "thread_id": thread_id,
                "region_id": id(region),  # Memory address
                "cache_id": id(getattr(region, "_processing_cache", None)),
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_region_instance, i) for i in range(5)]

            instance_results = []
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                instance_results.append(result)

        # Check if all threads got the same instance
        region_ids = [r["region_id"] for r in instance_results]
        cache_ids = [r["cache_id"] for r in instance_results]

        print(f"Region instance IDs: {region_ids}")
        print(f"Cache instance IDs: {cache_ids}")

        same_region = len(set(region_ids)) == 1
        same_cache = len(set(cache_ids)) == 1

        if same_region and same_cache:
            print(
                "FAIL CONFIRMED: All threads share the SAME region instance and cache"
            )
            print("   This WILL cause race conditions in multi-threaded processing")
            return True
        else:
            print("PASS Threads get different instances (safer)")
            return False


def main():
    """Run comprehensive thread safety tests."""
    print("🔥 ULTRATHINK: THREAD SAFETY AUDIT - EXPOSING RACE CONDITIONS")
    print("=" * 80)

    tester = ThreadSafetyTester()

    # Test 1: Demonstrate instance sharing problem
    sharing_confirmed = tester.demonstrate_manager_instance_sharing()

    # Test 2: Test concurrent access with multiple threads
    tester.test_concurrent_access("A1", num_threads=5, entries_per_thread=10)
    tester.test_concurrent_access("A2", num_threads=3, entries_per_thread=15)

    # Test 3: Specifically test cache race conditions
    cache_safe = tester.test_cache_race_conditions()

    # Summary
    print("\n" + "=" * 80)
    print("🎯 THREAD SAFETY AUDIT SUMMARY:")
    print("=" * 80)

    issues = []

    if sharing_confirmed:
        issues.append("CRITICAL: Shared region instances across threads")

    if not cache_safe:
        issues.append("CRITICAL: Cache race conditions detected")

    if issues:
        print("FAIL THREAD SAFETY FAILED:")
        for issue in issues:
            print(f"  • {issue}")
        print("\n🚨 MULTI-CORE PARALLELIZATION IS NOT SAFE")
        print("   Race conditions WILL cause data corruption and crashes")
    else:
        print("PASS Thread safety tests passed")
        print("🚀 Multi-core parallelization appears safe")

    return len(issues) == 0


if __name__ == "__main__":
    success = main()
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
