"""
Global pytest configuration and fixtures for GMNAP testing.
Provides shared fixtures, test utilities, and configuration.
"""

import gc
import json
import logging
import os
import shutil
import sys
import tempfile
import tracemalloc
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import Mock, patch

import psutil
import pytest

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "paranoid: marks tests as paranoid/exhaustive tests")
    config.addinivalue_line("markers", "smoke: marks tests as smoke tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "regression: marks tests as regression tests")


# Test configuration
@pytest.fixture(scope="session")
def test_config():
    """Global test configuration."""
    return {
        "max_memory_mb": 100,  # Memory limit for tests
        "timeout_seconds": 30,  # Test timeout
        "stress_test_iterations": 1000,
        "property_test_examples": 100,
        "unicode_test_scripts": [
            "Latin", "Cyrillic", "Greek", "Arabic", "Hebrew", 
            "Devanagari", "Bengali", "Tamil", "Thai", "Khmer",
            "CJK", "Hangul", "Kana", "Armenian", "Georgian"
        ]
    }


# Memory monitoring fixtures
@pytest.fixture(autouse=True)
def memory_monitor():
    """Monitor memory usage during tests."""
    tracemalloc.start()
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    yield
    
    # Check for memory leaks
    current_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_growth = current_memory - initial_memory
    
    if memory_growth > 50:  # 50MB threshold
        logger.warning(f"Potential memory leak detected: {memory_growth:.2f}MB growth")
        
        # Get memory traces
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        logger.warning("Top memory allocations:")
        for stat in top_stats[:5]:
            logger.warning(f"  {stat}")
    
    tracemalloc.stop()
    gc.collect()


# Temporary directory fixtures
@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = tempfile.mkdtemp(prefix="gmnap_test_")
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_db_path(temp_dir):
    """Create temporary database path."""
    return temp_dir / "test.db"


@pytest.fixture
def temp_schema_path(temp_dir):
    """Create temporary schema file."""
    schema_path = temp_dir / "schema.json"
    
    # Copy real schema to temp location
    real_schema = Path(__file__).parent.parent / "docs" / "schema.json"
    if real_schema.exists():
        shutil.copy2(real_schema, schema_path)
    
    return schema_path


# Test data fixtures
@pytest.fixture
def valid_entry_data():
    """Valid entry data for testing."""
    return {
        "García, Juan Carlos": {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-07-15T10:30:00Z",
            "CanonicalLatin": "García, Juan Carlos",
            "CanonicalNative": "García, Juan Carlos",
            "LanguageOfPublication": ["en", "es"],
            "FamilyNameType": "surname",
            "Gender": "male",
            "GenderProvided": True,
            "CountryCodes": ["ES"],
            "Confidence": 96,
            "Historic": False,
            "GDPR_DATA": False
        }
    }


@pytest.fixture
def malformed_entry_data():
    """Malformed entry data for security testing."""
    return {
        "Smith, John": {
            "GlobalID": "INVALID_ID",
            "UpdatedAt": "not-a-date",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "LanguageOfPublication": ["invalid-lang-code"],
            "FamilyNameType": "invalid-type",
            "Gender": "invalid-gender",
            "GenderProvided": "not-boolean",
            "CountryCodes": ["INVALID"],
            "Confidence": 150,  # Out of range
            "Historic": "not-boolean",
            "GDPR_DATA": "not-boolean"
        }
    }


@pytest.fixture
def unicode_test_strings():
    """Unicode test strings for comprehensive testing."""
    return {
        "basic_latin": "Smith, John",
        "accented_latin": "García, José María",
        "ligatures": "Cæsar, Œuvre",
        "sharp_s": "Weiß, Hans",
        "cyrillic": "Иванов, Иван",
        "greek": "Παπαδόπουλος, Γιάννης",
        "arabic": "الخوارزمي, محمد",
        "hebrew": "כהן, דוד",
        "devanagari": "शर्मा, राम",
        "bengali": "শর্মা, রাম",
        "tamil": "முருகன், சுந்தர்",
        "thai": "สมิท, จอห์น",
        "khmer": "ស្មីត, ចន",
        "cjk": "田中, 太郎",
        "hangul": "김, 철수",
        "kana": "たなか, たろう",
        "armenian": "Հայրապետյան, Արամ",
        "georgian": "ჯავახიშვილი, იაკობ",
        "mixed_scripts": "Smith-田中, John-太郎",
        "rtl_text": "الخوارزمي, محمد بن موسى",
        "combining_chars": "José María García",
        "zalgo_text": "Z̴̢̰̗̞̈́̀͘ă̷̧̺̙̯̈́l̴̨̰̟̈́̚g̷̢̰̗̞̈́̀͘ō̷̢̰̗̞̈́̀͘",
        "null_bytes": "Smith\x00John",
        "control_chars": "Smith\x01\x02\x03John",
        "emoji": "Smith 😀, John 🎉",
        "very_long": "a" * 1000,
        "empty": "",
        "whitespace_only": "   ",
        "unicode_normalization": "é" + "́",  # e + acute + acute
        "bidi_text": "Hello مرحبا World",
        "surrogates": "𝕊𝕞𝕚𝕥𝕙, 𝕁𝕠𝕙𝕟",
        "zero_width": "Smith\u200b\u200c\u200d, John",
        "private_use": "Smith\ue000, John\ue001"
    }


@pytest.fixture
def injection_test_payloads():
    """Injection test payloads for security testing."""
    return {
        "sql_injection": [
            "Smith'; DROP TABLE users; --",
            "Smith' OR '1'='1",
            "Smith\"; DELETE FROM entries; --",
            "Smith' UNION SELECT * FROM passwords --"
        ],
        "xss_injection": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "Smith<svg onload=alert('xss')>"
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ],
        "command_injection": [
            "Smith; rm -rf /",
            "Smith && cat /etc/passwd",
            "Smith | nc -l -p 1234 -e /bin/bash",
            "Smith`whoami`"
        ],
        "format_string": [
            "Smith %s %x %p",
            "Smith %n",
            "Smith %1000000d",
            "Smith %.*s"
        ],
        "unicode_attacks": [
            "Smith\u0000John",  # Null byte
            "Smith\ufeffJohn",  # BOM
            "Smith\u202eJohn",  # Right-to-left override
            "Smith\u2066John\u2069"  # Isolate characters
        ]
    }


