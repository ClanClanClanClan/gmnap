"""
Performance and memory leak testing for all components.
Monitors resource usage, execution time, and memory patterns.
"""

import gc
import random
import string
import tempfile
import threading
import time
import tracemalloc
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List
from unittest.mock import patch

import psutil
import pytest

from src.core.unicode_handler import UnicodeNormalizer, generate_name_variants, normalize_name
from src.utils.database import DatabaseConfig, DatabaseManager
from src.validation.schema import SchemaValidator, validate_entry


class PerformanceProfiler:
    """Performance profiling utility."""

    def __init__(self):
        self.measurements = {}

    @contextmanager
    def measure(self, operation_name: str):
        """Measure execution time and memory usage."""
        # Start memory tracking
        tracemalloc.start()
        gc.collect()

        process = psutil.Process()
        start_memory = process.memory_info().rss
        start_time = time.perf_counter()

        try:
            yield
        finally:
            # Measure results
            end_time = time.perf_counter()
            end_memory = process.memory_info().rss

            # Get memory allocation snapshot
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics("lineno")

            self.measurements[operation_name] = {
                "execution_time": end_time - start_time,
                "memory_start": start_memory,
                "memory_end": end_memory,
                "memory_delta": end_memory - start_memory,
                "top_allocations": top_stats[:5] if top_stats else [],
            }

            tracemalloc.stop()

    def get_measurement(self, operation_name: str) -> Dict[str, Any]:
        """Get measurement results."""
        return self.measurements.get(operation_name, {})

    def assert_performance(
        self, operation_name: str, max_time: float = None, max_memory_mb: float = None
    ):
        """Assert performance constraints."""
        measurement = self.get_measurement(operation_name)
        assert measurement, f"No measurement found for {operation_name}"

        if max_time:
            actual_time = measurement["execution_time"]
            assert (
                actual_time <= max_time
            ), f"Operation {operation_name} took {actual_time:.3f}s, expected <= {max_time}s"

        if max_memory_mb:
            memory_delta_mb = measurement["memory_delta"] / 1024 / 1024
            assert (
                memory_delta_mb <= max_memory_mb
            ), f"Operation {operation_name} used {memory_delta_mb:.2f}MB, expected <= {max_memory_mb}MB"


@pytest.fixture
def profiler():
    """Performance profiler fixture."""
    return PerformanceProfiler()


@pytest.mark.memory
class TestUnicodeNormalizationPerformance:
    """Performance tests for Unicode normalization."""

    def test_normalization_speed_benchmark(self, profiler, unicode_test_strings):
        """Benchmark Unicode normalization speed."""
        normalizer = UnicodeNormalizer()

        # Test different text sizes
        test_cases = [
            ("short_text", "García, José María"),
            ("medium_text", "García, José María " * 100),
            ("long_text", "García, José María " * 1000),
            ("unicode_mixed", unicode_test_strings["mixed_scripts"] * 50),
        ]

        for case_name, text in test_cases:
            with profiler.measure(f"normalize_{case_name}"):
                for _ in range(100):
                    normalized = normalizer.normalize(text)
                    assert isinstance(normalized, str)

            # Assert performance constraints
            if case_name == "short_text":
                profiler.assert_performance(f"normalize_{case_name}", max_time=0.1)
            elif case_name == "medium_text":
                profiler.assert_performance(f"normalize_{case_name}", max_time=0.5)
            elif case_name == "long_text":
                profiler.assert_performance(f"normalize_{case_name}", max_time=2.0)

    def test_script_detection_performance(self, profiler, unicode_test_strings):
        """Test script detection performance."""
        normalizer = UnicodeNormalizer()

        with profiler.measure("script_detection"):
            for _ in range(1000):
                for text in unicode_test_strings.values():
                    if text:  # Skip empty strings
                        script = normalizer.detect_primary_script(text)
                        assert isinstance(script, str)

        profiler.assert_performance("script_detection", max_time=1.0, max_memory_mb=10)

    def test_variant_generation_performance(self, profiler):
        """Test variant generation performance."""
        normalizer = UnicodeNormalizer()

        test_texts = ["Weiß, Hans", "Cæsar, Julius", "García, José María", "Smith-Jones, Mary-Anne"]

        with profiler.measure("variant_generation"):
            for _ in range(500):
                for text in test_texts:
                    variants = normalizer.generate_variants(text)
                    assert isinstance(variants, list)
                    assert len(variants) > 0

        profiler.assert_performance("variant_generation", max_time=2.0, max_memory_mb=20)

    def test_large_text_normalization(self, profiler):
        """Test normalization of very large texts."""
        normalizer = UnicodeNormalizer()

        # Create 1MB text with mixed Unicode
        large_text = (
            "García, José María " + "Παπαδόπουλος, Γιάννης " + "الخوارزمي, محمد " + "田中, 太郎 "
        ) * 10000

        with profiler.measure("large_text_normalization"):
            normalized = normalizer.normalize(large_text)
            assert isinstance(normalized, str)

        profiler.assert_performance("large_text_normalization", max_time=5.0, max_memory_mb=50)

    def test_memory_leak_normalization(self, profiler):
        """Test for memory leaks in normalization."""
        normalizer = UnicodeNormalizer()

        # Baseline measurement
        gc.collect()
        initial_objects = len(gc.get_objects())

        with profiler.measure("memory_leak_test"):
            for i in range(1000):
                text = f"García{i}, José María{i}"
                normalized = normalizer.normalize(text)
                variants = normalizer.generate_variants(normalized)
                script = normalizer.detect_primary_script(normalized)

                # Explicitly delete variables
                del normalized, variants, script

                # Periodic garbage collection
                if i % 100 == 0:
                    gc.collect()

        # Final cleanup and measurement
        gc.collect()
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        # Should not create excessive objects
        assert object_growth < 1000, f"Potential memory leak: {object_growth} objects created"

        # Memory delta should be reasonable
        profiler.assert_performance("memory_leak_test", max_memory_mb=20)


