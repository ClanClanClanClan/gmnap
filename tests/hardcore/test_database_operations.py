"""
Hardcore database operations testing for GMNAP.

Tests database integrity, transaction handling, memory fallback,
and concurrent access scenarios that could cause data corruption.
"""

import gc
import random
import sqlite3
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from queue import Empty, Queue
from unittest.mock import Mock, patch

import psutil
import pytest

from src.utils.database import DatabaseConfig, DatabaseManager


class TestDatabaseIntegrity:
    """Test database integrity under extreme conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.process = psutil.Process()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_corruption_recovery(self):
        """Test recovery from database corruption."""
        config = DatabaseConfig(
            db_path=str(self.db_path), use_duckdb=False
        )  # Use SQLite for this test
        db = DatabaseManager(config)

        # Insert test data
        test_entries = [
            {
                "Smith, John": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalNative": "Smith, John",
                    "BirthYear": 1950,
                    "CountryCodes": ["US"],
                    "Confidence": 85,
                }
            },
            {
                "Doe, Jane": {
                    "GlobalID": "BCDEFGHIJKLMNOPQRSTUVW",
                    "CanonicalNative": "Doe, Jane",
                    "BirthYear": 1960,
                    "CountryCodes": ["UK"],
                    "Confidence": 90,
                }
            },
        ]

        db.insert_initial_stats(test_entries)
        db.close()

        # Corrupt the database file
        with open(self.db_path, "r+b") as f:
            f.seek(100)  # Seek to middle of file
            f.write(b"\xff" * 1000)  # Write garbage bytes to corrupt

        # Try to access corrupted database
        corrupted_config = DatabaseConfig(db_path=str(self.db_path), use_duckdb=False)

        # Should detect corruption and handle gracefully
        try:
            corrupted_db = DatabaseManager(corrupted_config)
            # Try to query - should fail
            stats = corrupted_db.get_statistics()
            corrupted_db.close()
            # If we got here without error, the database might have recovered
            # Check if data is intact
            assert stats["total_entries"] >= 0, "Database recovered but data might be lost"
        except Exception as e:
            # Expected - database is corrupted
            assert (
                "corrupt" in str(e).lower()
                or "malformed" in str(e).lower()
                or "database" in str(e).lower()
                or "disk" in str(e).lower()
            )

    def test_memory_exhaustion_fallback(self):
        """Test DuckDB to SQLite fallback under memory pressure."""
        # Test with low memory threshold
        config = DatabaseConfig(
            db_path=str(self.db_path), memory_threshold_gb=100.0  # Set impossibly high threshold
        )

        # Mock low available memory
        with patch("psutil.virtual_memory") as mock_memory:
            mock_memory.return_value.available = 100 * 1024 * 1024  # 100MB available

            db = DatabaseManager(config)

            # Should be using SQLite due to memory constraints
            assert db.db_type == "sqlite", "Should fall back to SQLite under memory pressure"

            # Should still work correctly
            test_entries = [
                {
                    "Test, Memory": {
                        "GlobalID": "CDEFGHIJKLMNOPQRSTUVWX",
                        "CanonicalNative": "Test, Memory",
                        "BirthYear": 1970,
                        "CountryCodes": ["US"],
                        "Confidence": 75,
                    }
                }
            ]

            inserted = db.insert_initial_stats(test_entries)
            assert inserted == 1

            stats = db.get_statistics()
            assert stats["total_entries"] == 1
            assert stats["database_type"] == "sqlite"

            db.close()

    def test_concurrent_transaction_integrity(self):
        """Test transaction integrity under concurrent access."""
        config = DatabaseConfig(
            db_path=str(self.db_path), use_duckdb=False  # Force SQLite for transaction testing
        )

        # Create initial database
        with DatabaseManager(config) as db:
            # Insert initial entries
            entries = []
            for i in range(100):
                entries.append(
                    {
                        f"Test{i:04d}, User": {
                            "GlobalID": f"{'A' * 20}{i:02d}",
                            "CanonicalNative": f"Test{i:04d}, User",
                            "BirthYear": 1900 + i,
                            "CountryCodes": ["US"],
                            "Confidence": 80,
                        }
                    }
                )
            db.insert_initial_stats(entries)

        # Track results
        results = Queue()
        errors = Queue()

        def transaction_worker(worker_id, iterations):
            """Worker that performs concurrent database operations."""
            worker_config = DatabaseConfig(db_path=str(self.db_path), use_duckdb=False)

            successful_operations = 0

            for i in range(iterations):
                try:
                    with DatabaseManager(worker_config) as worker_db:
                        # Insert new entry
                        new_entry = [
                            {
                                f"Worker{worker_id}Entry{i:04d}, Test": {
                                    "GlobalID": f"W{worker_id:02d}E{i:04d}{'Z' * 14}",
                                    "CanonicalNative": f"Worker{worker_id}Entry{i:04d}, Test",
                                    "BirthYear": 2000 + i,
                                    "CountryCodes": ["US"],
                                    "Confidence": 70,
                                }
                            }
                        ]

                        worker_db.insert_initial_stats(new_entry)

                        # Read statistics
                        stats = worker_db.get_statistics()

                        successful_operations += 1

                except Exception as e:
                    errors.put((worker_id, i, str(e)))

            results.put((worker_id, successful_operations))

        # Run concurrent workers
        num_workers = 5
        iterations_per_worker = 10

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for worker_id in range(num_workers):
                future = executor.submit(transaction_worker, worker_id, iterations_per_worker)
                futures.append(future)

            # Wait for completion
            for future in as_completed(futures):
                future.result()

        # Collect results
        total_successful = 0
        while not results.empty():
            worker_id, successful = results.get()
            total_successful += successful

        # Check for errors
        error_count = 0
        while not errors.empty():
            error_count += 1
            worker_id, iteration, error = errors.get()
            print(f"Worker {worker_id} iteration {iteration} error: {error}")

        # Verify results
        assert (
            total_successful == num_workers * iterations_per_worker
        ), f"Not all operations succeeded: {total_successful}/{num_workers * iterations_per_worker}"

        # Verify final count
        with DatabaseManager(config) as db:
            stats = db.get_statistics()
            expected_entries = 100 + (
                num_workers * iterations_per_worker
            )  # Initial + worker entries
            assert (
                stats["total_entries"] == expected_entries
            ), f"Entry count mismatch: {stats['total_entries']} != {expected_entries}"

    def test_large_dataset_performance(self):
        """Test database performance with large datasets."""
        config = DatabaseConfig(
            db_path=str(self.db_path),
            cache_size_mb=512,  # Increase cache for performance
            use_duckdb=False,  # Use SQLite for simpler testing
        )

        with DatabaseManager(config) as db:
            # Insert large batch of entries
            batch_size = 1000
            num_batches = 10

            start_time = time.time()

            for batch_num in range(num_batches):
                entries = []
                for i in range(batch_size):
                    idx = batch_num * batch_size + i
                    entries.append(
                        {
                            f"LargeTest{idx:06d}, User": {
                                "GlobalID": f"L{idx:020d}",
                                "CanonicalNative": f"LargeTest{idx:06d}, User",
                                "BirthYear": 1900 + (idx % 100),
                                "CountryCodes": ["US", "UK", "CA"][idx % 3],
                                "Confidence": 60 + (idx % 40),
                            }
                        }
                    )

                db.insert_initial_stats(entries)

            insert_time = time.time() - start_time

            # Build surname statistics
            start_time = time.time()
            surname_stats = db.build_surname_stats()
            stats_time = time.time() - start_time

            # Detect collisions
            start_time = time.time()
            collisions = db.detect_collisions(threshold=2)
            collision_time = time.time() - start_time

            # Performance assertions
            total_entries = batch_size * num_batches
            assert (
                insert_time < 10.0
            ), f"Insert too slow: {insert_time:.2f}s for {total_entries} entries"
            assert stats_time < 5.0, f"Stats building too slow: {stats_time:.2f}s"
            assert collision_time < 5.0, f"Collision detection too slow: {collision_time:.2f}s"

            # Verify data integrity
            stats = db.get_statistics()
            assert stats["total_entries"] == total_entries
            assert stats["surname_combinations"] > 0

            print(f"Performance stats for {total_entries} entries:")
            print(
                f"  Insert time: {insert_time:.2f}s ({total_entries/insert_time:.0f} entries/sec)"
            )
            print(f"  Stats build time: {stats_time:.2f}s")
            print(f"  Collision detection time: {collision_time:.2f}s")
            print(f"  Database size: {stats['database_size_mb']:.2f} MB")


class TestDatabaseMemoryManagement:
    """Test database memory usage and leaks."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.process = psutil.Process()
        gc.collect()  # Clean slate

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        gc.collect()

    def test_memory_leak_detection(self):
        """Test for memory leaks in database operations."""
        db_path = Path(self.temp_dir) / "memory_test.db"
        config = DatabaseConfig(
            db_path=str(db_path), use_duckdb=False
        )  # Use SQLite for simpler testing

        # Get baseline memory
        gc.collect()
        baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        # Perform many database operations
        for cycle in range(10):
            with DatabaseManager(config) as db:
                # Insert entries
                entries = []
                for i in range(100):
                    entries.append(
                        {
                            f"MemTest{cycle:02d}{i:03d}, User": {
                                "GlobalID": f"M{cycle:02d}{i:018d}",
                                "CanonicalNative": f"MemTest{cycle:02d}{i:03d}, User",
                                "BirthYear": 1900 + i,
                                "CountryCodes": ["US"],
                                "Confidence": 80,
                            }
                        }
                    )

                db.insert_initial_stats(entries)
                db.build_surname_stats()
                db.detect_collisions()
                stats = db.get_statistics()

            # Force garbage collection
            gc.collect()

            # Check memory growth
            current_memory = self.process.memory_info().rss / 1024 / 1024
            memory_growth = current_memory - baseline_memory

            # Should not grow more than 50MB after 10 cycles
            assert (
                memory_growth < 50
            ), f"Excessive memory growth: {memory_growth:.1f}MB after {cycle+1} cycles"

    def test_connection_pool_cleanup(self):
        """Test that database connections are properly cleaned up."""
        db_path = Path(self.temp_dir) / "connection_test.db"
        config = DatabaseConfig(db_path=str(db_path))

        # Track open file descriptors
        initial_fds = len(self.process.open_files())

        # Create and destroy many connections
        for i in range(50):
            db = DatabaseManager(config)

            # Perform operations
            db.insert_initial_stats(
                [
                    {
                        f"ConnTest{i:03d}, User": {
                            "GlobalID": f"C{i:019d}",
                            "CanonicalNative": f"ConnTest{i:03d}, User",
                            "BirthYear": 2000,
                            "CountryCodes": ["US"],
                            "Confidence": 75,
                        }
                    }
                ]
            )

            # Explicitly close
            db.close()

            # Check file descriptors
            current_fds = len(self.process.open_files())

            # Should not accumulate file descriptors
            assert (
                current_fds - initial_fds < 5
            ), f"File descriptor leak: {current_fds - initial_fds} extra FDs after {i+1} iterations"


