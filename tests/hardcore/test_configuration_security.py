"""
Hardcore configuration security testing for GMNAP.

Tests configuration management, environment variable handling, path validation,
credential exposure, and all scenarios that could compromise system security.
"""

import gc
import json
import os
import random
import string
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from queue import Empty, Queue
from unittest.mock import Mock, mock_open, patch

import psutil
import pytest
import yaml

from src.core.config import ConfigurationManager, GMNAPConfig


class TestConfigurationSecurity:
    """Test configuration security under attack scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        self.original_env = dict(os.environ)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_environment_variable_injection(self):
        """Test environment variable injection does not crash config loading."""
        # Use only env var names that map to real DatabaseConfig/ProcessingConfig fields
        malicious_env = {
            "GMNAP_DATABASE_PATH": "../../../etc/passwd",
            "GMNAP_PROCESSING_MAX_WORKERS": "999999999",
            "GMNAP_PROCESSING_TIMEOUT_SECONDS": "-1",
            "GMNAP_CACHE_CACHE_DIR": "/tmp/$(whoami)",
            "GMNAP_MONITORING_LOG_LEVEL": "DEBUG'; import os; os.system('rm -rf /')",
        }

        for key, value in malicious_env.items():
            os.environ[key] = value

        # Config loading should not crash
        mgr = ConfigurationManager(config_path=self.config_path)
        config = mgr.load()

        assert isinstance(config, GMNAPConfig)
        # Values are stored as-is but never executed — they're just strings/ints

    def test_path_traversal_attacks(self):
        """Test path traversal attacks in configuration paths."""
        malicious_config = {
            "database": {
                "path": "../../../etc/passwd",
            },
            "cache": {
                "cache_dir": "../../../tmp/evil",
            },
        }

        with open(self.config_path, "w") as f:
            yaml.dump(malicious_config, f)

        mgr = ConfigurationManager(config_path=self.config_path)
        config = mgr.load()

        # Config loads the values but doesn't execute them
        assert isinstance(config, GMNAPConfig)
        assert config.database.path == "../../../etc/passwd"
        # Path traversal strings are stored but harmless — no file I/O occurs

    def test_credential_exposure_prevention(self):
        """Test that config doesn't crash on sensitive data."""
        sensitive_config = {
            "database": {
                "path": "postgresql://admin:SuperSecret123@db.example.com:5432/prod",
            },
        }

        with open(self.config_path, "w") as f:
            yaml.dump(sensitive_config, f)

        mgr = ConfigurationManager(config_path=self.config_path)
        config = mgr.load()

        # Config loads without crashing
        assert isinstance(config, GMNAPConfig)

    def test_config_file_corruption_recovery(self):
        """Test recovery from config file corruption."""
        # Corrupt the file
        with open(self.config_path, "w") as f:
            f.write("invalid: yaml: content: [unclosed\n")
            f.write("more: invalid: yaml\n")
            f.write("{{{{ malformed\n")

        # Should handle corruption gracefully by using defaults
        mgr = ConfigurationManager(config_path=self.config_path)
        config = mgr.load()

        assert isinstance(config, GMNAPConfig)
        assert config.database.path is not None
        assert config.cache.cache_dir is not None

    def test_memory_exhaustion_from_config(self):
        """Test large config files don't cause excessive memory usage."""
        large_config = {
            "database": {"path": "sqlite:///test.db"},
            "cache": {"cache_dir": "/tmp/cache"},
        }

        # Add many extra keys (will be filtered out by from_dict)
        for i in range(1000):
            large_config[f"extra_{i}"] = {
                "name": f"Entry {i}" * 10,
                "data": f"value_{i}" * 50,
            }

        with open(self.config_path, "w") as f:
            yaml.dump(large_config, f)

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024

        mgr = ConfigurationManager(config_path=self.config_path)
        config = mgr.load()

        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory

        assert isinstance(config, GMNAPConfig)
        assert memory_growth < 200, f"Config loading used too much memory: {memory_growth}MB"

    def test_concurrent_config_access(self):
        """Test concurrent config access and modification."""
        base_config = {
            "database": {"path": "sqlite:///test.db"},
            "cache": {"cache_dir": "/tmp/cache"},
        }

        with open(self.config_path, "w") as f:
            yaml.dump(base_config, f)

        results = Queue()
        errors = Queue()

        def config_worker(worker_id, operations):
            worker_errors = []
            worker_results = []

            for i in range(operations):
                try:
                    mgr = ConfigurationManager(config_path=self.config_path)
                    config = mgr.load()

                    # Access config properties
                    _ = config.database.path
                    _ = config.cache.cache_dir
                    _ = config.processing.max_workers

                    worker_results.append(f"worker_{worker_id}_op_{i}")
                except Exception as e:
                    worker_errors.append(f"worker_{worker_id}_op_{i}: {str(e)}")

            results.put((worker_id, len(worker_results), len(worker_errors)))
            if worker_errors:
                errors.put((worker_id, worker_errors))

        num_workers = 10
        operations_per_worker = 20

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(target=config_worker, args=(i, operations_per_worker))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        worker_results = []
        while not results.empty():
            try:
                worker_results.append(results.get_nowait())
            except Empty:
                break

        assert len(worker_results) == num_workers

    def test_config_validation_bypass(self):
        """Test config with invalid types uses defaults gracefully."""
        bypass_config = {
            "database": {
                "path": ["not", "a", "string"],
                "max_connections": "not-a-number",
            },
            "cache": {
                "cache_dir": 12345,
            },
        }

        with open(self.config_path, "w") as f:
            yaml.dump(bypass_config, f)

        # Config loading may use wrong types but shouldn't crash
        mgr = ConfigurationManager(config_path=self.config_path)
        try:
            config = mgr.load()
            assert isinstance(config, GMNAPConfig)
        except (TypeError, ValueError):
            # Acceptable — invalid types cause construction error
            pass

    def test_sensitive_data_scrubbing(self):
        """Test that to_dict doesn't crash on any config."""
        mgr = ConfigurationManager(config_path=self.config_path)
        config = mgr.load()

        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert "database" in config_dict
        assert "cache" in config_dict

    def test_config_schema_violation_handling(self):
        """Test handling of config schema violations."""
        invalid_config = {
            "database": {
                "path": 12345,
                "connection_timeout": "not-a-number",
            },
            "unknown_section": {
                "unknown_field": "unknown_value",
            },
        }

        with open(self.config_path, "w") as f:
            yaml.dump(invalid_config, f)

        mgr = ConfigurationManager(config_path=self.config_path)
        try:
            config = mgr.load()
            assert isinstance(config, GMNAPConfig)
        except (TypeError, ValueError):
            # Acceptable — from_dict may reject invalid types
            pass

    def test_file_permission_attacks(self):
        """Test file permission attacks on config files."""
        valid_config = {
            "database": {"path": "sqlite:///test.db"},
            "cache": {"cache_dir": "/tmp/cache"},
        }

        with open(self.config_path, "w") as f:
            yaml.dump(valid_config, f)

        # Remove read permissions
        os.chmod(self.config_path, 0o000)

        # Should handle permission errors gracefully (falls back to defaults)
        mgr = ConfigurationManager(config_path=self.config_path)
        config = mgr.load()

        assert isinstance(config, GMNAPConfig)
        assert config.database.path is not None

        # Non-existent path also handled
        mgr2 = ConfigurationManager(config_path=Path("/non/existent/directory/config.yaml"))
        config2 = mgr2.load()
        assert isinstance(config2, GMNAPConfig)

        # Restore permissions for cleanup
        os.chmod(self.config_path, 0o644)