@pytest.mark.memory
class TestSchemaValidationPerformance:
    """Performance tests for schema validation."""

    def test_validation_speed_benchmark(self, profiler, valid_entry_data):
        """Benchmark schema validation speed."""
        validator = SchemaValidator()

        with profiler.measure("schema_validation_speed"):
            for _ in range(1000):
                is_valid, errors = validator.validate_entry(valid_entry_data)
                assert isinstance(is_valid, bool)
                assert isinstance(errors, list)

        profiler.assert_performance("schema_validation_speed", max_time=2.0, max_memory_mb=20)

    def test_large_entry_validation(self, profiler):
        """Test validation of large entries."""
        validator = SchemaValidator()

        # Create large entry with many fields
        large_entry = {
            "García, Juan Carlos": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "García, Juan Carlos",
                "CanonicalNative": "García, Juan Carlos",
                "LanguageOfPublication": [
                    "en",
                    "es",
                    "fr",
                    "de",
                    "it",
                    "pt",
                    "ca",
                    "eu",
                    "gl",
                    "an",
                ],
                "AffiliationTimeline": [
                    {"country": "ES", "from": 2000, "to": 2005},
                    {"country": "US", "from": 2005, "to": 2010},
                    {"country": "GB", "from": 2010, "to": 2015},
                    {"country": "FR", "from": 2015, "to": 2020},
                    {"country": "DE", "from": 2020, "to": None},
                ],
                "Variants": {
                    "Observed": [
                        {
                            "str": f"García{i}, J. C.",
                            "source": "MathSciNet",
                            "accessed": "2025-07-15",
                        }
                        for i in range(100)
                    ],
                    "Synthesised": [
                        {"str": f"Garcia{i} Juan Carlos", "type": "ascii-lossy"} for i in range(100)
                    ],
                },
                "FamilyNameType": "surname",
                "Gender": "male",
                "GenderProvided": True,
                "PreferredPronouns": ["he", "him"],
                "BirthYear": 1975,
                "DeathYear": None,
                "CountryCodes": ["ES"],
                "DiasporaCodes": ["US:2005-2010", "GB:2010-2015", "FR:2015-2020", "DE:2020-"],
                "PrimaryMSC": [
                    {"code": f"{i:02d}A{j:02d}", "source": "zbMATH"}
                    for i in range(10, 20)
                    for j in range(10, 15)
                ],
                "NameEvents": [
                    {
                        "type": "marriage",
                        "year": 2005,
                        "from": "Juan Carlos García",
                        "to": "Juan Carlos García Marín",
                    },
                    {
                        "type": "passport",
                        "year": 2010,
                        "from": "Juan Carlos García Marín",
                        "to": "Juan Carlos García-Marín",
                    },
                ],
                "Advisors": [f"ADVISOR{i:02d}ABCDEFGHIJK" for i in range(5)],
                "ShortFormClusters": {f"J. C. García{i}": i + 1 for i in range(50)},
                "AuthorityIDs": {
                    "ORCID": "0000-0003-1111-2222",
                    "MathSciNet": "203000",
                    "Scopus": {"id": "57189234567", "license": "Elsevier"},
                    "zbMATH": "garcia.juan-carlos",
                    "DBLP": "Garcia:Juan_Carlos",
                    "OpenAlex": "A43637294",
                },
                "Confidence": 96,
                "RegionalExtras": {
                    "primary_surname": "García",
                    "secondary_surname": "Marín",
                    "ipa": "ɡaɾˈθi.a maˈɾin",
                    "nested_data": {
                        "level1": {"level2": {"level3": {"deep_field": "value" * 100}}}
                    },
                },
                "Historic": False,
                "GDPR_DATA": False,
                "SourceNote": "Comprehensive test entry " * 50,
                "Comments": "Free-form curator notes " * 100,
            }
        }

        with profiler.measure("large_entry_validation"):
            is_valid, errors = validator.validate_entry(large_entry)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)

        profiler.assert_performance("large_entry_validation", max_time=1.0, max_memory_mb=30)

    def test_batch_validation_performance(self, profiler):
        """Test batch validation performance."""
        validator = SchemaValidator()

        # Create batch of entries
        entries = []
        for i in range(100):
            entry = {
                f"TestUser{i}, Given{i}": {
                    "GlobalID": f"TEST{i:04d}ABCDEFGHIJKL",
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": f"TestUser{i}, Given{i}",
                    "CanonicalNative": f"TestUser{i}, Given{i}",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "unspecified",
                    "GenderProvided": False,
                    "CountryCodes": ["US"],
                    "Confidence": 50,
                    "Historic": False,
                    "GDPR_DATA": False,
                }
            }
            entries.append(entry)

        with profiler.measure("batch_validation"):
            for entry in entries:
                is_valid, errors = validator.validate_entry(entry)
                assert isinstance(is_valid, bool)
                assert isinstance(errors, list)

        profiler.assert_performance("batch_validation", max_time=3.0, max_memory_mb=50)

    def test_schema_validation_memory_leak(self, profiler):
        """Test for memory leaks in schema validation."""
        validator = SchemaValidator()

        test_entry = {
            "Test, User": {
                "GlobalID": "TESTABCDEFGHIJKLMNOPQ",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "Test, User",
                "CanonicalNative": "Test, User",
                "LanguageOfPublication": ["en"],
                "FamilyNameType": "surname",
                "Gender": "unspecified",
                "GenderProvided": False,
                "CountryCodes": ["US"],
                "Confidence": 50,
                "Historic": False,
                "GDPR_DATA": False,
            }
        }

        gc.collect()
        initial_objects = len(gc.get_objects())

        with profiler.measure("schema_validation_memory_leak"):
            for i in range(1000):
                # Modify entry to prevent caching
                test_entry[f"Test{i}, User{i}"] = test_entry.pop(list(test_entry.keys())[0])
                entry_data = test_entry[f"Test{i}, User{i}"]
                entry_data["CanonicalLatin"] = f"Test{i}, User{i}"

                is_valid, errors = validator.validate_entry(test_entry)

                # Clean up
                del is_valid, errors
                if i % 100 == 0:
                    gc.collect()

        gc.collect()
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        assert object_growth < 1000, f"Potential memory leak: {object_growth} objects created"
        profiler.assert_performance("schema_validation_memory_leak", max_memory_mb=30)


