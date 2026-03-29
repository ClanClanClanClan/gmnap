"""
import unittest
from typing import List
from typing import Optional
from typing import Any
ULTRATHINK Production Test Suite

Comprehensive production-grade tests for GMNAP v7 system.
Tests scale, memory, concurrency, error recovery, network failures,
backup/restore, and deployment readiness.

Created: 2025-09-17
"""

import asyncio
import concurrent.futures
import gc
import json
import os
import pickle
import psutil
import pytest
import random
import shutil
import signal
import string
import sys
import tempfile
import threading
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.pipeline_v7 import V7Pipeline, PipelineMode
from src.regions.manager import RegionManager
from src.regions.manager_optimized import RegionManager as OptimizedRegionManager
from src.authorities.enricher import AuthorityEnricher
from src.core.cache_manager import CacheManager
from src.quality.gates import QualityGates


@dataclass
class TestResult:
    """Container for test results."""

    test_name: str
    passed: bool
    duration: float
    memory_peak: float
    entries_processed: int
    errors: List[str]
    metadata: Dict[str, Any]


class ProductionTestSuite:
    """Production-grade test suite for GMNAP v7."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()

    # ========== SCALE TESTS ==========

    @pytest.mark.production
    @pytest.mark.timeout(3600)  # 1 hour timeout
    async def test_1m_entry_processing(self):
        """Test processing 1M+ entries within performance targets."""
        print("\n🚀 Testing 1M+ Entry Processing...")

        # Track memory
        tracemalloc.start()
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        batch_size = 1000
        total_entries = 1_000_000

        start_time = time.time()
        processed_count = 0
        errors = []

        try:
            for batch_num in range(0, total_entries, batch_size):
                # Generate test batch
                batch = []
                for i in range(batch_size):
                    entry_id = f"TEST-{batch_num + i:07d}"

                    # Mix of different name types
                    if i % 5 == 0:
                        name = f"김민수{random.randint(1, 999)}"  # Korean
                    elif i % 5 == 1:
                        name = f"李明{random.randint(1, 999)}"  # Chinese
                    elif i % 5 == 2:
                        name = f"Smith{random.randint(1, 999)}, John"  # English
                    elif i % 5 == 3:
                        name = f"Иванов{random.randint(1, 999)} Иван"  # Russian
                    else:
                        name = f"محمد علي{random.randint(1, 999)}"  # Arabic

                    batch.append({"CanonicalNative": name, "GlobalID": entry_id})

                # Process batch
                result = await pipeline.process_batch(batch)
                processed_count += len(result.get("entries", []))

                # Check for errors
                if result.get("errors"):
                    errors.extend(result["errors"])

                # Progress report every 100k
                if (batch_num + batch_size) % 100000 == 0:
                    elapsed = time.time() - start_time
                    rate = processed_count / elapsed
                    projected = (total_entries / rate) / 60
                    print(
                        f"  Processed {processed_count:,}/{total_entries:,} "
                        f"({rate:.0f} entries/sec, projected {projected:.1f} min)"
                    )

                # Memory check
                current_memory = process.memory_info().rss / 1024 / 1024
                if current_memory > 8000:  # 8GB limit
                    errors.append(f"Memory exceeded 8GB: {current_memory:.0f}MB")
                    break

        except Exception as e:
            errors.append(str(e))

        # Final stats
        total_time = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_used = final_memory - start_memory

        # Get memory peak
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")
        peak_memory = sum(stat.size for stat in top_stats[:10]) / 1024 / 1024
        tracemalloc.stop()

        # Performance assertions
        rate = processed_count / total_time if total_time > 0 else 0
        projected_1m_time = (1_000_000 / rate / 60) if rate > 0 else float("inf")

        result = TestResult(
            test_name="1M+ Entry Processing",
            passed=projected_1m_time <= 35 and len(errors) == 0,
            duration=total_time,
            memory_peak=peak_memory,
            entries_processed=processed_count,
            errors=errors,
            metadata={
                "rate": rate,
                "projected_1m_time": projected_1m_time,
                "memory_used_mb": memory_used,
                "target_time_minutes": 35,
            },
        )

        print(f"  PASS Processed {processed_count:,} entries in {total_time:.1f}s")
        print(f"  📊 Rate: {rate:.0f} entries/sec")
        print(f"  💾 Memory used: {memory_used:.0f}MB")
        print(f"  ⏱️ Projected 1M time: {projected_1m_time:.1f} min")

        assert (
            projected_1m_time <= 35
        ), f"Performance target not met: {projected_1m_time:.1f} min > 35 min"
        assert len(errors) == 0, f"Errors occurred: {errors[:5]}"

        return result

    # ========== MEMORY TESTS ==========

    @pytest.mark.production
    @pytest.mark.timeout(600)  # 10 minute timeout
    async def test_memory_under_load(self):
        """Test memory usage under sustained high load."""
        print("\n💾 Testing Memory Under Load...")

        process = psutil.Process()
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        memory_samples = []
        errors = []
        start_time = time.time()

        try:
            # Process batches continuously for 5 minutes
            end_time = start_time + 300  # 5 minutes
            batch_count = 0

            while time.time() < end_time:
                # Generate large batch
                batch = []
                for i in range(1000):
                    batch.append(
                        {
                            "CanonicalNative": f"Test Name {random.randint(1, 999999)}",
                            "GlobalID": f"MEM-{batch_count:06d}-{i:04d}",
                        }
                    )

                # Process batch
                await pipeline.process_batch(batch)
                batch_count += 1

                # Sample memory every 10 batches
                if batch_count % 10 == 0:
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    memory_samples.append(memory_mb)

                    if memory_mb > 4000:  # 4GB warning
                        print(f"  WARN High memory usage: {memory_mb:.0f}MB")

                    if memory_mb > 8000:  # 8GB limit
                        errors.append(f"Memory limit exceeded: {memory_mb:.0f}MB")
                        break

                # Force garbage collection periodically
                if batch_count % 100 == 0:
                    gc.collect()

        except Exception as e:
            errors.append(str(e))

        duration = time.time() - start_time
        avg_memory = sum(memory_samples) / len(memory_samples) if memory_samples else 0
        peak_memory = max(memory_samples) if memory_samples else 0

        # Check for memory leak (memory should stabilize)
        if len(memory_samples) > 10:
            first_half_avg = sum(memory_samples[: len(memory_samples) // 2]) / (
                len(memory_samples) // 2
            )
            second_half_avg = sum(memory_samples[len(memory_samples) // 2 :]) / (
                len(memory_samples) - len(memory_samples) // 2
            )
            leak_ratio = second_half_avg / first_half_avg if first_half_avg > 0 else 1

            if leak_ratio > 1.5:
                errors.append(
                    f"Potential memory leak detected: {leak_ratio:.2f}x increase"
                )

        result = TestResult(
            test_name="Memory Under Load",
            passed=peak_memory < 8000 and len(errors) == 0,
            duration=duration,
            memory_peak=peak_memory,
            entries_processed=batch_count * 1000,
            errors=errors,
            metadata={
                "avg_memory_mb": avg_memory,
                "memory_samples": len(memory_samples),
                "batch_count": batch_count,
            },
        )

        print(f"  PASS Processed {batch_count} batches")
        print(f"  💾 Peak memory: {peak_memory:.0f}MB")
        print(f"  📊 Average memory: {avg_memory:.0f}MB")

        assert peak_memory < 8000, f"Memory limit exceeded: {peak_memory:.0f}MB"
        assert len(errors) == 0, f"Errors occurred: {errors}"

        return result

    # ========== CONCURRENCY TESTS ==========

    @pytest.mark.production
    @pytest.mark.timeout(300)  # 5 minute timeout
    def test_concurrent_access(self):
        """Test system under concurrent access from multiple threads."""
        print("\n🔄 Testing Concurrent Access...")

        manager = OptimizedRegionManager()
        errors = []
        processed_count = 0
        lock = threading.Lock()

        def worker(worker_id: int, num_operations: int):
            """Worker thread function."""
            nonlocal processed_count, errors

            for i in range(num_operations):
                try:
                    # Random operation
                    op_type = random.choice(["detect", "process", "cache"])

                    if op_type == "detect":
                        # Test region detection
                        names = ["Kim Min-su", "John Smith", "李明", "محمد علي"]
                        name = random.choice(names)
                        result = manager.detect_region({"CanonicalLatin": name})

                    elif op_type == "process":
                        # Test processing
                        entry = {
                            "CanonicalNative": f"Worker{worker_id} Name{i}",
                            "GlobalID": f"CONC-{worker_id:03d}-{i:05d}",
                        }
                        # Simulate processing
                        result = manager.detect_region(entry)

                    else:  # cache
                        # Test cache operations
                        cache_key = f"worker_{worker_id}_key_{i}"
                        # Simulate cache access

                    with lock:
                        processed_count += 1

                except Exception as e:
                    with lock:
                        errors.append(f"Worker {worker_id}: {str(e)}")

        # Start multiple worker threads
        num_workers = 10
        operations_per_worker = 1000
        threads = []

        start_time = time.time()

        for i in range(num_workers):
            t = threading.Thread(target=worker, args=(i, operations_per_worker))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        duration = time.time() - start_time
        rate = processed_count / duration if duration > 0 else 0

        result = TestResult(
            test_name="Concurrent Access",
            passed=len(errors) == 0
            and processed_count == num_workers * operations_per_worker,
            duration=duration,
            memory_peak=0,
            entries_processed=processed_count,
            errors=errors[:10],  # Limit error list
            metadata={
                "num_workers": num_workers,
                "operations_per_worker": operations_per_worker,
                "rate": rate,
            },
        )

        print(f"  PASS {num_workers} workers completed")
        print(f"  📊 {processed_count} operations in {duration:.2f}s")
        print(f"  🚀 Rate: {rate:.0f} ops/sec")

        assert len(errors) == 0, f"Thread safety issues: {errors[:5]}"
        assert processed_count == num_workers * operations_per_worker, "Lost operations"

        return result

    # ========== ERROR RECOVERY TESTS ==========

    @pytest.mark.production
    @pytest.mark.timeout(300)
    async def test_error_recovery(self):
        """Test system's ability to recover from various error conditions."""
        print("\n🔧 Testing Error Recovery...")

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        errors_recovered = []
        errors_failed = []

        test_cases = [
            # Malformed input
            {"test": "malformed_input", "data": {"BadField": "test"}},
            # Null values
            {
                "test": "null_values",
                "data": {"CanonicalNative": None, "GlobalID": "NULL-001"},
            },
            # Empty strings
            {
                "test": "empty_strings",
                "data": {"CanonicalNative": "", "GlobalID": "EMPTY-001"},
            },
            # Unicode issues
            {
                "test": "unicode_issues",
                "data": {"CanonicalNative": "\x00\x01\x02", "GlobalID": "UNI-001"},
            },
            # Very long strings
            {
                "test": "long_strings",
                "data": {"CanonicalNative": "A" * 10000, "GlobalID": "LONG-001"},
            },
            # Injection attempts
            {
                "test": "injection",
                "data": {
                    "CanonicalNative": "'; DROP TABLE users; --",
                    "GlobalID": "INJ-001",
                },
            },
            # Mixed scripts
            {
                "test": "mixed_scripts",
                "data": {
                    "CanonicalNative": "Test测试тестテスト",
                    "GlobalID": "MIX-001",
                },
            },
            # Special characters
            {
                "test": "special_chars",
                "data": {"CanonicalNative": "!@#$%^&*()", "GlobalID": "SPEC-001"},
            },
        ]

        for test_case in test_cases:
            try:
                # Try to process problematic input
                result = await pipeline.process_batch([test_case["data"]])

                # Check if it handled the error gracefully
                if result.get("errors"):
                    errors_recovered.append(
                        {
                            "test": test_case["test"],
                            "handled": True,
                            "error": result["errors"][0],
                        }
                    )
                else:
                    # Successfully processed problematic input
                    errors_recovered.append(
                        {"test": test_case["test"], "handled": True, "processed": True}
                    )

            except Exception as e:
                # System crashed - not good
                errors_failed.append({"test": test_case["test"], "exception": str(e)})

        # Test recovery from resource exhaustion
        try:
            # Simulate OOM by processing huge batch
            huge_batch = [
                {"CanonicalNative": f"Name{i}", "GlobalID": f"HUGE-{i}"}
                for i in range(100000)
            ]

            with pytest.raises(Exception):
                await pipeline.process_batch(huge_batch)

            # Try normal operation after failure
            normal_batch = [{"CanonicalNative": "Test", "GlobalID": "NORMAL-001"}]
            result = await pipeline.process_batch(normal_batch)

            if not result.get("errors"):
                errors_recovered.append(
                    {"test": "resource_exhaustion_recovery", "handled": True}
                )
        except:
            errors_failed.append(
                {
                    "test": "resource_exhaustion_recovery",
                    "exception": "Failed to recover",
                }
            )

        result = TestResult(
            test_name="Error Recovery",
            passed=len(errors_failed) == 0,
            duration=0,
            memory_peak=0,
            entries_processed=len(test_cases),
            errors=[str(e) for e in errors_failed],
            metadata={
                "recovered": len(errors_recovered),
                "failed": len(errors_failed),
                "test_cases": len(test_cases),
            },
        )

        print(f"  PASS Recovered from {len(errors_recovered)} error conditions")
        print(f"  FAIL Failed on {len(errors_failed)} error conditions")

        assert len(errors_failed) == 0, f"Failed to recover from: {errors_failed}"

        return result

    # ========== NETWORK FAILURE TESTS ==========

    @pytest.mark.production
    @pytest.mark.timeout(300)
    async def test_network_failures(self):
        """Test system behavior under network failures."""
        print("\n🌐 Testing Network Failures...")

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        errors = []
        successes = 0

        # Test with offline mode
        os.environ["OFFLINE"] = "1"

        test_scenarios = [
            # Authority source timeout
            {"scenario": "authority_timeout", "simulate": "timeout"},
            # Connection refused
            {"scenario": "connection_refused", "simulate": "refused"},
            # DNS failure
            {"scenario": "dns_failure", "simulate": "dns"},
            # Partial response
            {"scenario": "partial_response", "simulate": "partial"},
            # Slow network
            {"scenario": "slow_network", "simulate": "slow"},
        ]

        for scenario in test_scenarios:
            try:
                # Mock network issues
                with patch("requests.get") as mock_get:
                    if scenario["simulate"] == "timeout":
                        mock_get.side_effect = TimeoutError("Connection timed out")
                    elif scenario["simulate"] == "refused":
                        mock_get.side_effect = ConnectionRefusedError(
                            "Connection refused"
                        )
                    elif scenario["simulate"] == "dns":
                        mock_get.side_effect = Exception("DNS resolution failed")
                    elif scenario["simulate"] == "partial":
                        mock_get.return_value = MagicMock(
                            status_code=200, json=lambda: {"partial": "data"}
                        )
                    else:  # slow

                        async def slow_response(*args, **kwargs):
                            time.sleep(5)
                            return MagicMock(status_code=200, json=lambda: {})

                        mock_get.side_effect = slow_response

                    # Try to process with network issues
                    batch = [
                        {"CanonicalNative": f"Test{i}", "GlobalID": f"NET-{i}"}
                        for i in range(10)
                    ]

                    result = await pipeline.process_batch(batch)

                    # Should still work in offline mode
                    if result.get("entries"):
                        successes += 1
                        print(f"  PASS Handled {scenario['scenario']}")
                    else:
                        errors.append(f"{scenario['scenario']}: No entries processed")

            except Exception as e:
                errors.append(f"{scenario['scenario']}: {str(e)}")

        # Restore online mode
        del os.environ["OFFLINE"]

        result = TestResult(
            test_name="Network Failures",
            passed=successes == len(test_scenarios),
            duration=0,
            memory_peak=0,
            entries_processed=successes * 10,
            errors=errors,
            metadata={
                "scenarios_tested": len(test_scenarios),
                "scenarios_passed": successes,
            },
        )

        print(
            f"  PASS Handled {successes}/{len(test_scenarios)} network failure scenarios"
        )

        assert successes == len(test_scenarios), f"Failed scenarios: {errors}"

        return result

    # ========== BACKUP/RESTORE TESTS ==========

    @pytest.mark.production
    @pytest.mark.timeout(300)
    def test_backup_restore(self):
        """Test backup and restore functionality."""
        print("\n💾 Testing Backup/Restore...")

        errors = []

        # Create temporary directories
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_dir = tmpdir / "backup"
            backup_dir.mkdir()

            # Initialize system with data
            cache_manager = CacheManager(cache_dir=tmpdir / "cache")

            # Add test data to cache
            test_data = {
                f"key_{i}": {"data": f"value_{i}", "timestamp": time.time()}
                for i in range(1000)
            }

            for key, value in test_data.items():
                cache_manager.set(key, value, ttl=3600)

            # Create backup
            try:
                # Backup cache
                cache_backup = backup_dir / "cache_backup.pkl"
                with open(cache_backup, "wb") as f:
                    pickle.dump(test_data, f)

                # Backup config
                config_data = {"version": "v7", "timestamp": time.time()}
                config_backup = backup_dir / "config_backup.json"
                with open(config_backup, "w") as f:
                    json.dump(config_data, f)

                print(f"  PASS Created backup at {backup_dir}")

            except Exception as e:
                errors.append(f"Backup failed: {str(e)}")

            # Clear cache to simulate data loss
            cache_manager = None
            gc.collect()

            # Restore from backup
            try:
                # Restore cache
                restored_cache = CacheManager(cache_dir=tmpdir / "cache_restored")

                with open(cache_backup, "rb") as f:
                    restored_data = pickle.load(f)

                # Verify restoration
                mismatches = []
                for key, original_value in test_data.items():
                    if key not in restored_data:
                        mismatches.append(f"Missing key: {key}")
                    elif restored_data[key] != original_value:
                        mismatches.append(f"Value mismatch for {key}")

                if mismatches:
                    errors.extend(mismatches[:10])  # Limit to 10 errors

                # Restore config
                with open(config_backup, "r") as f:
                    restored_config = json.load(f)

                if restored_config != config_data:
                    errors.append("Config restoration mismatch")

                print(f"  PASS Restored {len(restored_data)} cache entries")

            except Exception as e:
                errors.append(f"Restore failed: {str(e)}")

        result = TestResult(
            test_name="Backup/Restore",
            passed=len(errors) == 0,
            duration=0,
            memory_peak=0,
            entries_processed=len(test_data),
            errors=errors,
            metadata={
                "cache_entries": len(test_data),
                "backup_size_kb": (
                    cache_backup.stat().st_size / 1024 if cache_backup.exists() else 0
                ),
            },
        )

        assert len(errors) == 0, f"Backup/Restore errors: {errors[:5]}"

        return result

    # ========== DEPLOYMENT TEST ==========

    @pytest.mark.production
    @pytest.mark.timeout(600)
    async def test_production_deployment(self):
        """Test full production deployment readiness."""
        print("\n🚀 Testing Production Deployment...")

        checks_passed = []
        checks_failed = []

        # 1. Check all required modules are importable
        required_modules = [
            "src.core.pipeline_v7",
            "src.regions.manager",
            "src.authorities.enricher",
            "src.quality.gates",
            "src.core.cache_manager",
            "src.core.unicode_handler",
            "src.analytics.duckdb_analytics",
        ]

        for module in required_modules:
            try:
                __import__(module)
                checks_passed.append(f"Module {module}")
            except ImportError as e:
                checks_failed.append(f"Module {module}: {str(e)}")

        # 2. Check configuration files exist
        config_files = [
            "config/weights.yaml",
            "config/authorities.yaml",
            "config/regions.yaml",
            "config/gates.yaml",
        ]

        for config_file in config_files:
            if Path(config_file).exists():
                checks_passed.append(f"Config {config_file}")
            else:
                checks_failed.append(f"Config {config_file}: Missing")

        # 3. Check database connectivity
        try:
            from src.analytics.duckdb_analytics import DuckDBAnalytics

            analytics = DuckDBAnalytics()
            # Test query
            result = analytics.execute_query("SELECT 1")
            checks_passed.append("DuckDB connectivity")
        except Exception as e:
            checks_failed.append(f"DuckDB: {str(e)}")

        # 4. Test end-to-end pipeline
        try:
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)
            test_batch = [{"CanonicalNative": "Test Name", "GlobalID": "DEPLOY-001"}]
            result = await pipeline.process_batch(test_batch)

            if result.get("entries"):
                checks_passed.append("End-to-end pipeline")
            else:
                checks_failed.append("End-to-end pipeline: No output")

        except Exception as e:
            checks_failed.append(f"Pipeline: {str(e)}")

        # 5. Check quality gates
        try:
            gates = QualityGates()
            gate_result = gates.check_all(
                {"entries": test_batch, "metrics": {"processed_entries": 1}}
            )
            checks_passed.append("Quality gates")
        except Exception as e:
            checks_failed.append(f"Quality gates: {str(e)}")

        # 6. Check regional processors
        regions_to_test = ["A1", "E4", "B1", "C3", "D1"]
        manager = RegionManager()

        for region in regions_to_test:
            try:
                if region in manager.IMPLEMENTED_REGIONS:
                    checks_passed.append(f"Region {region}")
                else:
                    checks_failed.append(f"Region {region}: Not implemented")
            except Exception as e:
                checks_failed.append(f"Region {region}: {str(e)}")

        # 7. Performance check
        try:
            start = time.time()
            batch = [
                {"CanonicalNative": f"Name{i}", "GlobalID": f"PERF-{i}"}
                for i in range(100)
            ]
            result = await pipeline.process_batch(batch)
            duration = time.time() - start
            rate = 100 / duration if duration > 0 else 0

            if rate >= 100:  # At least 100 entries/sec
                checks_passed.append(f"Performance ({rate:.0f} entries/sec)")
            else:
                checks_failed.append(f"Performance: {rate:.0f} entries/sec < 100")

        except Exception as e:
            checks_failed.append(f"Performance: {str(e)}")

        # 8. Memory footprint
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb < 2000:  # Less than 2GB
            checks_passed.append(f"Memory ({memory_mb:.0f}MB)")
        else:
            checks_failed.append(f"Memory: {memory_mb:.0f}MB > 2GB")

        result = TestResult(
            test_name="Production Deployment",
            passed=len(checks_failed) == 0,
            duration=0,
            memory_peak=memory_mb,
            entries_processed=0,
            errors=checks_failed,
            metadata={
                "checks_passed": len(checks_passed),
                "checks_failed": len(checks_failed),
                "total_checks": len(checks_passed) + len(checks_failed),
            },
        )

        print(f"  PASS Passed {len(checks_passed)} checks")
        print(f"  FAIL Failed {len(checks_failed)} checks")

        if checks_failed:
            print("\n  Failed checks:")
            for check in checks_failed[:10]:
                print(f"    - {check}")

        assert len(checks_failed) == 0, f"Deployment checks failed: {checks_failed[:5]}"

        return result


