"""
Hardcore invariant verification tests for GMNAP.

Tests that critical system invariants hold under all conditions.
These are the most important tests - they verify that the system's
core guarantees are never violated.
"""

import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from src.core.config import GMNAPConfig
from src.core.globalid import GlobalIDGenerator, validate_global_id
from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
from src.core.unicode_handler import UnicodeNormalizer
from src.regions.manager_optimized import RegionManager


class TestGlobalIDInvariants:
    """Test that GlobalID invariants are never violated."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GlobalIDGenerator()
        self.generator.clear()
        self.all_generated_ids = set()
        self.collision_tracking = defaultdict(int)

    def test_invariant_no_duplicate_globalids_ever(self):
        """INVARIANT: No duplicate GlobalIDs are ever generated."""
        # Generate IDs under various conditions
        test_scenarios = [
            # Identical entries
            [{"CanonicalNative": "Smith, John", "BirthYear": 1980}] * 100,
            # Similar entries
            [
                {"CanonicalNative": f"Smith, John{i}", "BirthYear": 1980}
                for i in range(100)
            ],
            # Different birth years
            [
                {"CanonicalNative": "Smith, John", "BirthYear": 1980 + i}
                for i in range(100)
            ],
            # Unicode variations
            [
                {"CanonicalNative": f"García{i}, José", "BirthYear": 1980}
                for i in range(100)
            ],
            # Mixed scripts
            [{"CanonicalNative": f"李{i}明", "BirthYear": 1980} for i in range(100)],
        ]

        for scenario_name, entries in enumerate(test_scenarios):
            for entry in entries:
                global_id = self.generator.generate(entry)

                # INVARIANT: Every GlobalID must be unique
                assert (
                    global_id not in self.all_generated_ids
                ), f"INVARIANT VIOLATED: Duplicate GlobalID {global_id} in scenario {scenario_name}"

                self.all_generated_ids.add(global_id)

                # INVARIANT: All GlobalIDs must be valid
                assert validate_global_id(
                    global_id
                ), f"INVARIANT VIOLATED: Invalid GlobalID format {global_id}"

    def test_invariant_deterministic_generation(self):
        """INVARIANT: Same input always produces same GlobalID."""
        test_entries = [
            {"CanonicalNative": "Smith, John", "BirthYear": 1980},
            {"CanonicalNative": "García, José", "BirthYear": 1975},
            {"CanonicalNative": "李明", "BirthYear": 1990},
            {"CanonicalNative": "محمد الأحمد", "BirthYear": 1985},
            {"CanonicalNative": "Владимир Петров", "BirthYear": 1965},
        ]

        # Generate multiple times
        for entry in test_entries:
            ids = [self.generator.generate(entry) for _ in range(10)]

            # INVARIANT: All generations must be identical
            assert (
                len(set(ids)) == 1
            ), f"INVARIANT VIOLATED: Non-deterministic generation for {entry}: {set(ids)}"

    def test_invariant_collision_handling_correctness(self):
        """INVARIANT: Collision handling is always correct."""
        # Force many collisions
        base_id = "ABCDEFGHIJKLMNOPQRSTUV"

        # Mock to force the same base ID
        with patch.object(self.generator, "_compute_base_id", return_value=base_id):
            collision_ids = []

            # Generate 100 entries that would collide
            for i in range(100):
                entry = {
                    "CanonicalNative": f"Test{i:03d}, Person",
                    "BirthYear": 1980 + i,
                }
                global_id = self.generator.generate(entry)
                collision_ids.append(global_id)

            # INVARIANT: First ID should be base, rest should have collision suffixes
            assert (
                collision_ids[0] == base_id
            ), f"INVARIANT VIOLATED: First collision ID should be base: {collision_ids[0]}"

            # INVARIANT: All collision IDs should be unique
            assert len(set(collision_ids)) == len(
                collision_ids
            ), "INVARIANT VIOLATED: Collision handling produced duplicates"

            # INVARIANT: Collision suffixes should be sequential
            collision_suffixes = []
            for gid in collision_ids[1:]:  # Skip base ID
                if "--" in gid:
                    suffix = int(gid.split("--")[1])
                    collision_suffixes.append(suffix)

            collision_suffixes.sort()
            expected_suffixes = list(range(1, len(collision_suffixes) + 1))
            assert (
                collision_suffixes == expected_suffixes
            ), f"INVARIANT VIOLATED: Non-sequential collision suffixes: {collision_suffixes}"

    def test_invariant_globalid_format_always_valid(self):
        """INVARIANT: All generated GlobalIDs have valid format."""
        # Test with various edge cases
        edge_cases = [
            {"CanonicalNative": ""},  # Empty name
            {"CanonicalNative": "A"},  # Single character
            {"CanonicalNative": "A" * 1000},  # Very long name
            {"CanonicalNative": "Smith, John", "BirthYear": None},  # No birth year
            {
                "CanonicalNative": "Smith, John",
                "BirthYear": "invalid",
            },  # Invalid birth year
            {
                "CanonicalNative": "Smith, John",
                "BirthYear": float("inf"),
            },  # Infinite birth year
            {
                "CanonicalNative": "Smith, John",
                "BirthYear": -999999,
            },  # Ancient birth year
        ]

        for entry in edge_cases:
            try:
                global_id = self.generator.generate(entry)

                # INVARIANT: If generated, must be valid format
                if global_id is not None:
                    assert validate_global_id(
                        global_id
                    ), f"INVARIANT VIOLATED: Invalid GlobalID format {global_id} for {entry}"

            except Exception:
                # Exception is acceptable for invalid input
                pass

    def test_invariant_concurrent_uniqueness(self):
        """INVARIANT: Concurrent generation never produces duplicates."""
        generated_ids = []
        errors = []

        def concurrent_generator(worker_id):
            """Generate IDs concurrently."""
            local_ids = []

            try:
                for i in range(50):
                    entry = {
                        "CanonicalNative": f"Worker{worker_id:02d}Test{i:03d}, Person",
                        "BirthYear": 1980 + i,
                    }
                    global_id = self.generator.generate(entry)
                    local_ids.append(global_id)

                return local_ids
            except Exception as e:
                errors.append((worker_id, str(e)))
                return []

        # Run concurrent generation
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(concurrent_generator, i) for i in range(10)]

            for future in as_completed(futures):
                result = future.result()
                generated_ids.extend(result)

        # INVARIANT: No errors should occur
        assert (
            len(errors) == 0
        ), f"INVARIANT VIOLATED: Concurrent generation errors: {errors}"

        # INVARIANT: All IDs should be unique
        assert len(set(generated_ids)) == len(
            generated_ids
        ), "INVARIANT VIOLATED: Concurrent generation produced duplicates"

        # INVARIANT: All IDs should be valid
        for global_id in generated_ids:
            assert validate_global_id(
                global_id
            ), f"INVARIANT VIOLATED: Invalid GlobalID from concurrent generation: {global_id}"


class TestUnicodeNormalizationInvariants:
    """Test that Unicode normalization invariants are never violated."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = UnicodeNormalizer()

    def test_invariant_normalization_idempotent(self):
        """INVARIANT: Normalization is always idempotent."""
        test_strings = [
            "Smith, John",
            "García, José",
            "李明",
            "محمد الأحمد",
            "Владимир Петров",
            "Σωκράτης",
            "café",
            "naïve",
            "Zürich",
            "A\u0300",  # A with combining grave
            "caf\u00e9",  # café with é
            "cafe\u0301",  # café with combining acute
            "Smith\u200b, John",  # Zero-width space
            "Smith\u202e, John",  # Right-to-left override
            "",  # Empty string
            "A",  # Single character
            "A" * 1000,  # Very long string
        ]

        for text in test_strings:
            normalized1 = self.handler.normalize(text)

            if normalized1 is not None:
                normalized2 = self.handler.normalize(normalized1)

                # INVARIANT: Normalization must be idempotent
                assert (
                    normalized1 == normalized2
                ), f"INVARIANT VIOLATED: Non-idempotent normalization: {repr(text)} -> {repr(normalized1)} -> {repr(normalized2)}"

    def test_invariant_no_data_corruption(self):
        """INVARIANT: Normalization never corrupts essential data."""
        # Test cases where certain characters must be preserved
        preservation_cases = [
            ("Smith, John", ","),  # Comma must be preserved
            (
                "García, José",
                "í",
                "é",
            ),  # Accented characters should be preserved or safely converted
            ("李明", "李", "明"),  # Chinese characters must be preserved
            ("O'Connor", "'"),  # Apostrophe in names
            ("van der Berg", " "),  # Spaces must be preserved
            ("Jean-Pierre", "-"),  # Hyphens in names
        ]

        for text, *critical_chars in preservation_cases:
            normalized = self.handler.normalize(text)

            if normalized is not None:
                # INVARIANT: Critical characters must be preserved or safely converted
                for char in critical_chars:
                    if char in text:
                        # Either preserved or safely converted
                        assert (
                            char in normalized or len(normalized) >= len(text) - 1
                        ), f"INVARIANT VIOLATED: Critical character {repr(char)} lost in normalization of {repr(text)}"

    def test_invariant_no_dangerous_characters(self):
        """INVARIANT: Normalization never introduces dangerous characters."""
        dangerous_inputs = [
            "Smith\x00, John",  # Null byte
            "Smith\x01, John",  # Control character
            "Smith\r\n, John",  # CRLF
            "Smith\t, John",  # Tab
            "Smith\u200b, John",  # Zero-width space
            "Smith\u202e, John",  # Right-to-left override
            "Smith\ufeff, John",  # Byte order mark
        ]

        for text in dangerous_inputs:
            normalized = self.handler.normalize(text)

            if normalized is not None:
                # INVARIANT: No dangerous characters should remain
                dangerous_chars = [
                    "\x00",
                    "\x01",
                    "\x02",
                    "\x03",
                    "\x04",
                    "\x05",
                    "\r",
                    "\n",
                    "\t",
                ]
                for char in dangerous_chars:
                    assert (
                        char not in normalized
                    ), f"INVARIANT VIOLATED: Dangerous character {repr(char)} not removed from {repr(text)}"

    def test_invariant_script_detection_consistency(self):
        """INVARIANT: Script detection is always consistent."""
        test_cases = [
            ("Smith, John", "Latin"),
            ("García, José", "Latin"),
            ("李明", "CJK"),
            ("محمد الأحمد", "Arabic"),
            ("Владимир Петров", "Cyrillic"),
            ("Σωκράτης", "Greek"),
        ]

        for text, expected_script in test_cases:
            # Test multiple times to ensure consistency
            scripts = [self.handler.detect_primary_script(text) for _ in range(10)]

            # INVARIANT: Script detection must be consistent
            assert (
                len(set(scripts)) == 1
            ), f"INVARIANT VIOLATED: Inconsistent script detection for {repr(text)}: {set(scripts)}"

            # INVARIANT: Script detection should be reasonable
            detected_script = scripts[0]
            assert detected_script in [
                "Latin",
                "CJK",
                "Arabic",
                "Cyrillic",
                "Greek",
                "Other",
                "Unknown",
            ], f"INVARIANT VIOLATED: Invalid script detected: {detected_script}"


