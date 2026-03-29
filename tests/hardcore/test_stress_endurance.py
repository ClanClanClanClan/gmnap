"""
Stress and endurance testing for GMNAP system.

Tests system behavior under sustained load, resource exhaustion,
and extreme conditions over extended periods.
"""

import asyncio
import gc
import random
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import psutil
import pytest
import yaml

from src.core.config import GMNAPConfig
from src.core.globalid import GlobalIDGenerator
from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
from src.core.unicode_handler import UnicodeNormalizer
from src.utils.cache import CacheManager
from src.utils.database import DatabaseManager


class StressTestMonitor:
    """Monitor system resources during stress testing."""

    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.metrics = []
        self.alerts = []
        self.thread = None

    def start(self):
        """Start monitoring."""
        self.monitoring = True
        self.metrics = []
        self.alerts = []
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop monitoring."""
        self.monitoring = False
        if self.thread:
            self.thread.join(timeout=1)

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                # Collect metrics
                memory = self.process.memory_info()
                cpu = self.process.cpu_percent()

                metric = {
                    "timestamp": time.time(),
                    "memory_rss_mb": memory.rss / 1024 / 1024,
                    "memory_vms_mb": memory.vms / 1024 / 1024,
                    "cpu_percent": cpu,
                    "threads": self.process.num_threads(),
                    "fds": self.process.num_fds() if hasattr(self.process, "num_fds") else 0,
                    "gc_objects": len(gc.get_objects()),
                }

                self.metrics.append(metric)

                # Check for alerts
                if memory.rss / 1024 / 1024 > 2048:  # 2GB
                    self.alerts.append(f"High memory usage: {memory.rss / 1024 / 1024:.1f}MB")

                if cpu > 95:
                    self.alerts.append(f"High CPU usage: {cpu:.1f}%")

                if len(self.metrics) > 10000:  # Limit history
                    self.metrics = self.metrics[-5000:]

            except Exception as e:
                self.alerts.append(f"Monitoring error: {str(e)}")

            time.sleep(0.1)

    def get_summary(self):
        """Get monitoring summary."""
        if not self.metrics:
            return {}

        memory_values = [m["memory_rss_mb"] for m in self.metrics]
        cpu_values = [m["cpu_percent"] for m in self.metrics]

        return {
            "duration_seconds": self.metrics[-1]["timestamp"] - self.metrics[0]["timestamp"],
            "memory_peak_mb": max(memory_values),
            "memory_avg_mb": sum(memory_values) / len(memory_values),
            "cpu_peak_percent": max(cpu_values),
            "cpu_avg_percent": sum(cpu_values) / len(cpu_values),
            "alerts": self.alerts,
            "total_samples": len(self.metrics),
        }


class TestLongRunningStress:
    """Test long-running operations under stress."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = StressTestMonitor()
        self.config = GMNAPConfig()
        self.config.processing.memory_limit_mb = 1024  # 1GB limit for testing

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.monitor:
            self.monitor.stop()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.slow
    def test_continuous_globalid_generation(self):
        """Test continuous GlobalID generation for 5 minutes."""
        generator = GlobalIDGenerator()
        self.monitor.start()

        start_time = time.time()
        end_time = start_time + 300  # 5 minutes

        generated_ids = set()
        generation_count = 0
        errors = []

        try:
            while time.time() < end_time:
                try:
                    # Generate with variety of inputs
                    entry = {
                        "CanonicalNative": f"Test{generation_count:08d}, Person",
                        "BirthYear": 1950 + (generation_count % 100),
                    }

                    global_id = generator.generate(entry)

                    # Verify uniqueness
                    assert (
                        global_id not in generated_ids
                    ), f"Duplicate ID after {generation_count} generations"
                    generated_ids.add(global_id)

                    generation_count += 1

                    # Periodic cleanup
                    if generation_count % 10000 == 0:
                        gc.collect()

                except Exception as e:
                    errors.append((generation_count, str(e)))
                    if len(errors) > 100:  # Stop if too many errors
                        break

        finally:
            self.monitor.stop()

        # Verify results
        summary = self.monitor.get_summary()

        assert len(errors) < 10, f"Too many errors during continuous generation: {errors[:5]}"
        assert generation_count > 10000, f"Generation rate too low: {generation_count} in 5 minutes"
        assert (
            summary["memory_peak_mb"] < 2048
        ), f"Memory exceeded limit: {summary['memory_peak_mb']}MB"

        # Check for memory leaks
        assert (
            summary["memory_peak_mb"] < summary["memory_avg_mb"] * 2
        ), f"Possible memory leak: peak {summary['memory_peak_mb']}MB vs avg {summary['memory_avg_mb']}MB"

    @pytest.mark.slow
    def test_sustained_unicode_processing(self):
        """Test sustained Unicode processing with various scripts."""
        handler = UnicodeHandler()
        self.monitor.start()

        # Test strings from various scripts
        test_strings = [
            "García, José María",
            "李明华",
            "محمد عبد الله",
            "Владимир Петров",
            "Σωκράτης",
            "राम चन्द्र",
            "การันต์ สมบูรณ์",
            "ሃይለ ሥላሴ",
            "😀🎉🚀",  # Emoji
            "A" * 1000,  # Long string
            "A\u0300\u0301\u0302",  # Combining characters
        ]

        start_time = time.time()
        end_time = start_time + 180  # 3 minutes

        processing_count = 0
        errors = []

        try:
            while time.time() < end_time:
                try:
                    # Process random test string
                    test_string = random.choice(test_strings)
                    normalized = handler.normalize(test_string)

                    # Verify normalization
                    if normalized is not None:
                        # Should be idempotent
                        normalized2 = handler.normalize(normalized)
                        assert (
                            normalized == normalized2
                        ), f"Non-idempotent normalization at {processing_count}"

                    processing_count += 1

                    # Periodic cleanup
                    if processing_count % 5000 == 0:
                        gc.collect()

                except Exception as e:
                    errors.append((processing_count, str(e)))
                    if len(errors) > 50:
                        break

        finally:
            self.monitor.stop()

        # Verify results
        summary = self.monitor.get_summary()

        assert len(errors) < 5, f"Too many errors during Unicode processing: {errors[:3]}"
        assert processing_count > 5000, f"Processing rate too low: {processing_count} in 3 minutes"
        assert (
            summary["memory_peak_mb"] < 1024
        ), f"Memory exceeded limit: {summary['memory_peak_mb']}MB"

    @pytest.mark.slow
    def test_concurrent_load_endurance(self):
        """Test concurrent load endurance over extended period."""
        self.monitor.start()

        # Create shared resources
        generator = GlobalIDGenerator()
        handler = UnicodeHandler()

        # Results tracking
        results = Queue()
        errors = Queue()

        def worker(worker_id, duration_seconds):
            """Worker function for concurrent load."""
            end_time = time.time() + duration_seconds
            local_count = 0

            while time.time() < end_time:
                try:
                    # Mix of operations
                    operation = random.choice(["globalid", "unicode", "mixed"])

                    if operation == "globalid":
                        entry = {
                            "CanonicalNative": f"Worker{worker_id:02d}Test{local_count:06d}, Person",
                            "BirthYear": 1950 + (local_count % 100),
                        }
                        global_id = generator.generate(entry)
                        assert global_id is not None, f"GlobalID generation failed"

                    elif operation == "unicode":
                        test_text = f"Test{local_count:06d}García, José"
                        normalized = handler.normalize(test_text)
                        assert normalized is not None, f"Unicode normalization failed"

                    elif operation == "mixed":
                        # Combined operation
                        test_text = f"Worker{worker_id:02d}李{local_count:06d}明"
                        normalized = handler.normalize(test_text)
                        if normalized:
                            entry = {"CanonicalNative": normalized}
                            global_id = generator.generate(entry)
                            assert global_id is not None, f"Combined operation failed"

                    local_count += 1

                except Exception as e:
                    errors.put((worker_id, local_count, str(e)))

            results.put((worker_id, local_count))

        # Start workers
        num_workers = 8
        duration = 120  # 2 minutes

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(target=worker, args=(i, duration))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        self.monitor.stop()

        # Collect results
        worker_results = []
        worker_errors = []

        while not results.empty():
            try:
                worker_results.append(results.get_nowait())
            except Empty:
                break

        while not errors.empty():
            try:
                worker_errors.append(errors.get_nowait())
            except Empty:
                break

        # Verify results
        summary = self.monitor.get_summary()

        assert (
            len(worker_results) == num_workers
        ), f"Not all workers completed: {len(worker_results)}/{num_workers}"
        assert len(worker_errors) < 20, f"Too many worker errors: {len(worker_errors)}"

        total_operations = sum(result[1] for result in worker_results)
        assert total_operations > 10000, f"Total operations too low: {total_operations}"

        # Check resource usage
        assert (
            summary["memory_peak_mb"] < 2048
        ), f"Memory exceeded limit: {summary['memory_peak_mb']}MB"
        assert len(summary["alerts"]) < 10, f"Too many resource alerts: {len(summary['alerts'])}"