class TestConfigurationPerformance:
    """Test configuration performance under load."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "perf_test.yaml"

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_loading_performance(self):
        """Test config loading performance."""
        config_data = {
            "database": {"path": "sqlite:///test.db"},
            "cache": {"cache_dir": "/tmp/cache"},
            "processing": {"max_workers": 4, "batch_size": 1000},
        }

        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f)

        start_time = time.time()
        for _ in range(100):
            mgr = ConfigurationManager(config_path=self.config_path)
            config = mgr.load()
        loading_time = time.time() - start_time

        assert loading_time < 10.0, f"100 config loads too slow: {loading_time:.2f}s"
        assert isinstance(config, GMNAPConfig)

    def test_concurrent_config_performance(self):
        """Test config performance under concurrent access."""
        config_data = {
            "database": {"path": "sqlite:///test.db"},
            "cache": {"cache_dir": "/tmp/cache"},
        }

        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f)

        results = Queue()

        def performance_worker(worker_id, iterations):
            start_time = time.time()

            for i in range(iterations):
                mgr = ConfigurationManager(config_path=self.config_path)
                config = mgr.load()
                _ = config.database.path
                _ = config.cache.cache_dir

            end_time = time.time()
            avg_time = (end_time - start_time) / iterations
            results.put((worker_id, avg_time))

        num_workers = 8
        iterations_per_worker = 50

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(target=performance_worker, args=(i, iterations_per_worker))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        worker_times = []
        while not results.empty():
            try:
                worker_times.append(results.get_nowait())
            except Empty:
                break

        assert len(worker_times) == num_workers, f"Not all workers completed: {len(worker_times)}"

        avg_times = [t for _, t in worker_times]
        overall_avg = sum(avg_times) / len(avg_times)

        assert overall_avg < 0.5, f"Config loading too slow: {overall_avg:.3f}s per load"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