# Mock fixtures
@pytest.fixture
def mock_duckdb():
    """Mock DuckDB for testing without actual database."""
    with patch('src.utils.database.duckdb') as mock_db:
        mock_conn = Mock()
        mock_db.connect.return_value = mock_conn
        yield mock_db, mock_conn


@pytest.fixture
def mock_sqlite():
    """Mock SQLite for testing without actual database."""
    with patch('sqlite3.connect') as mock_connect:
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        yield mock_connect, mock_conn


@pytest.fixture
def mock_memory_pressure():
    """Mock memory pressure conditions."""
    with patch('psutil.virtual_memory') as mock_memory:
        mock_memory.return_value.available = 500 * 1024 * 1024  # 500MB
        yield mock_memory


# Error injection fixtures
@pytest.fixture
def error_injector():
    """Utility for injecting errors during testing."""
    class ErrorInjector:
        def __init__(self):
            self.error_count = 0
            self.max_errors = 3
            
        def maybe_raise(self, error_type=Exception, message="Injected error"):
            if self.error_count < self.max_errors:
                self.error_count += 1
                raise error_type(message)
            
        def reset(self):
            self.error_count = 0
    
    return ErrorInjector()


# Performance monitoring fixtures
@pytest.fixture
def performance_monitor():
    """Monitor test performance."""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.perf_counter()
            
        def stop(self):
            self.end_time = time.perf_counter()
            
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
            
        def assert_faster_than(self, seconds):
            elapsed = self.elapsed()
            assert elapsed is not None, "Performance monitor not properly started/stopped"
            assert elapsed < seconds, f"Operation took {elapsed:.3f}s, expected < {seconds}s"
    
    return PerformanceMonitor()