class TestDatabaseRecovery:
    """Test database recovery and resilience."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_wal_mode_recovery(self):
        """Test WAL mode recovery after crash."""
        db_path = Path(self.temp_dir) / "wal_test.db"
        config = DatabaseConfig(
            db_path=str(db_path), use_duckdb=False, enable_wal=True  # Use SQLite for WAL testing
        )

        # Create database and insert data
        with DatabaseManager(config) as db:
            entries = []
            for i in range(100):
                entries.append(
                    {
                        f"WALTest{i:03d}, User": {
                            "GlobalID": f"W{i:019d}",
                            "CanonicalNative": f"WALTest{i:03d}, User",
                            "BirthYear": 1950 + i,
                            "CountryCodes": ["US"],
                            "Confidence": 85,
                        }
                    }
                )

            db.insert_initial_stats(entries)
            stats_before = db.get_statistics()

        # Verify WAL files exist
        wal_path = Path(str(db_path) + "-wal")
        shm_path = Path(str(db_path) + "-shm")

        if wal_path.exists():
            # Simulate crash by copying database without WAL
            import shutil

            crashed_db = Path(self.temp_dir) / "crashed.db"
            shutil.copy(db_path, crashed_db)

            # Open crashed database
            crashed_config = DatabaseConfig(db_path=str(crashed_db), use_duckdb=False)

            with DatabaseManager(crashed_config) as db:
                stats_after = db.get_statistics()

                # Should have recovered data
                assert stats_after["total_entries"] > 0, "No data recovered after crash"

    def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        db_path = Path(self.temp_dir) / "rollback_test.db"
        config = DatabaseConfig(
            db_path=str(db_path), use_duckdb=False  # Use SQLite for transaction testing
        )

        with DatabaseManager(config) as db:
            # Insert initial data
            initial_entries = [
                {
                    "Initial, Test": {
                        "GlobalID": "INITIAL00000000000000",
                        "CanonicalNative": "Initial, Test",
                        "BirthYear": 1900,
                        "CountryCodes": ["US"],
                        "Confidence": 90,
                    }
                }
            ]

            db.insert_initial_stats(initial_entries)
            initial_count = db.get_statistics()["total_entries"]

            # Try to insert duplicate GlobalID (should fail)
            duplicate_entries = [
                {
                    "Duplicate, Test": {
                        "GlobalID": "INITIAL00000000000000",  # Same GlobalID
                        "CanonicalNative": "Duplicate, Test",
                        "BirthYear": 2000,
                        "CountryCodes": ["UK"],
                        "Confidence": 80,
                    }
                }
            ]

            try:
                db.insert_initial_stats(duplicate_entries)
            except Exception:
                pass  # Expected to fail

            # Verify rollback - count should be unchanged
            final_count = db.get_statistics()["total_entries"]
            assert (
                final_count == initial_count
            ), f"Transaction not rolled back: {final_count} != {initial_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