@pytest.mark.memory
class TestDatabasePerformance:
    """Performance tests for database operations."""

    def test_insert_performance_benchmark(self, profiler, temp_db_path):
        """Benchmark database insert performance."""
        config = DatabaseConfig(db_path=str(temp_db_path), use_duckdb=False)

        # Create test entries
        entries = []
        for i in range(1000):
            entry = {
                f"TestUser{i}, Given{i}": {
                    "GlobalID": f"TEST{i:04d}ABCDEFGHIJKL",
                    "CanonicalLatin": f"TestUser{i}, Given{i}",
                    "CanonicalNative": f"TestUser{i}, Given{i}",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "unspecified",
                    "GenderProvided": False,
                    "BirthYear": 1950 + (i % 50),
                    "CountryCodes": ["US"],
                    "Confidence": 50,
                    "Historic": False,
                    "GDPR_DATA": False,
                }
            }
            entries.append(entry)

        with profiler.measure("database_insert_1000"):
            with DatabaseManager(config) as db:
                inserted = db.insert_initial_stats(entries)
                assert inserted == len(entries)

        # Should insert 1000 entries in reasonable time
        profiler.assert_performance("database_insert_1000", max_time=10.0, max_memory_mb=100)

    def test_surname_stats_performance(self, profiler, temp_db_path):
        """Test surname statistics building performance."""
        config = DatabaseConfig(db_path=str(temp_db_path), use_duckdb=False)

        # Pre-populate database
        entries = []
        surnames = ["Smith", "Johnson", "Williams", "Brown", "Jones"] * 200
        for i, surname in enumerate(surnames):
            entry = {
                f"{surname}, Given{i}": {
                    "GlobalID": f"{surname[:4].upper()}{i:010d}"[:22],
                    "CanonicalLatin": f"{surname}, Given{i}",
                    "CanonicalNative": f"{surname}, Given{i}",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "unspecified",
                    "GenderProvided": False,
                    "BirthYear": 1950 + (i % 50),
                    "CountryCodes": ["US"],
                    "Confidence": 50,
                    "Historic": False,
                    "GDPR_DATA": False,
                }
            }
            entries.append(entry)

        with DatabaseManager(config) as db:
            db.insert_initial_stats(entries)

            with profiler.measure("surname_stats_building"):
                stats = db.build_surname_stats()
                assert stats["unique_surnames"] > 0

        profiler.assert_performance("surname_stats_building", max_time=5.0, max_memory_mb=50)

    def test_collision_detection_performance(self, profiler, temp_db_path):
        """Test collision detection performance."""
        config = DatabaseConfig(db_path=str(temp_db_path), use_duckdb=False)

        # Create many entries with similar names
        entries = []
        for i in range(2000):
            surname = f"Smith{i // 100}"  # Create groups of similar surnames
            entry = {
                f"{surname}, Given{i}": {
                    "GlobalID": f"SMITH{i:06d}ABCDEFGH",
                    "CanonicalLatin": f"{surname}, Given{i}",
                    "CanonicalNative": f"{surname}, Given{i}",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "unspecified",
                    "GenderProvided": False,
                    "BirthYear": 1980,  # Same birth decade for collisions
                    "CountryCodes": ["US"],
                    "Confidence": 50,
                    "Historic": False,
                    "GDPR_DATA": False,
                }
            }
            entries.append(entry)

        with DatabaseManager(config) as db:
            db.insert_initial_stats(entries)
            db.build_surname_stats()

            with profiler.measure("collision_detection"):
                collisions = db.detect_collisions(threshold=10)
                assert len(collisions) > 0

        profiler.assert_performance("collision_detection", max_time=10.0, max_memory_mb=100)

    def test_database_memory_usage_scaling(self, profiler, temp_db_path):
        """Test database memory usage scaling."""
        config = DatabaseConfig(db_path=str(temp_db_path), use_duckdb=False)

        # Test scaling with different dataset sizes
        sizes = [100, 500, 1000, 2000]

        for size in sizes:
            entries = []
            for i in range(size):
                entry = {
                    f"ScaleTest{size}_{i}, User{i}": {
                        "GlobalID": f"SCALE{size:04d}{i:06d}AB",
                        "CanonicalLatin": f"ScaleTest{size}_{i}, User{i}",
                        "CanonicalNative": f"ScaleTest{size}_{i}, User{i}",
                        "LanguageOfPublication": ["en"],
                        "FamilyNameType": "surname",
                        "Gender": "unspecified",
                        "GenderProvided": False,
                        "CountryCodes": ["US"],
                        "Confidence": 50,
                        "Historic": False,
                        "GDPR_DATA": False,
                    }
                }
                entries.append(entry)

            with profiler.measure(f"database_scaling_{size}"):
                with DatabaseManager(config) as db:
                    inserted = db.insert_initial_stats(entries)
                    assert inserted == size

                    # Also test read operations
                    stats = db.get_statistics()
                    assert stats["total_entries"] >= size

            # Memory usage should scale reasonably
            max_memory = min(50 + (size / 100) * 10, 200)  # Max 200MB
            profiler.assert_performance(f"database_scaling_{size}", max_memory_mb=max_memory)


