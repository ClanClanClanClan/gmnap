"""
Hardcore concurrent access and race condition testing.

Tests data integrity under extreme concurrent load, race conditions,
and chaos engineering scenarios.

Migrated 2026-06-29 from the deleted ``src.core.pipeline_v6.GMNAPPipeline``
(file-based ``run(input_dir)``) to the V7 async pipeline
(``src.core.pipeline_v7.V7Pipeline.process_batch(entries)``). The
GlobalID / cache / database race tests never depended on the v6
pipeline — only ``TestChaosEngineering`` did, and it now feeds entry
dicts straight through ``process_batch`` instead of writing YAML and
calling the removed file-ingest path.
"""

import asyncio
import gc
import random
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from queue import Empty, Queue
from threading import Barrier
from unittest.mock import patch

import psutil
import pytest

from src.core.globalid import GlobalIDGenerator
from src.core.pipeline_v7 import PipelineMode, V7Pipeline
from src.core.unicode_handler import UnicodeNormalizer
from src.utils.cache import CacheManager
from src.utils.database import DatabaseManager


class TestConcurrentGlobalIDGeneration:
    """Test concurrent GlobalID generation for race conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GlobalIDGenerator()
        self.generator.clear()
        self.results = Queue()
        self.errors = Queue()

    # NOTE (2026-06-29 migration): two former sub-tests were RETIRED here
    # — ``test_concurrent_globalid_uniqueness`` and
    # ``test_concurrent_collision_handling_race_condition``. They asserted
    # V6 collision semantics: identical entries (same CanonicalNative +
    # BirthYear) were each force-assigned a sequential ``--N`` suffix.
    # The live V7 generator (``src/core/globalid.py``) only suffixes a
    # *true* collision — a different person (different hash input) that
    # happens to hash to the same base ID. Feeding it N identical entries
    # now correctly returns the SAME deterministic ID N times (identical
    # input -> identical GlobalID), so the "force a unique suffix per
    # duplicate" guarantee those tests checked no longer exists by design.
    # ``test_concurrent_memory_corruption`` below still covers concurrent
    # uniqueness for genuinely *distinct* entries.

    def test_concurrent_memory_corruption(self):
        """Test for memory corruption under concurrent access."""

        # This test looks for memory corruption by checking data integrity
        def memory_stress_worker(worker_id):
            """Worker that creates memory pressure."""
            local_generator = GlobalIDGenerator()

            # Generate many IDs quickly to stress memory
            for i in range(100):
                entry = {
                    "CanonicalNative": f"Worker{worker_id:03d}Test{i:03d}, Person",
                    "BirthYear": 1980 + i % 50,
                }

                try:
                    global_id = local_generator.generate(entry)

                    # Verify ID integrity
                    assert (
                        len(global_id) >= 22
                    ), f"Corrupted GlobalID length: {global_id}"
                    assert (
                        global_id.count("--") <= 1
                    ), f"Corrupted GlobalID format: {global_id}"

                    # Store for verification
                    self.results.put((worker_id, i, global_id))

                except Exception as e:
                    self.errors.put((worker_id, i, str(e)))

        # Run many workers to create memory pressure
        num_workers = 20
        threads = []

        for i in range(num_workers):
            thread = threading.Thread(target=memory_stress_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Collect and verify results
        results = []
        errors = []

        while not self.results.empty():
            try:
                results.append(self.results.get_nowait())
            except Empty:
                break

        while not self.errors.empty():
            try:
                errors.append(self.errors.get_nowait())
            except Empty:
                break

        # Verify no errors
        assert len(errors) == 0, f"Memory corruption errors: {errors[:5]}"

        # Verify expected number of results
        expected_results = num_workers * 100
        assert (
            len(results) == expected_results
        ), f"Lost results due to memory corruption: {len(results)}/{expected_results}"

        # Verify all GlobalIDs are unique
        global_ids = [result[2] for result in results]
        unique_ids = set(global_ids)
        assert len(unique_ids) == len(
            global_ids
        ), "Memory corruption caused duplicate GlobalIDs"


class TestConcurrentCacheAccess:
    """Test concurrent cache access for race conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / "cache"
        self.cache_dir.mkdir(parents=True)

        self.cache = CacheManager(cache_dir=self.cache_dir, max_size_gb=0.1, max_days=1)

        self.results = Queue()
        self.errors = Queue()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_cache_write_integrity(self):
        """Test cache write integrity under concurrent access."""

        def cache_write_worker(worker_id):
            """Worker that writes to cache concurrently."""
            try:
                for i in range(50):
                    key = f"worker_{worker_id}_item_{i}"
                    data = {
                        "worker_id": worker_id,
                        "item_id": i,
                        "data": f"test_data_{worker_id}_{i}",
                        "timestamp": time.time(),
                    }

                    # Write to cache
                    self.cache.put("test_service", key, data)

                    # Immediately read back to verify
                    read_data = self.cache.get("test_service", key)

                    if read_data != data:
                        self.errors.put(
                            (worker_id, i, "Data corruption", data, read_data)
                        )
                    else:
                        self.results.put((worker_id, i, "success"))

            except Exception as e:
                self.errors.put((worker_id, -1, str(e)))

        # Run concurrent writers
        num_workers = 10
        threads = []

        for i in range(num_workers):
            thread = threading.Thread(target=cache_write_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Collect results
        results = []
        errors = []

        while not self.results.empty():
            try:
                results.append(self.results.get_nowait())
            except Empty:
                break

        while not self.errors.empty():
            try:
                errors.append(self.errors.get_nowait())
            except Empty:
                break

        # Verify no errors
        assert len(errors) == 0, f"Cache corruption errors: {errors[:5]}"

        # Verify expected number of results
        expected_results = num_workers * 50
        assert (
            len(results) == expected_results
        ), f"Lost cache writes: {len(results)}/{expected_results}"

    def test_concurrent_cache_eviction_race(self):
        """Test cache eviction race conditions."""
        # Set very small cache size to force evictions
        small_cache = CacheManager(
            cache_dir=self.cache_dir / "small", max_size_gb=0.001, max_days=1  # 1MB
        )

        def cache_eviction_worker(worker_id):
            """Worker that creates cache pressure."""
            try:
                for i in range(100):
                    key = f"worker_{worker_id}_large_{i}"
                    # Create large data to force evictions
                    data = {"large_data": "x" * 1000}  # 1KB each

                    small_cache.put("test_service", key, data)

                    # Try to read some data back
                    read_data = small_cache.get("test_service", key)

                    if read_data is not None:
                        self.results.put((worker_id, i, "success"))
                    else:
                        # Eviction is expected, but should be clean
                        self.results.put((worker_id, i, "evicted"))

            except Exception as e:
                self.errors.put((worker_id, str(e)))

        # Run workers that create eviction pressure
        num_workers = 5
        threads = []

        for i in range(num_workers):
            thread = threading.Thread(target=cache_eviction_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Collect results
        results = []
        errors = []

        while not self.results.empty():
            try:
                results.append(self.results.get_nowait())
            except Empty:
                break

        while not self.errors.empty():
            try:
                errors.append(self.errors.get_nowait())
            except Empty:
                break

        # Verify no errors during eviction
        assert len(errors) == 0, f"Cache eviction errors: {errors}"

        # Verify some operations completed
        assert len(results) > 0, "No cache operations completed"

        # Cache should still be functional
        test_key = "eviction_test"
        test_data = {"test": "data"}
        small_cache.put("test_service", test_key, test_data)
        assert (
            small_cache.get("test_service", test_key) == test_data
        ), "Cache corrupted by eviction race"


class TestConcurrentDatabaseAccess:
    """Test concurrent database access for race conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"

        from src.utils.database import UtilsDatabaseConfig as DatabaseConfig

        config = DatabaseConfig(db_path=str(self.db_path))
        self.db = DatabaseManager(config)

        self.results = Queue()
        self.errors = Queue()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_database_writes(self):
        """Test concurrent database writes for race conditions."""

        def db_write_worker(worker_id):
            """Worker that writes to database concurrently."""
            try:
                # Create a separate connection for this worker
                from src.utils.database import UtilsDatabaseConfig as DatabaseConfig

                worker_config = DatabaseConfig(db_path=str(self.db_path))
                worker_db = DatabaseManager(worker_config)

                for i in range(50):
                    # Create test data for initial_stats table - using correct nested format
                    canonical_name = f"Test{worker_id:02d}_{i:03d}, Worker"
                    test_data = [
                        {
                            canonical_name: {
                                "GlobalID": f"WORKER{worker_id:02d}ITEM{i:03d}TEST",
                                "CanonicalLatin": canonical_name,
                                "CanonicalNative": canonical_name,
                                "BirthYear": 1980 + i,
                                "DeathYear": None,
                                "CountryCodes": ["US"],
                                "Confidence": 80.0,
                            }
                        }
                    ]

                    # Insert test data using the actual API
                    worker_db.insert_initial_stats(test_data)

                    # Verify the write by getting statistics
                    stats = worker_db.get_statistics()

                    if stats and stats.get("total_entries", 0) > 0:
                        self.results.put((worker_id, i, "success"))
                    else:
                        self.errors.put((worker_id, i, "verification_failed", stats))

            except Exception as e:
                self.errors.put((worker_id, -1, str(e)))

        # Run concurrent writers
        num_workers = 5  # Reduced for database test
        threads = []

        for i in range(num_workers):
            thread = threading.Thread(target=db_write_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Collect results
        results = []
        errors = []

        while not self.results.empty():
            try:
                results.append(self.results.get_nowait())
            except Empty:
                break

        while not self.errors.empty():
            try:
                errors.append(self.errors.get_nowait())
            except Empty:
                break

        # Verify no errors
        assert len(errors) == 0, f"Database race condition errors: {errors[:5]}"

        # Verify expected number of results
        expected_results = num_workers * 50
        assert (
            len(results) == expected_results
        ), f"Lost database writes: {len(results)}/{expected_results}"

        # Verify database integrity
        stats = self.db.get_statistics()
        total_records = stats.get("total_entries", 0)
        assert (
            total_records == expected_results
        ), f"Database integrity compromised: {total_records}/{expected_results}"

    def test_concurrent_database_deadlock_prevention(self):
        """Test database deadlock prevention."""
        deadlock_detected = threading.Event()

        def deadlock_worker(worker_id):
            """Worker that creates potential deadlock scenarios."""
            try:
                from src.utils.database import UtilsDatabaseConfig as DatabaseConfig

                worker_config = DatabaseConfig(db_path=str(self.db_path))
                worker_db = DatabaseManager(worker_config)

                # Create transactions that could deadlock
                for i in range(20):
                    try:
                        worker_db.connection.execute("BEGIN TRANSACTION")

                        # Update in different orders to create deadlock potential
                        if worker_id % 2 == 0:
                            worker_db.connection.execute(
                                "UPDATE test_deadlock SET value = ? WHERE id = 1",
                                (f"worker_{worker_id}_{i}",),
                            )
                            time.sleep(0.01)  # Small delay to increase deadlock chance
                            worker_db.connection.execute(
                                "UPDATE test_deadlock SET value = ? WHERE id = 2",
                                (f"worker_{worker_id}_{i}",),
                            )
                        else:
                            worker_db.connection.execute(
                                "UPDATE test_deadlock SET value = ? WHERE id = 2",
                                (f"worker_{worker_id}_{i}",),
                            )
                            time.sleep(0.01)  # Small delay to increase deadlock chance
                            worker_db.connection.execute(
                                "UPDATE test_deadlock SET value = ? WHERE id = 1",
                                (f"worker_{worker_id}_{i}",),
                            )

                        worker_db.connection.execute("COMMIT")
                        self.results.put((worker_id, i, "success"))

                    except Exception as e:
                        # Handle both SQLite and DuckDB transaction conflicts
                        error_msg = str(e).lower()
                        if any(
                            keyword in error_msg
                            for keyword in [
                                "database is locked",
                                "deadlock",
                                "conflict",
                                "transaction",
                                "concurrent",
                                "busy",
                            ]
                        ):
                            deadlock_detected.set()
                            try:
                                worker_db.connection.execute("ROLLBACK")
                            except:
                                pass  # Rollback might fail if transaction is already aborted
                            # Retry after brief delay
                            time.sleep(0.001)
                            continue
                        else:
                            raise

            except Exception as e:
                self.errors.put((worker_id, str(e)))

        # Create test table for deadlock testing
        self.db.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS test_deadlock (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """
        )

        # Initialize test data
        self.db.connection.execute(
            "INSERT OR REPLACE INTO test_deadlock (id, value) VALUES (1, 'initial')"
        )
        self.db.connection.execute(
            "INSERT OR REPLACE INTO test_deadlock (id, value) VALUES (2, 'initial')"
        )

        # Run workers that could cause deadlocks
        num_workers = 8
        threads = []

        for i in range(num_workers):
            thread = threading.Thread(target=deadlock_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Collect results
        results = []
        errors = []

        while not self.results.empty():
            try:
                results.append(self.results.get_nowait())
            except Empty:
                break

        while not self.errors.empty():
            try:
                errors.append(self.errors.get_nowait())
            except Empty:
                break

        # Verify no unhandled errors
        assert len(errors) == 0, f"Unhandled database errors: {errors}"

        # Verify operations completed (some may have been retried)
        assert len(results) > 0, "No database operations completed"

        # Database should still be functional
        test_result = self.db.connection.execute(
            "SELECT COUNT(*) FROM test_deadlock"
        ).fetchone()[0]
        assert test_result == 2, "Database corrupted by deadlock scenarios"


class TestChaosEngineering:
    """Chaos engineering tests for system resilience."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.failures_injected = []

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_random_failure_injection(self):
        """Test system resilience with random failure injection."""
        # Build entry dicts (V7 process_batch consumes a list of dicts
        # directly; the v6 YAML-file ingest path was removed).
        entries = [
            {
                "GlobalID": f"ABCDEFGHIJKLMNOPQR{i:04d}",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": f"Test{i:03d}, Person",
                "CanonicalNative": f"Test{i:03d}, Person",
                "BirthYear": 1950 + i,
                "CountryCodes": ["US"],
                "Confidence": 80,
            }
            for i in range(100)
        ]

        # Inject random failures

        def inject_random_failure(method_name, original_method):
            """Inject random failures into method calls."""

            def wrapper(*args, **kwargs):
                # 10% chance of failure
                if random.random() < 0.1:
                    self.failures_injected.append(method_name)
                    raise Exception(f"Chaos engineering failure in {method_name}")
                return original_method(*args, **kwargs)

            return wrapper

        # Patch a method the V7 pipeline exercises per entry
        # (UnicodeNormalizer.normalize is called in stage 1) to inject
        # failures, then drive the async batch.
        with patch(
            "src.core.unicode_handler.UnicodeNormalizer.normalize",
            side_effect=inject_random_failure(
                "unicode_normalize", UnicodeNormalizer.normalize
            ),
        ):
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)

            try:
                result = asyncio.run(pipeline.process_batch(entries))

                # Pipeline should handle failures gracefully and still
                # return a (possibly partial) list of processed entries.
                assert result is not None, "Pipeline failed to handle injected failures"
                assert isinstance(result, list), "process_batch must return a list"

                # System should still produce some results
                assert len(result) > 0, "No entries processed despite partial failures"

            except Exception as e:
                # Complete failure is acceptable if many failures were injected
                if len(self.failures_injected) > 50:  # More than 50% failure rate
                    assert (
                        "chaos" in str(e).lower() or "failure" in str(e).lower()
                    ), f"Unexpected failure type: {str(e)}"
                else:
                    pytest.fail(f"Pipeline failed with low failure rate: {str(e)}")

    def test_resource_exhaustion_scenarios(self):
        """Test system behavior under resource exhaustion."""

        # Test memory exhaustion
        def memory_exhaustion_worker():
            """Worker that consumes memory."""
            memory_hogs = []
            try:
                # Consume memory until near system limits
                process = psutil.Process()
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB

                while True:
                    # Allocate 10MB chunks
                    chunk = bytearray(10 * 1024 * 1024)  # 10MB
                    memory_hogs.append(chunk)

                    current_memory = process.memory_info().rss / 1024 / 1024  # MB

                    # Stop when we've consumed 500MB additional
                    if current_memory - initial_memory > 500:
                        break

            except MemoryError:
                # Expected when memory is exhausted
                pass
            finally:
                # Clean up
                del memory_hogs
                gc.collect()

        # Start memory pressure
        memory_thread = threading.Thread(target=memory_exhaustion_worker)
        memory_thread.start()

        try:
            # Run pipeline under memory pressure
            generator = GlobalIDGenerator()

            # Should handle memory pressure gracefully
            for i in range(100):
                entry = {"CanonicalNative": f"Test{i}, Person", "BirthYear": 1980}

                try:
                    global_id = generator.generate(entry)
                    assert (
                        global_id is not None
                    ), f"GlobalID generation failed under memory pressure: {i}"

                except MemoryError:
                    # Graceful degradation under memory pressure is acceptable
                    break
                except Exception as e:
                    # Other exceptions should be handled gracefully
                    assert (
                        "memory" in str(e).lower() or "resource" in str(e).lower()
                    ), f"Unexpected error under memory pressure: {str(e)}"

        finally:
            # Clean up memory pressure
            memory_thread.join(timeout=5)
            gc.collect()

    def test_network_partition_simulation(self):
        """Test behavior during network partition simulation."""

        # Simulate network failures for API calls
        def simulate_network_partition():
            """Simulate network connectivity issues."""
            failure_types = [
                "Connection timeout",
                "DNS resolution failed",
                "Connection refused",
                "Network unreachable",
                "SSL handshake failed",
            ]

            failure_type = random.choice(failure_types)
            raise Exception(f"Network partition: {failure_type}")

        # Mock API calls to simulate network issues. In QUICK/OFFLINE
        # mode the tier-0 fetchers are short-circuited, but patching the
        # canonical fetcher proves the pipeline still produces local
        # results even when any live authority call would explode.
        with patch(
            "src.authorities.tier0.openalex.OpenAlexFetcher.fetch",
            side_effect=simulate_network_partition,
        ):
            entries = [
                {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "UpdatedAt": "2025-01-01T00:00:00Z",
                    "CanonicalLatin": "Test, Person",
                    "CanonicalNative": "Test, Person",
                    "BirthYear": 1980,
                    "CountryCodes": ["US"],
                    "Confidence": 80,
                }
            ]

            pipeline = V7Pipeline(mode=PipelineMode.QUICK)

            try:
                result = asyncio.run(pipeline.process_batch(entries))

                # Pipeline should complete despite network issues
                assert result is not None, "Pipeline failed to handle network partition"

                # Should process local data even without network
                assert len(result) > 0, "No entries processed during network partition"

            except Exception as e:
                # Network failures should be handled gracefully
                assert (
                    "network" in str(e).lower() or "connection" in str(e).lower()
                ), f"Unexpected error during network partition: {str(e)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