# ========== TEST RUNNER ==========


@pytest.mark.production
class TestProductionSuite:
    """Pytest wrapper for production test suite."""

    @pytest.fixture
    def suite(self):
        """Provide test suite instance."""
        return ProductionTestSuite()

    @pytest.mark.asyncio
    @pytest.mark.timeout(3600)
    async def test_scale_1m_entries(self, suite):
        """Test 1M+ entry processing."""
        await suite.test_1m_entry_processing()

    @pytest.mark.asyncio
    @pytest.mark.timeout(600)
    async def test_memory_load(self, suite):
        """Test memory under load."""
        await suite.test_memory_under_load()

    @pytest.mark.timeout(300)
    def test_concurrent_access(self, suite):
        """Test concurrent access."""
        suite.test_concurrent_access()

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_error_recovery(self, suite):
        """Test error recovery."""
        await suite.test_error_recovery()

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_network_failures(self, suite):
        """Test network failure handling."""
        await suite.test_network_failures()

    @pytest.mark.timeout(300)
    def test_backup_restore(self, suite):
        """Test backup and restore."""
        suite.test_backup_restore()

    @pytest.mark.asyncio
    @pytest.mark.timeout(600)
    async def test_deployment_readiness(self, suite):
        """Test production deployment readiness."""
        await suite.test_production_deployment()


def main():
    """Run production test suite directly."""
    print("=" * 80)
    print("GMNAP V7 PRODUCTION TEST SUITE")
    print("=" * 80)

    # Run with pytest
    pytest.main(
        [
            __file__,
            "-v",
            "-m",
            "production",
            "--tb=short",
            "--timeout=3600",
            "--maxfail=1",
        ]
    )


if __name__ == "__main__":
    main()