@pytest.mark.memory
@pytest.mark.slow
class TestConcurrentPerformance:
    """Test performance under concurrent load."""

    def test_concurrent_normalization_performance(self, profiler):
        """Test Unicode normalization under concurrent load."""
        normalizer = UnicodeNormalizer()

        results = {"processed": 0, "errors": []}
        lock = threading.Lock()

        def worker(worker_id: int, iterations: int):
            """Worker thread for normalization."""
            try:
                for i in range(iterations):
                    text = f"García{worker_id}_{i}, José María{i}"
                    normalized = normalizer.normalize(text)
                    variants = normalizer.generate_variants(normalized)
                    script = normalizer.detect_primary_script(normalized)

                    with lock:
                        results["processed"] += 1

            except Exception as e:
                with lock:
                    results["errors"].append(f"Worker {worker_id}: {e}")

        with profiler.measure("concurrent_normalization"):
            threads = []
            num_workers = 4
            iterations_per_worker = 250

            for i in range(num_workers):
                thread = threading.Thread(target=worker, args=(i, iterations_per_worker))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

        assert len(results["errors"]) == 0, f"Worker errors: {results['errors']}"
        assert results["processed"] == num_workers * iterations_per_worker

        profiler.assert_performance("concurrent_normalization", max_time=5.0, max_memory_mb=100)

    def test_concurrent_validation_performance(self, profiler, temp_schema_path):
        """Test schema validation under concurrent load."""
        results = {"validated": 0, "errors": []}
        lock = threading.Lock()

        def worker(worker_id: int, iterations: int):
            """Worker thread for validation."""
            try:
                validator = SchemaValidator(str(temp_schema_path))

                for i in range(iterations):
                    entry = {
                        f"Worker{worker_id}_{i}, User{i}": {
                            "GlobalID": f"WORK{worker_id:02d}{i:04d}ABCDEF",
                            "UpdatedAt": "2025-07-15T10:30:00Z",
                            "CanonicalLatin": f"Worker{worker_id}_{i}, User{i}",
                            "CanonicalNative": f"Worker{worker_id}_{i}, User{i}",
                            "LanguageOfPublication": ["en"],
                            "FamilyNameType": "surname",
                            "Gender": "unspecified",
                            "GenderProvided": False,
                            "CountryCodes": ["US"],
                            "Confidence": 50,
                            "Historic": False,
                            "GDPR_DATA": False,
                        }
                    }

                    is_valid, errors = validator.validate_entry(entry)

                    with lock:
                        results["validated"] += 1

            except Exception as e:
                with lock:
                    results["errors"].append(f"Worker {worker_id}: {e}")

        with profiler.measure("concurrent_validation"):
            threads = []
            num_workers = 3
            iterations_per_worker = 100

            for i in range(num_workers):
                thread = threading.Thread(target=worker, args=(i, iterations_per_worker))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

        assert len(results["errors"]) == 0, f"Worker errors: {results['errors']}"
        assert results["validated"] == num_workers * iterations_per_worker

        profiler.assert_performance("concurrent_validation", max_time=10.0, max_memory_mb=150)


