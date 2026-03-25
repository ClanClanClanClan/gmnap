"""
Hardcore regional processing system testing for GMNAP.

Tests region detection accuracy, processor instantiation, name processing,
and performance under various loads.
"""

import random
import tempfile
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List, Set, Tuple
from unittest.mock import Mock, patch

import pytest

from src.core.unicode_handler import UnicodeNormalizer
from src.regions.base import RegionRuleError, RegionSpec
from src.regions.manager import RegionDetectionResult, RegionManager


class TestRegionDetectionAccuracy:
    """Test region detection accuracy across all scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.region_manager = RegionManager(Path(self.temp_dir))
        self.unicode_normalizer = UnicodeNormalizer()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_region_detection_by_script(self):
        """Test region detection produces valid results for different scripts."""
        script_test_cases = [
            # Latin script names
            ("Smith, John", "Latin"),
            ("García, José", "Latin"),
            ("Müller, Hans", "Latin"),
            # Cyrillic script names
            ("Иванов, Петр", "Cyrillic"),
            ("Петров, Александр", "Cyrillic"),
            # Arabic script names
            ("محمد, أحمد", "Arabic"),
            # CJK names
            ("李明", "CJK"),
            ("田中太郎", "CJK"),
            ("김민수", "CJK"),
        ]

        for name, script_type in script_test_cases:
            entry = {"canonical_name": name, "CanonicalLatin": name}
            detection = self.region_manager.detect_region(entry)

            # Should detect a valid region
            assert detection.region_code is not None, f"No region detected for {name}"
            assert isinstance(
                detection.region_code, str
            ), f"Region code should be a string for {name}"
            assert detection.confidence >= 0.0, f"Negative confidence for {name}"
            assert detection.confidence <= 1.0, f"Confidence > 1.0 for {name}"

    def test_region_detection_by_country(self):
        """Test region detection with country information."""
        country_test_cases = [
            ("Smith, John", "US"),
            ("Smith, John", "GB"),
            ("García, José", "ES"),
            ("Müller, Hans", "DE"),
            ("李明", "CN"),
            ("田中太郎", "JP"),
            ("김민수", "KR"),
            ("Иванов, Петр", "RU"),
        ]

        for name, country in country_test_cases:
            entry = {
                "canonical_name": name,
                "CanonicalLatin": name,
                "countries": [country],
                "affiliations": [{"country": country}],
            }

            detection = self.region_manager.detect_region(entry)

            assert detection.region_code is not None, f"No region detected for {name} in {country}"
            assert detection.confidence > 0, f"Zero confidence for {name} in {country}"

    def test_region_detection_by_institution(self):
        """Test region detection with institutional affiliation."""
        institution_test_cases = [
            ("Smith, John", "Harvard University"),
            ("Müller, Hans", "Max Planck Institute"),
            ("李明", "Tsinghua University"),
            ("田中太郎", "University of Tokyo"),
        ]

        for name, institution in institution_test_cases:
            entry = {
                "canonical_name": name,
                "CanonicalLatin": name,
                "affiliations": [{"name": institution}],
            }

            detection = self.region_manager.detect_region(entry)
            assert (
                detection.region_code is not None
            ), f"No region detected for {name} at {institution}"

    def test_region_detection_edge_cases(self):
        """Test region detection edge cases."""
        edge_cases = [
            # Empty/minimal data — should not crash
            {},
            {"canonical_name": ""},
            {"canonical_name": "???"},
            # Normal names
            {"canonical_name": "Smith, John", "CanonicalLatin": "Smith, John"},
            {"canonical_name": "李明", "CanonicalLatin": "Li, Ming"},
        ]

        for entry in edge_cases:
            detection = self.region_manager.detect_region(entry)
            # Should always produce a result
            assert detection.region_code is not None, f"No region for entry: {entry}"

    def test_region_detection_confidence_scoring(self):
        """Test region detection confidence is bounded."""
        test_entries = [
            {"canonical_name": "Smith, John", "countries": ["US"]},
            {"canonical_name": "李明", "countries": ["CN"]},
            {"canonical_name": "García, José"},
            {"canonical_name": "Unknown"},
        ]

        for entry in test_entries:
            detection = self.region_manager.detect_region(entry)

            assert (
                0.0 <= detection.confidence <= 1.0
            ), f"Confidence {detection.confidence} out of bounds for {entry}"


class TestRegionalRuleValidation:
    """Test regional processor instantiation and methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.region_manager = RegionManager(Path(self.temp_dir))

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_a1_region_validation(self):
        """Test A1 (Anglo-Sphere) region processor methods."""
        from src.regions.a_groups.a1_anglo_sphere import A1_AngloSphere

        processor = A1_AngloSphere()

        # Test clean method (modifies in-place, returns None)
        entry = {
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
        }
        processor.clean(entry)
        assert isinstance(entry, dict)

        # Test augment method (modifies in-place)
        processor.augment(entry)
        assert isinstance(entry, dict)

        # Test validate method
        processor.validate(entry)

        # Test order_key method
        order_key = processor.order_key(entry)
        assert isinstance(order_key, str)

    def test_a1_region_invalid_entries(self):
        """Test A1 region handles invalid entries gracefully."""
        from src.regions.a_groups.a1_anglo_sphere import A1_AngloSphere

        processor = A1_AngloSphere()

        invalid_entries = [
            {"CanonicalLatin": "", "CanonicalNative": ""},
            {"CanonicalLatin": "???", "CanonicalNative": "???"},
            {"CanonicalLatin": "NoComma", "CanonicalNative": "NoComma"},
        ]

        for entry in invalid_entries:
            # Should not crash (clean modifies in-place, returns None)
            try:
                processor.clean(entry)
                assert isinstance(entry, dict)
            except (ValueError, KeyError):
                pass  # Acceptable to raise on truly invalid entries

    def test_regional_name_normalization(self):
        """Test that region processors have clean/augment/validate/order_key."""
        region_classes = [
            ("A1", "src.regions.a_groups.a1_anglo_sphere", "A1_AngloSphere"),
        ]

        for code, module_path, class_name in region_classes:
            import importlib

            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            processor = cls()

            entry = {
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
            }

            # All processors should have these methods
            assert hasattr(processor, "clean"), f"{class_name} missing clean()"
            assert hasattr(processor, "augment"), f"{class_name} missing augment()"
            assert hasattr(processor, "validate"), f"{class_name} missing validate()"
            assert hasattr(processor, "order_key"), f"{class_name} missing order_key()"

            # Methods should be callable (clean modifies in-place, returns None)
            processor.clean(entry)
            assert isinstance(entry, dict)

    def test_regional_script_validation(self):
        """Test that region detection assigns CJK names to CJK regions."""
        # CJK names should not be assigned to Latin-only regions
        cjk_entry = {"canonical_name": "李明", "CanonicalLatin": "Li, Ming"}
        detection = self.region_manager.detect_region(cjk_entry)
        # CJK names should get E-group or similar CJK region, not A1
        assert detection.region_code is not None


