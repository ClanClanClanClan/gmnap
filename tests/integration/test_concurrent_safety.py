import pytest

#!/usr/bin/env python3
"""
Test concurrent safety with realistic data.
"""

import sys
import threading
import time
import random
import os

sys.path.insert(0, "src")

from src.core.pipeline import GMNAPPipeline

# Realistic name data for different regions
ANGLO_FIRST_NAMES = [
    "John",
    "Mary",
    "James",
    "Patricia",
    "Robert",
    "Jennifer",
    "Michael",
    "Linda",
    "William",
    "Elizabeth",
    "David",
    "Barbara",
    "Richard",
    "Susan",
    "Joseph",
    "Jessica",
    "Thomas",
    "Sarah",
    "Charles",
    "Karen",
    "Christopher",
    "Nancy",
    "Daniel",
    "Betty",
    "Matthew",
    "Helen",
    "Anthony",
    "Sandra",
    "Mark",
    "Donna",
    "Donald",
    "Carol",
]

ANGLO_LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
]

WESTERN_EUROPE_NAMES = [
    ("Jean", "Dupont"),
    ("Marie", "Martin"),
    ("Pierre", "Bernard"),
    ("Francoise", "Petit"),
    ("Hans", "Müller"),
    ("Anna", "Schmidt"),
    ("Klaus", "Schneider"),
    ("Greta", "Fischer"),
    ("Giovanni", "Rossi"),
    ("Maria", "Russo"),
    ("Luigi", "Ferrari"),
    ("Francesca", "Bianchi"),
    ("Juan", "García"),
    ("Carmen", "Rodríguez"),
    ("José", "López"),
    ("María", "Martínez"),
]

LATIN_AMERICA_NAMES = [
    ("Carlos", "García López"),
    ("María", "Rodríguez Pérez"),
    ("José", "Martínez González"),
    ("Ana", "Hernández Díaz"),
    ("Luis", "Pérez Sánchez"),
    ("Laura", "González Ramírez"),
    ("Pedro", "da Silva"),
    ("Juliana", "dos Santos"),
    ("João", "Oliveira"),
    ("Ana", "Costa"),
]


def generate_realistic_entry(region_code, index):
    """Generate a realistic entry for the given region."""

    if region_code == "A1":
        # Anglo-sphere names
        first = random.choice(ANGLO_FIRST_NAMES)
        last = random.choice(ANGLO_LAST_NAMES)
        name = f"{last}, {first}"
        territory = random.choice(["US", "GB", "CA", "AU"])

    elif region_code == "A2":
        # Western Europe
        first, last = random.choice(WESTERN_EUROPE_NAMES)
        name = f"{last}, {first}"
        territory = random.choice(["FR", "DE", "IT", "ES"])

    elif region_code == "G1":
        # Latin America
        first, last = random.choice(LATIN_AMERICA_NAMES)
        name = f"{last}, {first}"
        territory = random.choice(["MX", "BR", "AR", "CO"])

    else:
        # Default Anglo names
        first = random.choice(ANGLO_FIRST_NAMES)
        last = random.choice(ANGLO_LAST_NAMES)
        name = f"{last}, {first}"
        territory = "US"

    # Add some variations to ensure uniqueness
    if random.random() < 0.3:
        name += f" {random.choice(['Jr.', 'Sr.', 'III', 'IV'])}"

    # Add birth year for more unique GlobalIDs
    birth_year = 1900 + random.randint(0, 120)

    return {
        "CanonicalLatin": name,
        "TerritoryCode": territory,
        "BirthYear": birth_year,
        "_thread_id": index,  # Track which thread created this
    }