class TestMemoryPressureEndurance:
    """Test system behavior under memory pressure."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = StressTestMonitor()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.monitor:
            self.monitor.stop()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.slow
    def test_memory_pressure_globalid_generation(self):
        """Test GlobalID generation under memory pressure."""
        generator = GlobalIDGenerator()
        self.monitor.start()

        # Create memory pressure
        memory_hogs = []
        try:
            # Consume memory gradually
            for i in range(100):
                # Allocate 10MB chunks
                chunk = bytearray(10 * 1024 * 1024)
                memory_hogs.append(chunk)

                # Test GlobalID generation under pressure
                entry = {"CanonicalNative": f"MemoryTest{i:03d}, Person", "BirthYear": 1980 + i}

                global_id = generator.generate(entry)
                assert (
                    global_id is not None
                ), f"GlobalID generation failed under memory pressure at {i}"

                # Monitor memory usage
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                if current_memory > 1500:  # 1.5GB
                    break

        finally:
            # Clean up memory
            del memory_hogs
            gc.collect()
            self.monitor.stop()

        summary = self.monitor.get_summary()

        # Should have handled memory pressure gracefully
        assert len(summary["alerts"]) > 0, "Expected memory pressure alerts"

        # System should still be functional
        test_entry = {"CanonicalNative": "Final, Test", "BirthYear": 2000}
        final_id = generator.generate(test_entry)
        assert final_id is not None, "System not functional after memory pressure"

    @pytest.mark.slow
    def test_cache_under_memory_pressure(self):
        """Test cache behavior under memory pressure."""
        cache = CacheManager(
            cache_dir=Path(self.temp_dir) / "cache", max_size_gb=0.1, default_ttl_days=1  # 100MB
        )

        self.monitor.start()

        # Fill cache while under memory pressure
        memory_hogs = []
        cache_operations = 0

        try:
            for i in range(200):
                # Create memory pressure
                if i % 10 == 0:
                    chunk = bytearray(5 * 1024 * 1024)  # 5MB chunks
                    memory_hogs.append(chunk)

                # Cache operations
                key = f"memory_test_{i}"
                data = {"index": i, "data": "x" * 1000}

                cache.set(key, data)
                retrieved = cache.get(key)

                if retrieved == data:
                    cache_operations += 1

                # Check memory usage
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                if current_memory > 1000:  # 1GB
                    break

        finally:
            del memory_hogs
            gc.collect()
            self.monitor.stop()

        summary = self.monitor.get_summary()

        # Cache should have handled memory pressure
        assert (
            cache_operations > 50
        ), f"Cache operations too low under memory pressure: {cache_operations}"

        # Cache should still be functional
        cache.set("final_test", {"final": "test"})
        final_data = cache.get("final_test")
        assert final_data == {"final": "test"}, "Cache not functional after memory pressure"


class TestDatabaseStressEndurance:
    """Test database operations under stress."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "stress_test.db"
        self.monitor = StressTestMonitor()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.monitor:
            self.monitor.stop()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.slow
    def test_database_concurrent_stress(self):
        """Test database under concurrent stress."""
        self.monitor.start()

        # Create database
        db = DatabaseManager()
        db.db_path = self.db_path
        db.initialize()

        # Create test table
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS stress_test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER,
                operation_id INTEGER,
                data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Stress test function
        def database_stress_worker(worker_id, operations):
            """Worker function for database stress."""
            worker_db = DatabaseManager()
            worker_db.db_path = self.db_path
            worker_db.initialize()

            successful_ops = 0
            errors = []

            for i in range(operations):
                try:
                    # Mix of operations
                    operation = random.choice(["insert", "select", "update", "delete"])

                    if operation == "insert":
                        worker_db.execute(
                            "INSERT INTO stress_test (worker_id, operation_id, data) VALUES (?, ?, ?)",
                            (worker_id, i, f"data_{worker_id}_{i}"),
                        )

                    elif operation == "select":
                        result = worker_db.execute(
                            "SELECT COUNT(*) FROM stress_test WHERE worker_id = ?", (worker_id,)
                        ).fetchone()

                    elif operation == "update":
                        worker_db.execute(
                            "UPDATE stress_test SET data = ? WHERE worker_id = ? AND operation_id = ?",
                            (f"updated_{worker_id}_{i}", worker_id, i % 10),
                        )

                    elif operation == "delete":
                        worker_db.execute(
                            "DELETE FROM stress_test WHERE worker_id = ? AND operation_id < ?",
                            (worker_id, i - 50),
                        )

                    successful_ops += 1

                except Exception as e:
                    errors.append((i, str(e)))
                    if len(errors) > 10:  # Stop if too many errors
                        break

            return successful_ops, errors

        # Run concurrent stress test
        num_workers = 6
        operations_per_worker = 1000

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(database_stress_worker, i, operations_per_worker)
                for i in range(num_workers)
            ]

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        self.monitor.stop()

        # Verify results
        total_successful = sum(result[0] for result in results)
        total_errors = sum(len(result[1]) for result in results)

        assert (
            total_successful > num_workers * operations_per_worker * 0.9
        ), f"Too many failed operations: {total_successful}/{num_workers * operations_per_worker}"

        assert total_errors < 100, f"Too many database errors: {total_errors}"

        # Database should still be functional
        final_count = db.execute("SELECT COUNT(*) FROM stress_test").fetchone()[0]
        assert final_count > 0, "Database corrupted after stress test"

        summary = self.monitor.get_summary()
        assert (
            summary["memory_peak_mb"] < 2048
        ), f"Memory exceeded limit: {summary['memory_peak_mb']}MB"


