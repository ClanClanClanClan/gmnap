"""
Stress testing and failover scenarios for database layer.
Tests memory pressure, failover, corruption, and edge cases.
"""

import gc
import os
import random
import shutil
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import psutil
import pytest

from src.utils.database import (DatabaseConfig, DatabaseManager,
                                create_database_manager)


@pytest.mark.stress
class TestDatabaseStressTests:
    """Stress tests for database operations."""
    
    def test_large_batch_insert_stress(self, temp_db_path):
        """Test inserting large batches of entries."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            memory_threshold_gb=0.1,  # Force SQLite
            use_duckdb=False
        )
        
        # Generate large dataset
        entries = []
        for i in range(10000):
            entry = {
                f"TestName{i}, Given{i}": {
                    "GlobalID": f"ABCDEFGHIJKLMNOPQRST{i:02d}",
                    "CanonicalLatin": f"TestName{i}, Given{i}",
                    "CanonicalNative": f"TestName{i}, Given{i}",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "unspecified",
                    "GenderProvided": False,
                    "BirthYear": 1900 + (i % 100),
                    "CountryCodes": ["US"],
                    "Confidence": 50 + (i % 50),
                    "Historic": False,
                    "GDPR_DATA": False
                }
            }
            entries.append(entry)
        
        with DatabaseManager(config) as db:
            # Should handle large batch without crashing
            inserted_count = db.insert_initial_stats(entries)
            assert inserted_count == len(entries)
            
            # Verify data integrity
            stats = db.get_statistics()
            assert stats["total_entries"] == len(entries)
    
    def test_concurrent_database_access(self, temp_db_path):
        """Test concurrent access from multiple threads."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            memory_threshold_gb=0.1,
            use_duckdb=False,
            enable_wal=True  # Enable WAL for better concurrency
        )
        
        # Shared data for threads
        results = []
        errors = []
        
        def worker_thread(thread_id: int, num_entries: int):
            """Worker thread that inserts entries."""
            try:
                with DatabaseManager(config) as db:
                    entries = []
                    for i in range(num_entries):
                        entry = {
                            f"Thread{thread_id}Name{i}, Given{i}": {
                                "GlobalID": f"THREAD{thread_id:02d}ENTRY{i:04d}ABC",
                                "CanonicalLatin": f"Thread{thread_id}Name{i}, Given{i}",
                                "CanonicalNative": f"Thread{thread_id}Name{i}, Given{i}",
                                "LanguageOfPublication": ["en"],
                                "FamilyNameType": "surname",
                                "Gender": "unspecified",
                                "GenderProvided": False,
                                "CountryCodes": [f"T{thread_id}"],
                                "Confidence": 50,
                                "Historic": False,
                                "GDPR_DATA": False
                            }
                        }
                        entries.append(entry)
                    
                    inserted = db.insert_initial_stats(entries)
                    results.append((thread_id, inserted))
                    
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads
        threads = []
        num_threads = 5
        entries_per_thread = 100
        
        for i in range(num_threads):
            thread = threading.Thread(target=worker_thread, args=(i, entries_per_thread))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout
            if thread.is_alive():
                pytest.fail("Thread timed out")
        
        # Check results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == num_threads, f"Missing thread results: {results}"
        
        # Verify total entries
        with DatabaseManager(config) as db:
            stats = db.get_statistics()
            expected_total = num_threads * entries_per_thread
            assert stats["total_entries"] == expected_total
    
    def test_memory_pressure_failover(self, temp_db_path, mock_memory_pressure):
        """Test failover from DuckDB to SQLite under memory pressure."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            memory_threshold_gb=1.0,  # Will be below available memory
            use_duckdb=True
        )
        
        # Should fail over to SQLite due to mocked low memory
        with DatabaseManager(config) as db:
            assert db.db_type == "sqlite", f"Expected SQLite, got {db.db_type}"
            
            # Should still work normally
            entry = {
                "Smith, John": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John",
                    "CanonicalNative": "Smith, John",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": 95,
                    "Historic": False,
                    "GDPR_DATA": False
                }
            }
            
            inserted = db.insert_initial_stats([entry])
            assert inserted == 1
    
    def test_duckdb_unavailable_fallback(self, temp_db_path):
        """Test fallback when DuckDB is unavailable."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=True
        )
        
        # Mock DuckDB as unavailable
        with patch('src.utils.database.DUCKDB_AVAILABLE', False):
            with DatabaseManager(config) as db:
                assert db.db_type == "sqlite", "Should fall back to SQLite when DuckDB unavailable"
                
                # Should work normally
                entry = {
                    "Test, User": {
                        "GlobalID": "TESTABCDEFGHIJKLMNOPQ",
                        "CanonicalLatin": "Test, User",
                        "CanonicalNative": "Test, User",
                        "LanguageOfPublication": ["en"],
                        "FamilyNameType": "surname",
                        "Gender": "unspecified",
                        "GenderProvided": False,
                        "CountryCodes": ["US"],
                        "Confidence": 50,
                        "Historic": False,
                        "GDPR_DATA": False
                    }
                }
                
                inserted = db.insert_initial_stats([entry])
                assert inserted == 1
    
    def test_database_corruption_handling(self, temp_db_path):
        """Test handling of corrupted database files."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False
        )
        
        # Create a corrupted database file
        with open(temp_db_path, 'wb') as f:
            f.write(b"This is not a valid SQLite file")
        
        # Should handle corruption gracefully
        try:
            with DatabaseManager(config) as db:
                # Might succeed if it recreates the file
                pass
        except sqlite3.DatabaseError:
            # Acceptable to fail on corrupted database
            pass
    
    def test_disk_space_exhaustion(self, temp_db_path):
        """Test behavior when disk space is exhausted."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False
        )
        
        # Mock disk full error
        original_execute = sqlite3.Connection.execute
        
        def mock_execute(self, sql, parameters=None):
            if "INSERT" in sql.upper():
                raise sqlite3.OperationalError("database or disk is full")
            return original_execute(self, sql, parameters or [])
        
        with patch.object(sqlite3.Connection, 'execute', mock_execute):
            with DatabaseManager(config) as db:
                entry = {
                    "Test, User": {
                        "GlobalID": "TESTABCDEFGHIJKLMNOPQ",
                        "CanonicalLatin": "Test, User",
                        "CanonicalNative": "Test, User",
                        "LanguageOfPublication": ["en"],
                        "FamilyNameType": "surname",
                        "Gender": "unspecified",
                        "GenderProvided": False,
                        "CountryCodes": ["US"],
                        "Confidence": 50,
                        "Historic": False,
                        "GDPR_DATA": False
                    }
                }
                
                # Should handle disk full error gracefully
                try:
                    inserted = db.insert_initial_stats([entry])
                    # If it succeeds, that's fine too
                except sqlite3.OperationalError as e:
                    assert "disk is full" in str(e)
    
    def test_extremely_long_names(self, temp_db_path):
        """Test handling of extremely long names."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False
        )
        
        # Create very long names
        long_family = "A" * 10000
        long_given = "B" * 10000
        long_canonical = f"{long_family}, {long_given}"
        
        entry = {
            long_canonical: {
                "GlobalID": "LONGABCDEFGHIJKLMNOPQ",
                "CanonicalLatin": long_canonical,
                "CanonicalNative": long_canonical,
                "LanguageOfPublication": ["en"],
                "FamilyNameType": "surname",
                "Gender": "unspecified",
                "GenderProvided": False,
                "CountryCodes": ["US"],
                "Confidence": 50,
                "Historic": False,
                "GDPR_DATA": False
            }
        }
        
        with DatabaseManager(config) as db:
            # Should handle very long names
            try:
                inserted = db.insert_initial_stats([entry])
                assert inserted == 1
            except Exception as e:
                # Might fail due to database limits, which is acceptable
                assert "too long" in str(e).lower() or "limit" in str(e).lower()
    
    def test_rapid_open_close_cycles(self, temp_db_path):
        """Test rapid database open/close cycles."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False
        )
        
        # Rapidly open and close connections
        for i in range(100):
            with DatabaseManager(config) as db:
                # Quick operation
                stats = db.get_statistics()
                assert isinstance(stats, dict)
    
    def test_database_locking_scenarios(self, temp_db_path):
        """Test database locking scenarios."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False,
            enable_wal=False  # Disable WAL to test locking
        )
        
        # First connection holds a transaction
        db1 = DatabaseManager(config)
        
        try:
            # Start a transaction
            db1.connection.execute("BEGIN EXCLUSIVE TRANSACTION")
            
            # Second connection should handle lock appropriately
            db2 = DatabaseManager(config)
            
            try:
                entry = {
                    "Test, User": {
                        "GlobalID": "TESTABCDEFGHIJKLMNOPQ",
                        "CanonicalLatin": "Test, User",
                        "CanonicalNative": "Test, User",
                        "LanguageOfPublication": ["en"],
                        "FamilyNameType": "surname",
                        "Gender": "unspecified",
                        "GenderProvided": False,
                        "CountryCodes": ["US"],
                        "Confidence": 50,
                        "Historic": False,
                        "GDPR_DATA": False
                    }
                }
                
                # This might timeout or fail due to lock
                try:
                    inserted = db2.insert_initial_stats([entry])
                except sqlite3.OperationalError as e:
                    assert "locked" in str(e).lower()
                    
            finally:
                db2.close()
                
        finally:
            db1.connection.rollback()
            db1.close()
    
    def test_collision_detection_stress(self, temp_db_path):
        """Test collision detection with many similar names."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False
        )
        
        # Create many entries with same surname and birth decade
        entries = []
        base_surname = "Smith"
        birth_decade = 1980
        
        for i in range(1000):
            entry = {
                f"{base_surname}, Given{i}": {
                    "GlobalID": f"SMITH{i:04d}ABCDEFGHIJK",
                    "CanonicalLatin": f"{base_surname}, Given{i}",
                    "CanonicalNative": f"{base_surname}, Given{i}",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "unspecified",
                    "GenderProvided": False,
                    "BirthYear": birth_decade + random.randint(0, 9),
                    "CountryCodes": ["US"],
                    "Confidence": 50,
                    "Historic": False,
                    "GDPR_DATA": False
                }
            }
            entries.append(entry)
        
        with DatabaseManager(config) as db:
            # Insert all entries
            inserted = db.insert_initial_stats(entries)
            assert inserted == len(entries)
            
            # Build surname stats
            stats = db.build_surname_stats()
            assert stats["unique_surnames"] >= 1
            
            # Detect collisions
            collisions = db.detect_collisions(threshold=10)
            assert len(collisions) > 0, "Should detect collisions with 1000 similar names"
            
            # Verify collision data
            for collision in collisions:
                assert collision["count"] >= 10
                assert len(collision["global_ids"]) >= 10
    
    def test_memory_leak_detection(self, temp_db_path):
        """Test for memory leaks in database operations."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False
        )
        
        # Monitor memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Perform many operations
        for iteration in range(50):
            with DatabaseManager(config) as db:
                entries = []
                for i in range(20):
                    entry = {
                        f"Test{iteration}_{i}, User{i}": {
                            "GlobalID": f"TEST{iteration:02d}{i:02d}ABCDEFG",
                            "CanonicalLatin": f"Test{iteration}_{i}, User{i}",
                            "CanonicalNative": f"Test{iteration}_{i}, User{i}",
                            "LanguageOfPublication": ["en"],
                            "FamilyNameType": "surname",
                            "Gender": "unspecified",
                            "GenderProvided": False,
                            "CountryCodes": ["US"],
                            "Confidence": 50,
                            "Historic": False,
                            "GDPR_DATA": False
                        }
                    }
                    entries.append(entry)
                
                db.insert_initial_stats(entries)
                db.build_surname_stats()
                db.detect_collisions()
            
            # Force garbage collection
            gc.collect()
        
        final_memory = process.memory_info().rss
        memory_growth = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        # Should not grow memory excessively
        assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.2f}MB"
    
    def test_invalid_sql_injection_protection(self, temp_db_path):
        """Test protection against SQL injection in name data."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False
        )
        
        # SQL injection payloads
        injection_payloads = [
            "Smith'; DROP TABLE initial_stats; --",
            "Smith' OR '1'='1",
            "Smith\"; DELETE FROM surname_stats; --",
            "Smith' UNION SELECT * FROM sqlite_master --"
        ]
        
        with DatabaseManager(config) as db:
            for payload in injection_payloads:
                entry = {
                    payload: {
                        "GlobalID": "SQLINJECTESTABCDEFGH",
                        "CanonicalLatin": payload,
                        "CanonicalNative": payload,
                        "LanguageOfPublication": ["en"],
                        "FamilyNameType": "surname",
                        "Gender": "unspecified",
                        "GenderProvided": False,
                        "CountryCodes": ["US"],
                        "Confidence": 50,
                        "Historic": False,
                        "GDPR_DATA": False
                    }
                }
                
                # Should handle SQL injection safely
                try:
                    inserted = db.insert_initial_stats([entry])
                    assert inserted == 1
                    
                    # Verify tables still exist
                    stats = db.get_statistics()
                    assert isinstance(stats, dict)
                    
                except Exception as e:
                    # If it fails, should be due to validation, not SQL injection
                    assert "syntax error" not in str(e).lower()