@pytest.mark.timeout(15)
def test_concurrent_processing():
    """Test concurrent processing with realistic data."""
    print("=== Testing Concurrent Processing with Realistic Data ===\n")

    # Clean up old test database
    db_path = "concurrent_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    pipeline = GMNAPPipeline({"database_path": db_path})

    # Shared data structures
    results = {"success": [], "failed": []}
    results_lock = threading.Lock()

    def process_batch(thread_id, count, region_code):
        """Process a batch of entries in a thread."""
        thread_success = 0
        thread_failed = 0

        for i in range(count):
            entry = generate_realistic_entry(region_code, thread_id * 1000 + i)

            try:
                processed = pipeline.process_entry(entry)
                with results_lock:
                    results["success"].append(
                        {
                            "thread": thread_id,
                            "entry": processed["CanonicalLatin"],
                            "global_id": processed["GlobalID"],
                            "region": processed["RegionCode"],
                        }
                    )
                thread_success += 1

            except Exception as e:
                with results_lock:
                    results["failed"].append(
                        {
                            "thread": thread_id,
                            "entry": entry["CanonicalLatin"],
                            "error": str(e),
                        }
                    )
                thread_failed += 1

        print(
            f"Thread {thread_id} ({region_code}): {thread_success} success, {thread_failed} failed"
        )

    # Launch threads with different regions
    threads = []
    thread_configs = [
        (0, 20, "A1"),  # Anglo-sphere
        (1, 20, "A1"),  # Anglo-sphere
        (2, 20, "A2"),  # Western Europe
        (3, 20, "G1"),  # Latin America
        (4, 20, "A1"),  # Anglo-sphere
    ]

    start_time = time.time()

    for thread_id, count, region in thread_configs:
        thread = threading.Thread(target=process_batch, args=(thread_id, count, region))
        threads.append(thread)
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    elapsed = time.time() - start_time

    # Analyze results
    print(f"\n=== Results ===")
    print(
        f"Total processed: {len(results['success'])} success, {len(results['failed'])} failed"
    )
    print(f"Processing time: {elapsed:.2f}s")
    print(f"Throughput: {len(results['success']) / elapsed:.1f} entries/sec")

    # Check for GlobalID uniqueness
    global_ids = [r["global_id"] for r in results["success"]]
    unique_ids = set(global_ids)
    print(f"\nGlobalID uniqueness: {len(unique_ids)}/{len(global_ids)} unique")

    if len(unique_ids) < len(global_ids):
        # Find duplicates
        from collections import Counter

        id_counts = Counter(global_ids)
        duplicates = [(gid, count) for gid, count in id_counts.items() if count > 1]
        print(f"FAIL Found {len(duplicates)} duplicate GlobalIDs:")
        for gid, count in duplicates[:5]:  # Show first 5
            print(f"  {gid}: {count} occurrences")

    # Check database integrity
    stats = pipeline.database.get_stats()
    print(f"\nDatabase statistics:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Expected: {len(results['success'])}")

    if stats["total_entries"] == len(results["success"]):
        print("  PASS Database integrity: PASSED")
    else:
        print(
            f"  FAIL Database integrity: FAILED (missing {len(results['success']) - stats['total_entries']} entries)"
        )

    # Show region distribution
    print(f"\n  Entries by region:")
    for region, count in stats["regions"].items():
        print(f"    {region}: {count}")

    # Show some sample failures
    if results["failed"]:
        print(f"\nSample failures (first 5):")
        for failure in results["failed"][:5]:
            print(
                f"  Thread {failure['thread']}: {failure['entry']} -> {failure['error']}"
            )

    # Test thread safety of stats
    print(f"\nPipeline statistics (thread-safe):")
    pipeline_status = pipeline.get_status()
    print(f"  Processed: {pipeline_status['statistics']['processed']}")
    print(f"  Failed: {pipeline_status['statistics']['failed']}")
    print(f"  Persisted: {pipeline_status['statistics']['persisted']}")
    print(f"  Success rate: {pipeline_status['statistics']['success_rate']:.1f}%")

    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)

    return len(unique_ids) == len(global_ids) and stats["total_entries"] == len(
        results["success"]
    )


@pytest.mark.timeout(15)
def test_stress_concurrent():
    """Stress test with many threads."""
    print("\n=== Stress Testing Concurrent Processing ===\n")

    # Clean up old test database
    db_path = "stress_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    pipeline = GMNAPPipeline({"database_path": db_path})

    success_count = 0
    lock = threading.Lock()

    def process_entries(thread_id):
        nonlocal success_count
        for i in range(10):
            entry = generate_realistic_entry("A1", thread_id * 1000 + i)
            try:
                pipeline.process_entry(entry)
                with lock:
                    success_count += 1
            except:
                pass

    # Launch many threads
    num_threads = 20
    threads = []

    start_time = time.time()

    for i in range(num_threads):
        thread = threading.Thread(target=process_entries, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    elapsed = time.time() - start_time

    stats = pipeline.database.get_stats()

    print(f"Threads: {num_threads}")
    print(f"Successful operations: {success_count}")
    print(f"Database entries: {stats['total_entries']}")
    print(f"Time: {elapsed:.2f}s")
    print(f"Operations/sec: {success_count / elapsed:.1f}")

    if stats["total_entries"] == success_count:
        print("PASS Stress test: PASSED")
    else:
        print(
            f"FAIL Stress test: FAILED (expected {success_count}, got {stats['total_entries']})"
        )

    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    # Run tests
    basic_passed = test_concurrent_processing()
    print("\n" + "=" * 60)
    test_stress_concurrent()

    print("\n=== Summary ===")
    if basic_passed:
        print("PASS Concurrent safety test: PASSED")
        print(
            "The pipeline handles concurrent operations correctly with proper locking."
        )
    else:
        print("FAIL Concurrent safety test: FAILED")
        print("Issues detected in concurrent processing.")