class TestSystemRecoveryEndurance:
    """Test system recovery from various failure scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = StressTestMonitor()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.monitor:
            self.monitor.stop()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.slow
    def test_repeated_failure_recovery(self):
        """Test system recovery from repeated failures."""
        generator = GlobalIDGenerator()
        self.monitor.start()

        # Simulate repeated failures and recovery
        failure_count = 0
        recovery_count = 0

        for cycle in range(50):  # 50 failure/recovery cycles
            try:
                # Normal operation
                for i in range(20):
                    entry = {
                        "CanonicalNative": f"Cycle{cycle:02d}Test{i:02d}, Person",
                        "BirthYear": 1980 + i,
                    }
                    global_id = generator.generate(entry)
                    assert global_id is not None, f"Generation failed in cycle {cycle}"

                # Simulate failure
                if cycle % 5 == 0:
                    # Force garbage collection to simulate memory pressure
                    gc.collect()

                    # Simulate temporary failure
                    original_generate = generator.generate

                    def failing_generate(entry):
                        if random.random() < 0.3:  # 30% failure rate
                            raise Exception("Simulated failure")
                        return original_generate(entry)

                    generator.generate = failing_generate

                    # Try operations under failure
                    for i in range(10):
                        try:
                            entry = {
                                "CanonicalNative": f"Failure{cycle:02d}Test{i:02d}, Person",
                                "BirthYear": 1980 + i,
                            }
                            global_id = generator.generate(entry)

                        except Exception:
                            failure_count += 1

                    # Restore functionality
                    generator.generate = original_generate

                    # Verify recovery
                    test_entry = {
                        "CanonicalNative": f"Recovery{cycle:02d}, Test",
                        "BirthYear": 1980,
                    }
                    recovery_id = generator.generate(test_entry)
                    assert recovery_id is not None, f"Recovery failed in cycle {cycle}"
                    recovery_count += 1

            except Exception as e:
                pytest.fail(f"Unhandled exception in cycle {cycle}: {str(e)}")

        self.monitor.stop()

        # Verify recovery behavior
        assert failure_count > 0, "No failures were simulated"
        assert recovery_count > 0, "No recoveries were tested"

        # System should be fully functional after all cycles
        final_entry = {"CanonicalNative": "Final, Test", "BirthYear": 2000}
        final_id = generator.generate(final_entry)
        assert final_id is not None, "System not functional after repeated failures"

        summary = self.monitor.get_summary()
        assert (
            summary["memory_peak_mb"] < 2048
        ), f"Memory exceeded limit: {summary['memory_peak_mb']}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "not slow"])
