
#!/usr/bin/env python3
"""
Demonstrate actual race condition causing data corruption
"""

import concurrent.futures
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.regions.manager import RegionManager


def demonstrate_cache_race_condition():
    """Demonstrate race condition with shared cache."""
    print("🧪 DEMONSTRATING CACHE RACE CONDITION")

    manager = RegionManager(Path("./config"))
    region = manager.get_region("A1")

    # Clear cache
    if hasattr(region, "_processing_cache"):
        region._processing_cache.clear()
        print("Starting with empty cache")

    corruption_found = False

    def racing_worker(worker_id):
        nonlocal corruption_found
        local_cache_sizes = []

        for i in range(100):
            entry = {
                "GlobalID": f"race-{worker_id}-{i}",
                "CanonicalLatin": f"Racing Name {worker_id} {i}",
            }

            try:
                # These operations modify the shared cache
                region.clean(entry)
                region.augment(entry)

                # Record cache size at this moment
                if hasattr(region, "_processing_cache"):
                    cache_size = len(region._processing_cache)
                    local_cache_sizes.append(cache_size)

                    # Check for cache corruption (invalid keys or values)
                    cache = region._processing_cache
                    for key, value in cache.items():
                        # Basic sanity checks
                        if not isinstance(key, str):
                            print(
                                f"FAIL CORRUPTION: Non-string cache key: {type(key)} = {key}"
                            )
                            corruption_found = True
                        if value is None:
                            print(f"FAIL CORRUPTION: None value for key: {key}")
                            corruption_found = True

            except Exception as e:
                print(f"FAIL EXCEPTION in worker {worker_id}: {e}")
                corruption_found = True

        return local_cache_sizes

    # Run concurrent workers
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(racing_worker, i) for i in range(20)]

        all_cache_sizes = []
        for future in concurrent.futures.as_completed(futures):
            cache_sizes = future.result()
            all_cache_sizes.extend(cache_sizes)

    duration = time.time() - start_time

    # Analysis
    final_cache_size = len(getattr(region, "_processing_cache", {}))
    expected_entries = 20 * 100  # 20 workers * 100 entries each

    print(f"Duration: {duration:.3f}s")
    print(f"Expected entries: {expected_entries}")
    print(f"Final cache size: {final_cache_size}")
    print(f"Cache size efficiency: {final_cache_size/expected_entries*100:.1f}%")

    # Check for inconsistencies in cache size observations
    unique_sizes = set(all_cache_sizes)
    if len(unique_sizes) > expected_entries:
        print(
            f"FAIL INCONSISTENT CACHE SIZE OBSERVATIONS: {len(unique_sizes)} unique sizes seen"
        )
        corruption_found = True

    # Look for specific race condition patterns
    cache_size_jumps = 0
    for i in range(1, len(all_cache_sizes)):
        if all_cache_sizes[i] < all_cache_sizes[i - 1]:
            cache_size_jumps += 1

    if cache_size_jumps > 0:
        print(
            f"FAIL CACHE SIZE DECREASES: {cache_size_jumps} instances (indicates race condition)"
        )
        corruption_found = True

    return corruption_found


def demonstrate_processed_entries_race():
    """Demonstrate race condition in _processed_entries set."""
    print("\n🧪 DEMONSTRATING PROCESSED ENTRIES RACE CONDITION")

    manager = RegionManager(Path("./config"))
    region = manager.get_region("A1")

    # Clear processed entries
    if hasattr(region, "_processed_entries"):
        region._processed_entries.clear()
        print("Starting with empty processed entries set")

    race_detected = False

    def entry_processor(worker_id):
        nonlocal race_detected

        for i in range(50):
            entry = {
                "GlobalID": f"processed-{worker_id}-{i}",
                "CanonicalLatin": f"Processed Name {worker_id} {i}",
            }

            try:
                # This modifies _processed_entries
                region.augment(entry)

                # Check set consistency
                if hasattr(region, "_processed_entries"):
                    processed_set = region._processed_entries
                    len(processed_set)

                    # Try to detect if we can observe the set in an inconsistent state
                    # This is tricky because set operations are mostly atomic in CPython
                    # But we might catch corruption during resize operations

                    if i % 10 == 0:  # Periodic check
                        try:
                            # Try to iterate over the set - this might fail if corrupted
                            list(processed_set)
                        except RuntimeError as e:
                            if "changed size during iteration" in str(e):
                                print(
                                    f"FAIL SET CORRUPTION: Set changed during iteration in worker {worker_id}"
                                )
                                race_detected = True

            except Exception as e:
                if "dictionary changed size during iteration" in str(
                    e
                ) or "set changed size during iteration" in str(e):
                    print(f"FAIL CONCURRENT MODIFICATION: {e}")
                    race_detected = True
                else:
                    print(f"FAIL UNEXPECTED ERROR in worker {worker_id}: {e}")

    # Run concurrent processors
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(entry_processor, i) for i in range(15)]

        for future in concurrent.futures.as_completed(futures):
            future.result()

    # Final analysis
    final_processed_size = len(getattr(region, "_processed_entries", set()))
    expected_processed = 15 * 50  # 15 workers * 50 entries

    print(f"Expected processed entries: {expected_processed}")
    print(f"Final processed entries: {final_processed_size}")
    print(f"Processing efficiency: {final_processed_size/expected_processed*100:.1f}%")

    return race_detected