@pytest.mark.memory
class TestResourceExhaustionScenarios:
    """Test behavior under resource exhaustion."""

    def test_memory_exhaustion_normalization(self, profiler):
        """Test normalization under memory pressure."""
        normalizer = UnicodeNormalizer()

        # Create increasingly large texts
        base_text = "García, José María Ñoño " * 1000

        for multiplier in [1, 2, 5, 10]:
            large_text = base_text * multiplier
            size_mb = len(large_text.encode("utf-8")) / 1024 / 1024

            try:
                with profiler.measure(f"memory_exhaustion_{size_mb:.1f}mb"):
                    normalized = normalizer.normalize(large_text)
                    assert isinstance(normalized, str)

                # Should complete within reasonable memory bounds
                profiler.assert_performance(
                    f"memory_exhaustion_{size_mb:.1f}mb",
                    max_memory_mb=size_mb * 3,  # Allow 3x expansion
                )

            except MemoryError:
                # Acceptable to run out of memory on very large inputs
                break

    def test_cpu_intensive_operations(self, profiler):
        """Test CPU-intensive operations."""
        normalizer = UnicodeNormalizer()
        validator = SchemaValidator()

        # CPU-intensive normalization
        with profiler.measure("cpu_intensive_normalization"):
            for i in range(10000):
                text = f"Test{i % 1000}, User{i % 1000}"
                normalized = normalizer.normalize(text)
                script = normalizer.detect_primary_script(normalized)

        # CPU-intensive validation
        base_entry = {
            "Test, User": {
                "GlobalID": "TESTABCDEFGHIJKLMNOPQ",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "Test, User",
                "CanonicalNative": "Test, User",
                "LanguageOfPublication": ["en"],
                "FamilyNameType": "surname",
                "Gender": "unspecified",
                "GenderProvided": False,
                "CountryCodes": ["US"],
                "Confidence": 50,
                "Historic": False,
                "GDPR_DATA": False,
            }
        }

        with profiler.measure("cpu_intensive_validation"):
            for i in range(5000):
                # Modify entry to prevent caching
                entry = {f"Test{i}, User{i}": base_entry["Test, User"].copy()}
                entry[f"Test{i}, User{i}"]["CanonicalLatin"] = f"Test{i}, User{i}"

                is_valid, errors = validator.validate_entry(entry)

        # Should complete within reasonable time
        profiler.assert_performance("cpu_intensive_normalization", max_time=30.0)
        profiler.assert_performance("cpu_intensive_validation", max_time=30.0)