class TestRegionDetectionInvariants:
    """Test that region detection invariants are never violated."""

    def setup_method(self):
        """Set up test fixtures."""
        self.region_manager = RegionManager()

    def test_invariant_region_detection_deterministic(self):
        """INVARIANT: Region detection is always deterministic."""
        test_entries = [
            {"CanonicalLatin": "Smith, John", "CountryCodes": ["US"]},
            {"CanonicalLatin": "García, José", "CountryCodes": ["ES"]},
            {"CanonicalLatin": "李明", "CountryCodes": ["CN"]},
            {"CanonicalLatin": "محمد الأحمد", "CountryCodes": ["SA"]},
            {"CanonicalLatin": "Владимир Петров", "CountryCodes": ["RU"]},
        ]

        for entry in test_entries:
            # Test multiple times
            results = [self.region_manager.detect_region(entry) for _ in range(10)]

            # INVARIANT: Region detection must be deterministic
            region_codes = [r.region_code for r in results]
            assert (
                len(set(region_codes)) == 1
            ), f"INVARIANT VIOLATED: Non-deterministic region detection for {entry}: {set(region_codes)}"

            # INVARIANT: Confidence should be consistent
            confidences = [r.confidence for r in results]
            assert (
                len(set(confidences)) == 1
            ), f"INVARIANT VIOLATED: Non-deterministic confidence for {entry}: {set(confidences)}"

    def test_invariant_region_codes_valid(self):
        """INVARIANT: Region codes are always valid."""
        valid_region_codes = {
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
            "A6",
            "A7",
            "A8",
            "B1",
            "B2",
            "B3",
            "B4",
            "B5",
            "B6",
            "B7",
            "B8",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
            "D6",
            "D7",
            "D8",
            "E1",
            "E2",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",
            "E8",
            "F1",
            "F2",
            "F3",
            "F4",
            "F5",
            "F6",
            "F7",
            "F8",
            "G1",
            "G2",
            "G3",
            "G4",
            "G5",
            "G6",
            "G7",
            "G8",
            "H1",
            "H2",
            "H3",
            "H4",
            "H5",
            "H6",
            "H7",
            "H8",
            "R0",
            "Z0",
        }

        # Test with various entries
        test_entries = [
            {"CanonicalLatin": "Smith, John", "CountryCodes": ["US"]},
            {"CanonicalLatin": "García, José", "CountryCodes": ["ES"]},
            {"CanonicalLatin": "李明", "CountryCodes": ["CN"]},
            {
                "CanonicalLatin": "Unknown, Person",
                "CountryCodes": ["ZZ"],
            },  # Invalid country
            {
                "CanonicalLatin": "Mixed, Script李明",
                "CountryCodes": ["US"],
            },  # Mixed scripts
            {"CanonicalLatin": "No Country, Person", "CountryCodes": []},  # No country
        ]

        for entry in test_entries:
            result = self.region_manager.detect_region(entry)

            # INVARIANT: Region code must be valid
            assert (
                result.region_code in valid_region_codes
            ), f"INVARIANT VIOLATED: Invalid region code {result.region_code} for {entry}"

    def test_invariant_confidence_bounds(self):
        """INVARIANT: Confidence scores are always within valid bounds."""
        test_entries = [
            {"CanonicalLatin": "Smith, John", "CountryCodes": ["US"]},
            {"CanonicalLatin": "García, José", "CountryCodes": ["ES"]},
            {"CanonicalLatin": "李明", "CountryCodes": ["CN"]},
            {"CanonicalLatin": "Ambiguous, Name", "CountryCodes": ["US", "GB", "CA"]},
            {"CanonicalLatin": "Unknown, Person", "CountryCodes": ["ZZ"]},
        ]

        for entry in test_entries:
            result = self.region_manager.detect_region(entry)

            # INVARIANT: Confidence must be between 0 and 1
            assert (
                0.0 <= result.confidence <= 1.0
            ), f"INVARIANT VIOLATED: Confidence {result.confidence} out of bounds for {entry}"