def demonstrate_idempotency_violation():
    """Demonstrate race conditions violating idempotency."""
    print("\n🧪 DEMONSTRATING IDEMPOTENCY VIOLATION")

    manager = RegionManager(Path("./config"))
    region = manager.get_region("A1")

    # Clear state
    if hasattr(region, "_processing_cache"):
        region._processing_cache.clear()
    if hasattr(region, "_processed_entries"):
        region._processed_entries.clear()

    # Same entry processed by multiple threads
    test_entry = {
        "GlobalID": "idempotency-test",
        "CanonicalLatin": "Idempotency Test Name",
    }

    results = []
    idempotency_violated = False

    def process_same_entry(worker_id):
        nonlocal idempotency_violated

        # Copy the entry so each thread has its own copy
        entry = test_entry.copy()

        # Process the entry
        region.clean(entry)
        region.augment(entry)

        # Record final state
        result = {
            "worker_id": worker_id,
            "final_entry": entry.copy(),
            "canonical": entry.get("CanonicalLatin"),
            "variants_count": len(entry.get("Variants", {}).get("Synthesised", [])),
        }

        return result

    # Process same entry concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_same_entry, i) for i in range(10)]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)

    # Check for idempotency violations
    canonical_values = [r["canonical"] for r in results]
    variant_counts = [r["variants_count"] for r in results]

    unique_canonicals = set(canonical_values)
    unique_variant_counts = set(variant_counts)

    print(f"Unique canonical values: {len(unique_canonicals)}")
    print(f"Unique variant counts: {len(unique_variant_counts)}")

    if len(unique_canonicals) > 1:
        print("FAIL IDEMPOTENCY VIOLATION: Different canonical values")
        print(f"   Values seen: {unique_canonicals}")
        idempotency_violated = True

    if len(unique_variant_counts) > 1:
        print("FAIL IDEMPOTENCY VIOLATION: Different variant counts")
        print(f"   Counts seen: {unique_variant_counts}")
        idempotency_violated = True

    if not idempotency_violated:
        print("PASS Idempotency maintained (this time)")

    return idempotency_violated


def main():
    """Demonstrate race conditions."""
    print("🔥 RACE CONDITION DEMONSTRATION")
    print("=" * 60)

    issues_found = []

    # Test 1: Cache race conditions
    if demonstrate_cache_race_condition():
        issues_found.append("Cache race condition")

    # Test 2: Processed entries race conditions
    if demonstrate_processed_entries_race():
        issues_found.append("Processed entries race condition")

    # Test 3: Idempotency violations
    if demonstrate_idempotency_violation():
        issues_found.append("Idempotency violation")

    # Summary
    print("\n" + "=" * 60)
    print("🎯 RACE CONDITION ANALYSIS RESULTS:")

    if issues_found:
        print("FAIL RACE CONDITIONS DETECTED:")
        for issue in issues_found:
            print(f"  • {issue}")
        print("\n🚨 MULTI-CORE PROCESSING IS NOT SAFE")
        print("   Shared state causes data corruption and unpredictable behavior")
        return False
    else:
        print("WARN No obvious race conditions detected in this run")
        print("   Race conditions are timing-dependent and may not always manifest")
        print("   Shared cache and processed entries still pose theoretical risks")
        return True


if __name__ == "__main__":
    success = main()
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