@pytest.mark.stress
@pytest.mark.slow
class TestDatabaseFailoverScenarios:
    """Test database failover and recovery scenarios."""
    
    def test_graceful_degradation_chain(self, temp_db_path):
        """Test graceful degradation through failure chain."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=True
        )
        
        # Test progression: DuckDB -> SQLite -> In-memory -> Fail
        test_entry = {
            "Test, User": {
                "GlobalID": "TESTABCDEFGHIJKLMNOPQ",
                "CanonicalLatin": "Test, User",
                "CanonicalNative": "Test, User",
                "LanguageOfPublication": ["en"],
                "FamilyNameType": "surname",
                "Gender": "unspecified",
                "GenderProvided": False,
                "CountryCodes": ["US"],
                "Confidence": 50,
                "Historic": False,
                "GDPR_DATA": False
            }
        }
        
        # Scenario 1: DuckDB fails, fall back to SQLite
        with patch('src.utils.database.duckdb.connect', side_effect=Exception("DuckDB failed")):
            with DatabaseManager(config) as db:
                assert db.db_type == "sqlite"
                inserted = db.insert_initial_stats([test_entry])
                assert inserted == 1
        
        # Scenario 2: Both DuckDB and SQLite file access fail
        config.db_path = "/invalid/path/that/cannot/exist/test.db"
        
        with patch('src.utils.database.duckdb.connect', side_effect=Exception("DuckDB failed")):
            try:
                with DatabaseManager(config) as db:
                    # Should fail gracefully
                    pass
            except Exception as e:
                # Expected to fail when no valid database path
                assert "No such file or directory" in str(e) or "cannot open" in str(e).lower()
    
    def test_database_recovery_after_corruption(self, temp_db_path):
        """Test recovery after database corruption."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False
        )
        
        # Create valid database first
        with DatabaseManager(config) as db:
            entry = {
                "Valid, Entry": {
                    "GlobalID": "VALIDABCDEFGHIJKLMNOP",
                    "CanonicalLatin": "Valid, Entry",
                    "CanonicalNative": "Valid, Entry",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "unspecified",
                    "GenderProvided": False,
                    "CountryCodes": ["US"],
                    "Confidence": 50,
                    "Historic": False,
                    "GDPR_DATA": False
                }
            }
            inserted = db.insert_initial_stats([entry])
            assert inserted == 1
        
        # Corrupt the database
        with open(temp_db_path, 'r+b') as f:
            f.seek(0)
            f.write(b"CORRUPTED" * 100)
        
        # Should handle corruption and potentially recreate
        try:
            with DatabaseManager(config) as db:
                # Might work if it recreates the database
                stats = db.get_statistics()
                assert isinstance(stats, dict)
        except sqlite3.DatabaseError:
            # Acceptable to fail on corrupted database
            pass
    
    def test_network_filesystem_issues(self, temp_dir):
        """Test handling of network filesystem issues."""
        # Simulate network filesystem with permission issues
        restricted_path = temp_dir / "restricted"
        restricted_path.mkdir(mode=0o000)  # No permissions
        
        config = DatabaseConfig(
            db_path=str(restricted_path / "test.db"),
            use_duckdb=False
        )
        
        try:
            with DatabaseManager(config) as db:
                # Should fail due to permissions
                pytest.fail("Should have failed due to permissions")
        except (PermissionError, OSError, sqlite3.OperationalError):
            # Expected to fail
            pass
        finally:
            # Restore permissions for cleanup
            restricted_path.chmod(0o755)
    
    def test_partial_write_scenarios(self, temp_db_path):
        """Test scenarios with partial writes/corruption."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False
        )
        
        # Mock partial write by interrupting executemany
        original_executemany = sqlite3.Connection.executemany
        call_count = 0
        
        def mock_executemany(self, sql, parameters):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and "INSERT" in sql:
                # Simulate interruption on first insert
                raise sqlite3.OperationalError("disk I/O error")
            return original_executemany(self, sql, parameters)
        
        with patch.object(sqlite3.Connection, 'executemany', mock_executemany):
            with DatabaseManager(config) as db:
                entries = [
                    {
                        "Test, User": {
                            "GlobalID": "TESTABCDEFGHIJKLMNOPQ",
                            "CanonicalLatin": "Test, User",
                            "CanonicalNative": "Test, User",
                            "LanguageOfPublication": ["en"],
                            "FamilyNameType": "surname",
                            "Gender": "unspecified",
                            "GenderProvided": False,
                            "CountryCodes": ["US"],
                            "Confidence": 50,
                            "Historic": False,
                            "GDPR_DATA": False
                        }
                    }
                ]
                
                # Should handle I/O error gracefully
                try:
                    inserted = db.insert_initial_stats(entries)
                except sqlite3.OperationalError as e:
                    assert "I/O error" in str(e)


@pytest.mark.integration
@pytest.mark.stress
class TestDatabaseIntegrationStress:
    """Integration stress tests combining multiple components."""
    
    def test_end_to_end_large_dataset_processing(self, temp_db_path):
        """Test end-to-end processing of large dataset."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False  # Use SQLite for predictable behavior
        )
        
        # Generate large realistic dataset
        entries = []
        surnames = ["Smith", "Johnson", "Williams", "Brown", "Jones", "García", "Miller", "Davis", "Rodriguez", "Martinez"]
        given_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth"]
        countries = ["US", "GB", "CA", "AU", "ES", "MX", "FR", "DE", "IT", "BR"]
        
        for i in range(5000):
            surname = random.choice(surnames)
            given = random.choice(given_names)
            country = random.choice(countries)
            
            entry = {
                f"{surname}, {given}": {
                    "GlobalID": f"{surname[:4].upper()}{given[:4].upper()}{i:010d}"[:22],
                    "CanonicalLatin": f"{surname}, {given}",
                    "CanonicalNative": f"{surname}, {given}",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": random.choice(["male", "female", "unspecified"]),
                    "GenderProvided": random.choice([True, False]),
                    "BirthYear": random.randint(1920, 2000),
                    "CountryCodes": [country],
                    "Confidence": random.randint(50, 100),
                    "Historic": random.choice([True, False]),
                    "GDPR_DATA": random.choice([True, False])
                }
            }
            entries.append(entry)
        
        with DatabaseManager(config) as db:
            # Phase 1: Insert all entries
            start_time = time.time()
            inserted = db.insert_initial_stats(entries)
            insert_time = time.time() - start_time
            
            assert inserted == len(entries)
            print(f"Inserted {inserted} entries in {insert_time:.2f}s ({inserted/insert_time:.0f} entries/s)")
            
            # Phase 2: Build surname statistics
            start_time = time.time()
            surname_stats = db.build_surname_stats()
            stats_time = time.time() - start_time
            
            assert surname_stats["unique_surnames"] > 0
            print(f"Built surname stats in {stats_time:.2f}s")
            
            # Phase 3: Detect collisions
            start_time = time.time()
            collisions = db.detect_collisions(threshold=5)
            collision_time = time.time() - start_time
            
            print(f"Detected {len(collisions)} collisions in {collision_time:.2f}s")
            
            # Phase 4: Verify data integrity
            final_stats = db.get_statistics()
            assert final_stats["total_entries"] == len(entries)
            assert final_stats["surname_combinations"] > 0
            
            print(f"Final statistics: {final_stats}")
    
    def test_concurrent_mixed_operations(self, temp_db_path):
        """Test concurrent mixed read/write operations."""
        config = DatabaseConfig(
            db_path=str(temp_db_path),
            use_duckdb=False,
            enable_wal=True  # Enable WAL for better concurrency
        )
        
        # Shared state
        results = {"inserts": 0, "reads": 0, "errors": []}
        lock = threading.Lock()
        
        def insert_worker(worker_id: int):
            """Worker that inserts entries."""
            try:
                with DatabaseManager(config) as db:
                    for i in range(10):
                        entry = {
                            f"InsertWorker{worker_id}, Entry{i}": {
                                "GlobalID": f"INS{worker_id:02d}{i:03d}ABCDEFGHIJ",
                                "CanonicalLatin": f"InsertWorker{worker_id}, Entry{i}",
                                "CanonicalNative": f"InsertWorker{worker_id}, Entry{i}",
                                "LanguageOfPublication": ["en"],
                                "FamilyNameType": "surname",
                                "Gender": "unspecified",
                                "GenderProvided": False,
                                "CountryCodes": ["US"],
                                "Confidence": 50,
                                "Historic": False,
                                "GDPR_DATA": False
                            }
                        }
                        
                        inserted = db.insert_initial_stats([entry])
                        with lock:
                            results["inserts"] += inserted
                        
                        time.sleep(0.01)  # Small delay
                        
            except Exception as e:
                with lock:
                    results["errors"].append(f"Insert worker {worker_id}: {e}")
        
        def read_worker(worker_id: int):
            """Worker that reads statistics."""
            try:
                with DatabaseManager(config) as db:
                    for i in range(20):
                        stats = db.get_statistics()
                        with lock:
                            results["reads"] += 1
                        
                        time.sleep(0.005)  # Small delay
                        
            except Exception as e:
                with lock:
                    results["errors"].append(f"Read worker {worker_id}: {e}")
        
        # Start mixed workers
        threads = []
        
        # Start insert workers
        for i in range(3):
            thread = threading.Thread(target=insert_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Start read workers  
        for i in range(2):
            thread = threading.Thread(target=read_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=60)
            if thread.is_alive():
                pytest.fail("Thread timed out")
        
        # Check results
        assert len(results["errors"]) == 0, f"Worker errors: {results['errors']}"
        assert results["inserts"] == 30, f"Expected 30 inserts, got {results['inserts']}"
        assert results["reads"] > 0, f"Expected reads > 0, got {results['reads']}"
        
        # Final verification
        with DatabaseManager(config) as db:
            final_stats = db.get_statistics()
            assert final_stats["total_entries"] == 30