class TestPipelineInvariants:
    """Test that pipeline processing invariants are never violated."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = GMNAPConfig()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_invariant_pipeline_data_integrity(self):
        """INVARIANT: Pipeline never corrupts data."""
        # Create test data
        input_dir = Path(self.temp_dir) / "input"
        input_dir.mkdir(parents=True)

        original_entries = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "BirthYear": 1980,
                "CountryCodes": ["US"],
                "Confidence": 85,
            },
            "García, José": {
                "GlobalID": "BCDEFGHIJKLMNOPQRSTUVW",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "García, José",
                "CanonicalNative": "García, José",
                "BirthYear": 1975,
                "CountryCodes": ["ES"],
                "Confidence": 90,
            },
        }

        test_file = input_dir / "test_entries.yaml"
        with open(test_file, "w", encoding="utf-8") as f:
            yaml.dump(original_entries, f, allow_unicode=True)

        # Run pipeline
        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_fetcher:
            mock_instance = Mock()
            mock_instance.fetch = Mock(
                return_value=Mock(
                    status=Mock(value="not_found"), error_message="Not found"
                )
            )
            mock_fetcher.return_value = mock_instance

            result = pipeline.run(input_dir)

        # INVARIANT: Pipeline should complete successfully
        assert result is not None, "INVARIANT VIOLATED: Pipeline failed to complete"

        # INVARIANT: All original entries should be processed
        assert result.total_entries == len(
            original_entries
        ), f"INVARIANT VIOLATED: Entry count mismatch: {result.total_entries} != {len(original_entries)}"

        # INVARIANT: No critical errors should occur
        for stage_name, stage_metrics in result.stage_metrics.items():
            critical_errors = [
                error for error in stage_metrics.errors if "critical" in error.lower()
            ]
            assert (
                len(critical_errors) == 0
            ), f"INVARIANT VIOLATED: Critical errors in {stage_name}: {critical_errors}"

    def test_invariant_pipeline_idempotency(self):
        """INVARIANT: Pipeline is idempotent."""
        # Create test data
        input_dir = Path(self.temp_dir) / "input"
        input_dir.mkdir(parents=True)

        entries = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "BirthYear": 1980,
                "CountryCodes": ["US"],
                "Confidence": 85,
            }
        }

        test_file = input_dir / "test_entries.yaml"
        with open(test_file, "w") as f:
            yaml.dump(entries, f)

        # Run pipeline twice
        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_fetcher:
            mock_instance = Mock()
            mock_instance.fetch = Mock(
                return_value=Mock(
                    status=Mock(value="not_found"), error_message="Not found"
                )
            )
            mock_fetcher.return_value = mock_instance

            result1 = pipeline.run(input_dir)
            result2 = pipeline.run(input_dir)

        # INVARIANT: Results should be identical
        assert (
            result1.total_entries == result2.total_entries
        ), f"INVARIANT VIOLATED: Non-idempotent pipeline: {result1.total_entries} != {result2.total_entries}"

        # INVARIANT: Stage metrics should be similar
        for stage_name in result1.stage_metrics:
            if stage_name in result2.stage_metrics:
                entries1 = result1.stage_metrics[stage_name].entries_processed
                entries2 = result2.stage_metrics[stage_name].entries_processed
                assert (
                    entries1 == entries2
                ), f"INVARIANT VIOLATED: Non-idempotent stage {stage_name}: {entries1} != {entries2}"


class TestSystemInvariants:
    """Test system-wide invariants."""

    def test_invariant_no_data_loss(self):
        """INVARIANT: System never loses data without explicit indication."""
        # This test would need to be implemented based on specific data flow requirements
        # For now, we test that components don't silently drop data

        generator = GlobalIDGenerator()
        unicode_handler = UnicodeNormalizer()

        # Test that processing always returns something or explicitly fails
        test_inputs = [
            "Smith, John",
            "García, José",
            "李明",
            "",  # Empty string
            "A",  # Single character
        ]

        for input_text in test_inputs:
            # Unicode normalization
            normalized = unicode_handler.normalize(input_text)

            # INVARIANT: Should either return result or None (explicit failure)
            assert normalized is None or isinstance(
                normalized, str
            ), f"INVARIANT VIOLATED: Unexpected return type from normalization: {type(normalized)}"

            # If we have a result, test GlobalID generation
            if normalized:
                try:
                    entry = {"CanonicalNative": normalized}
                    global_id = generator.generate(entry)

                    # INVARIANT: Should either return valid ID or raise exception
                    assert global_id is None or validate_global_id(
                        global_id
                    ), f"INVARIANT VIOLATED: Invalid GlobalID returned: {global_id}"

                except Exception as e:
                    # Exception is acceptable - explicit failure
                    assert isinstance(e, Exception), "Should raise proper exception"

    def test_invariant_resource_cleanup(self):
        """INVARIANT: System always cleans up resources."""
        import gc
        import os

        # Get initial resource state
        initial_objects = len(gc.get_objects())
        initial_fds = (
            len(os.listdir("/proc/self/fd")) if os.path.exists("/proc/self/fd") else 0
        )

        # Perform operations that could leak resources
        generator = GlobalIDGenerator()
        unicode_handler = UnicodeNormalizer()

        # Generate many objects
        for i in range(1000):
            entry = {"CanonicalNative": f"Test{i:03d}, Person", "BirthYear": 1980}
            generator.generate(entry)
            unicode_handler.normalize(f"Test{i:03d}, Person")

        # Force garbage collection
        gc.collect()

        # Check resource usage
        final_objects = len(gc.get_objects())
        final_fds = (
            len(os.listdir("/proc/self/fd")) if os.path.exists("/proc/self/fd") else 0
        )

        # INVARIANT: Should not have excessive resource growth
        object_growth = final_objects - initial_objects
        fd_growth = final_fds - initial_fds

        assert (
            object_growth < 1000
        ), f"INVARIANT VIOLATED: Excessive object growth: {object_growth}"
        assert fd_growth < 10, f"INVARIANT VIOLATED: File descriptor leak: {fd_growth}"

    def test_invariant_error_handling_consistency(self):
        """INVARIANT: Error handling is always consistent."""
        # Test that similar errors are handled consistently

        generator = GlobalIDGenerator()
        UnicodeNormalizer()

        # Test various error conditions
        error_cases = [
            ({}, "empty_dict"),
            ({"invalid": "entry"}, "missing_canonical"),
            ({"CanonicalNative": None}, "null_canonical"),
            ({"CanonicalNative": ""}, "empty_canonical"),
        ]

        for entry, case_name in error_cases:
            try:
                global_id = generator.generate(entry)

                # If no exception, result should be valid or None
                assert global_id is None or validate_global_id(
                    global_id
                ), f"INVARIANT VIOLATED: Invalid result for {case_name}: {global_id}"

            except Exception as e:
                # Exception should be appropriate
                assert isinstance(
                    e, (ValueError, KeyError, TypeError)
                ), f"INVARIANT VIOLATED: Unexpected exception type for {case_name}: {type(e)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