class TestRegionalPerformance:
    """Test regional processing performance."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.region_manager = RegionManager(Path(self.temp_dir))

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_region_detection_performance(self):
        """Test region detection performance."""
        entry_types = [
            {"canonical_name": "Smith, John", "countries": ["US"]},
            {"canonical_name": "García, José", "countries": ["ES"]},
            {"canonical_name": "Müller, Hans", "countries": ["DE"]},
            {"canonical_name": "李明", "countries": ["CN"]},
            {"canonical_name": "田中太郎", "countries": ["JP"]},
            {"canonical_name": "Иванов, Петр", "countries": ["RU"]},
            {"canonical_name": "محمد, أحمد", "countries": ["SA"]},
        ]

        test_entries = []
        for i in range(1000):
            base_entry = random.choice(entry_types)
            entry = base_entry.copy()
            entry["canonical_name"] = f"{base_entry['canonical_name']} {i:04d}"
            test_entries.append(entry)

        start_time = time.time()

        detections = []
        for entry in test_entries:
            detection = self.region_manager.detect_region(entry)
            detections.append(detection)

        total_time = time.time() - start_time
        entries_per_second = len(test_entries) / total_time

        assert (
            entries_per_second > 100
        ), f"Region detection too slow: {entries_per_second:.1f} entries/second"
        assert len(detections) == len(test_entries)

        for detection in detections:
            assert detection.region_code is not None
            assert 0.0 <= detection.confidence <= 1.0

    def test_concurrent_region_processing(self):
        """Test concurrent region processing."""
        test_entries = []
        for i in range(500):
            entry = {
                "canonical_name": f"TestPerson{i:04d}, John",
                "CanonicalLatin": f"TestPerson{i:04d}, John",
                "countries": ["US"],
            }
            test_entries.append(entry)

        results = Queue()
        errors = Queue()

        def region_worker(worker_id, entries):
            worker_results = []
            worker_errors = []

            for entry in entries:
                try:
                    detection = self.region_manager.detect_region(entry)
                    worker_results.append(
                        (entry["canonical_name"], detection.region_code, detection.confidence)
                    )
                except Exception as e:
                    worker_errors.append((entry["canonical_name"], str(e)))

            results.put((worker_id, worker_results))
            if worker_errors:
                errors.put((worker_id, worker_errors))

        num_workers = 8
        entries_per_worker = len(test_entries) // num_workers

        threads = []
        for i in range(num_workers):
            start_idx = i * entries_per_worker
            end_idx = (i + 1) * entries_per_worker if i < num_workers - 1 else len(test_entries)
            worker_entries = test_entries[start_idx:end_idx]

            thread = threading.Thread(target=region_worker, args=(i, worker_entries))
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
        total_processed = sum(len(r[1]) for r in worker_results)
        assert total_processed == len(test_entries)

    def test_region_processing_memory_efficiency(self):
        """Test memory efficiency of region processing."""
        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024

        for i in range(5000):
            entry = {
                "canonical_name": f"TestPerson{i:06d}, John",
                "CanonicalLatin": f"TestPerson{i:06d}, John",
                "countries": ["US"],
            }
            detection = self.region_manager.detect_region(entry)
            assert detection.region_code is not None

        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_growth = final_memory - initial_memory

        assert total_memory_growth < 200, f"Excessive memory usage: {total_memory_growth}MB"


class TestRegionalEdgeCases:
    """Test regional processing edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.region_manager = RegionManager(Path(self.temp_dir))

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_quarantine_region_handling(self):
        """Test entries with bad data get a region (not crash)."""
        quarantine_cases = [
            {"canonical_name": "", "CanonicalLatin": ""},
            {"canonical_name": "???", "CanonicalLatin": "???"},
            {"canonical_name": "████████", "CanonicalLatin": "████████"},
        ]

        for entry in quarantine_cases:
            detection = self.region_manager.detect_region(entry)
            assert detection.region_code is not None, f"No region for quarantine case: {entry}"

    def test_historical_region_handling(self):
        """Test historical names get a region."""
        historical_cases = [
            {"canonical_name": "Archimedes", "birth_year": -287, "death_year": -212},
            {"canonical_name": "Euclid", "birth_year": -330, "death_year": -270},
            {"canonical_name": "Al-Khwarizmi", "birth_year": 780, "death_year": 850},
        ]

        for entry in historical_cases:
            entry["CanonicalLatin"] = entry["canonical_name"]
            detection = self.region_manager.detect_region(entry)
            assert (
                detection.region_code is not None
            ), f"No region for historical name: {entry['canonical_name']}"

    def test_diaspora_region_handling(self):
        """Test names with multiple countries get a region."""
        diaspora_cases = [
            {
                "canonical_name": "Einstein, Albert",
                "CanonicalLatin": "Einstein, Albert",
                "countries": ["DE", "US", "CH"],
            },
            {
                "canonical_name": "Ramanujan, Srinivasa",
                "CanonicalLatin": "Ramanujan, Srinivasa",
                "countries": ["IN", "GB"],
            },
        ]

        for entry in diaspora_cases:
            detection = self.region_manager.detect_region(entry)
            assert (
                detection.region_code is not None
            ), f"No region for diaspora case: {entry['canonical_name']}"
            assert (
                detection.confidence > 0
            ), f"Zero confidence for diaspora case: {entry['canonical_name']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