# Test utilities
@pytest.fixture
def test_utils():
    """Test utility functions."""
    class TestUtils:
        @staticmethod
        def create_large_string(size_mb):
            """Create a large string for memory testing."""
            return "a" * (size_mb * 1024 * 1024)
            
        @staticmethod
        def create_nested_dict(depth, width=2):
            """Create nested dictionary for recursion testing."""
            if depth == 0:
                return "leaf"
            return {f"key_{i}": TestUtils.create_nested_dict(depth - 1, width) 
                   for i in range(width)}
                   
        @staticmethod
        def generate_random_unicode(length=100):
            """Generate random Unicode string."""
            import random
            import unicodedata

            # Generate random Unicode code points
            chars = []
            for _ in range(length):
                # Avoid surrogates and private use areas
                while True:
                    code_point = random.randint(0x0000, 0x10FFFF)
                    if (0xD800 <= code_point <= 0xDFFF or  # Surrogates
                        0xE000 <= code_point <= 0xF8FF or   # Private use
                        0xFFF0 <= code_point <= 0xFFFF):    # Specials
                        continue
                    try:
                        char = chr(code_point)
                        if unicodedata.category(char) not in ['Cc', 'Cf', 'Cs']:
                            chars.append(char)
                            break
                    except ValueError:
                        continue
            
            return ''.join(chars)
            
        @staticmethod
        def assert_no_memory_leak(func, *args, **kwargs):
            """Assert function doesn't leak memory."""
            gc.collect()
            initial_objects = len(gc.get_objects())
            
            for _ in range(10):
                func(*args, **kwargs)
                gc.collect()
            
            final_objects = len(gc.get_objects())
            growth = final_objects - initial_objects
            
            assert growth < 100, f"Potential memory leak: {growth} objects created"
    
    return TestUtils


# Database fixtures
@pytest.fixture
def db_config(temp_db_path):
    """Database configuration for testing."""
    from src.utils.database import DatabaseConfig
    
    return DatabaseConfig(
        db_path=str(temp_db_path),
        memory_threshold_gb=0.1,  # Low threshold for testing
        use_duckdb=True,
        enable_wal=False,  # Disable WAL for faster tests
        cache_size_mb=1    # Small cache for testing
    )


# Schema fixtures
@pytest.fixture
def schema_config(temp_schema_path):
    """Schema configuration for testing."""
    return {
        "schema_path": str(temp_schema_path),
        "strict_validation": True,
        "custom_validators": True
    }


# Test markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "stress: marks tests as stress tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )
    config.addinivalue_line(
        "markers", "property: marks tests as property-based tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "memory: marks tests as memory-intensive"
    )


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on test names
        if "stress" in item.name:
            item.add_marker(pytest.mark.stress)
        if "security" in item.name or "injection" in item.name:
            item.add_marker(pytest.mark.security)
        if "property" in item.name:
            item.add_marker(pytest.mark.property)
        if "memory" in item.name:
            item.add_marker(pytest.mark.memory)
        if "integration" in item.name:
            item.add_marker(pytest.mark.integration)
        if "slow" in item.name or "large" in item.name:
            item.add_marker(pytest.mark.slow)


# Test reporting hooks
def pytest_runtest_logreport(report):
    """Log test results."""
    if report.when == "call":
        if report.failed:
            logger.error(f"Test {report.nodeid} FAILED: {report.longrepr}")
        elif report.passed:
            logger.info(f"Test {report.nodeid} PASSED")


# Cleanup hooks
def pytest_sessionfinish(session, exitstatus):
    """Clean up after test session."""
    # Force garbage collection
    gc.collect()
    
    # Log final memory usage (with error handling for closed streams)
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"Final memory usage: {memory_mb:.2f}MB")
    except (ValueError, OSError):
        # Logger stream may be closed during pytest shutdown
        pass
    
    # Clean up temporary files
    import tempfile
    temp_dir = tempfile.gettempdir()
    for file in Path(temp_dir).glob("gmnap_test_*"):
        try:
            if file.is_dir():
                shutil.rmtree(file)
            else:
                file.unlink()
        except OSError:
            pass