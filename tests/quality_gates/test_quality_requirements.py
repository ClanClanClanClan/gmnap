"""
Quality gate tests for GMNAP system requirements.

Tests critical system requirements, performance targets, and quality thresholds.
"""

import tempfile
import time
from pathlib import Path

import psutil
import pytest
import yaml

from src.core.config import GMNAPConfig
from src.core.globalid import GlobalIDGenerator, validate_global_id
from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
from src.regions.manager import RegionManager
from src.validation.schema import SchemaValidator


class TestGlobalIDQualityGates:
    """Test GlobalID quality requirements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GlobalIDGenerator()
        self.generator.clear()

    def test_no_duplicate_globalids(self):
        """Test that no duplicate GlobalIDs are generated."""
        # Generate many IDs from different inputs
        entries = [
            {"CanonicalNative": f"Test{i:06d}, Person{i:03d}", "BirthYear": 1950 + i}
            for i in range(1000)
        ]

        generated_ids = set()
        duplicates = []

        for entry in entries:
            global_id = self.generator.generate(entry)

            if global_id in generated_ids:
                duplicates.append(global_id)
            else:
                generated_ids.add(global_id)

        # Quality gate: 0 duplicates allowed
        assert (
            len(duplicates) == 0
        ), f"Found {len(duplicates)} duplicate GlobalIDs: {duplicates[:5]}"

    def test_globalid_format_compliance(self):
        """Test that all GlobalIDs comply with format requirements."""
        test_cases = [
            {"CanonicalNative": "Smith, John", "BirthYear": 1980},
            {"CanonicalNative": "García, José", "BirthYear": 1975},
            {"CanonicalNative": "李明", "BirthYear": 1990},
            {"CanonicalNative": "Владимир Петров", "BirthYear": 1965},
            {"CanonicalNative": "محمد الأحمد", "BirthYear": 1985},
            {"CanonicalNative": "Σωκράτης", "BirthYear": -470},
            {"CanonicalNative": "von Neumann, John", "BirthYear": 1903},
            {"CanonicalNative": "Test, Person", "BirthYear": "1970s"},
            {"CanonicalNative": "Ancient, Mathematician", "BirthYear": "c1150"},
        ]

        invalid_formats = []

        for entry in test_cases:
            global_id = self.generator.generate(entry)

            if not validate_global_id(global_id):
                invalid_formats.append((entry, global_id))

        # Quality gate: All GlobalIDs must be valid format
        assert len(invalid_formats) == 0, f"Invalid GlobalID formats: {invalid_formats}"

    def test_globalid_collision_handling(self):
        """Test GlobalID collision handling works correctly."""
        # Force collisions by using same base ID
        base_id = "ABCDEFGHIJKLMNOPQRSTUV"

        # Pre-populate with existing IDs
        existing_ids = {base_id, f"{base_id}--1", f"{base_id}--2"}
        self.generator.load_existing_ids(existing_ids)

        # Generate new ID that would collide
        with pytest.mock.patch.object(
            self.generator, "_compute_base_id", return_value=base_id
        ):
            new_id = self.generator.generate({"CanonicalNative": "Test, Person"})

        # Should get next available collision number
        assert new_id == f"{base_id}--3"

        # Quality gate: Collision handling must work correctly
        assert validate_global_id(new_id)

    def test_globalid_deterministic_generation(self):
        """Test that GlobalID generation is deterministic."""
        test_entry = {"CanonicalNative": "Test, Person", "BirthYear": 1980}

        # Generate multiple times
        ids = [self.generator.generate(test_entry) for _ in range(10)]

        # All should be identical
        unique_ids = set(ids)

        # Quality gate: Deterministic generation
        assert len(unique_ids) == 1, f"Non-deterministic generation: {unique_ids}"


class TestUnicodeQualityGates:
    """Test Unicode handling quality requirements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = UnicodeHandler()

    def test_unicode_normalization_idempotency(self):
        """Test Unicode normalization idempotency."""
        test_cases = [
            "García, José",
            "李明",
            "Владимир Петров",
            "محمد الأحمد",
            "Σωκράτης",
            "Müller, Hans",
            "José María García-López",
            "Παπαδόπουλος, Γιάννης",
            "الخوارزمي, محمد بن موسى",
        ]

        non_idempotent = []

        for text in test_cases:
            normalized1 = self.handler.normalize(text)
            normalized2 = self.handler.normalize(normalized1)

            if normalized1 != normalized2:
                non_idempotent.append((text, normalized1, normalized2))

        # Quality gate: Normalization must be idempotent
        assert (
            len(non_idempotent) == 0
        ), f"Non-idempotent normalizations: {non_idempotent}"

    def test_unicode_script_detection_accuracy(self):
        """Test Unicode script detection accuracy."""
        test_cases = [
            ("Smith, John", "Latin"),
            ("García, José", "Latin"),
            ("李明", "CJK"),
            ("Владимир Петров", "Cyrillic"),
            ("محمد الأحمد", "Arabic"),
            ("Σωκράτης", "Greek"),
            ("རམ་པ", "Tibetan"),
            ("การันต์", "Thai"),
            ("អនុក្រឹត្យ", "Khmer"),
        ]

        incorrect_detections = []

        for text, expected_script in test_cases:
            detected_script = self.handler.detect_primary_script(text)

            if detected_script != expected_script:
                incorrect_detections.append((text, expected_script, detected_script))

        # Quality gate: ≥95% script detection accuracy
        accuracy = (len(test_cases) - len(incorrect_detections)) / len(test_cases)
        assert accuracy >= 0.95, f"Script detection accuracy {accuracy:.2%} < 95%"

    def test_unicode_roundtrip_preservation(self):
        """Test Unicode roundtrip preservation."""
        # Test important Unicode categories
        test_cases = [
            "Café",  # Latin with diacritics
            "naïve",  # Diaeresis
            "résumé",  # Acute accents
            "Zürich",  # Umlaut
            "Москва",  # Cyrillic
            "北京",  # CJK
            "한국어",  # Hangul
            "العربية",  # Arabic
            "ελληνικά",  # Greek
            "हिन्दी",  # Devanagari
        ]

        roundtrip_failures = []

        for text in test_cases:
            normalized = self.handler.normalize(text)
            # Check if essential characters are preserved
            original_alphanumeric = set(c for c in text if c.isalnum())
            normalized_alphanumeric = set(c for c in normalized if c.isalnum())

            if not original_alphanumeric.issubset(normalized_alphanumeric):
                roundtrip_failures.append((text, normalized))

        # Quality gate: ≥97% roundtrip preservation
        accuracy = (len(test_cases) - len(roundtrip_failures)) / len(test_cases)
        assert accuracy >= 0.97, f"Roundtrip preservation {accuracy:.2%} < 97%"


class TestRegionQualityGates:
    """Test region detection and processing quality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.region_manager = RegionManager()

    def test_region_detection_coverage(self):
        """Test region detection coverage."""
        test_cases = [
            ("Smith, John", ["US"], "A1"),
            ("García, José", ["ES"], "A2"),
            ("李明", ["CN"], "E1"),
            ("Владимир Петров", ["RU"], "D1"),
            ("محمد الأحمد", ["SA"], "C1"),
            ("Tanaka, Hiroshi", ["JP"], "E2"),
            ("Kim, Min-jun", ["KR"], "E3"),
            ("Singh, Raj", ["IN"], "B1"),
            ("Müller, Hans", ["DE"], "A3"),
            ("Andersson, Lars", ["SE"], "A4"),
        ]

        undetected_regions = []

        for name, countries, expected_region in test_cases:
            entry = {"CanonicalLatin": name, "CountryCodes": countries}

            result = self.region_manager.detect_region(entry)

            if result.region_code != expected_region:
                undetected_regions.append((name, expected_region, result.region_code))

        # Quality gate: ≥90% region detection accuracy
        accuracy = (len(test_cases) - len(undetected_regions)) / len(test_cases)
        assert accuracy >= 0.90, f"Region detection accuracy {accuracy:.2%} < 90%"

    def test_region_fallback_handling(self):
        """Test region fallback handling."""
        # Test entries that should fall back to R0 or Z0
        fallback_cases = [
            {
                "CanonicalLatin": "Unknown, Person",
                "CountryCodes": ["ZZ"],
            },  # Invalid country
            {
                "CanonicalLatin": "Mixed, Script 李明",
                "CountryCodes": ["US"],
            },  # Mixed scripts
            {"CanonicalLatin": "Ambiguous, Name", "CountryCodes": []},  # No country
        ]

        for entry in fallback_cases:
            result = self.region_manager.detect_region(entry)

            # Should fallback to R0 or Z0
            assert result.region_code in [
                "R0",
                "Z0",
            ], f"Entry {entry} should fallback to R0/Z0, got {result.region_code}"

    def test_order_key_consistency(self):
        """Test order key consistency across regions."""
        test_entries = [
            {"CanonicalLatin": "Smith, John", "CountryCodes": ["US"]},
            {"CanonicalLatin": "García, José", "CountryCodes": ["ES"]},
            {"CanonicalLatin": "李明", "CountryCodes": ["CN"]},
            {"CanonicalLatin": "Владимир Петров", "CountryCodes": ["RU"]},
        ]

        order_keys = []

        for entry in test_entries:
            result = self.region_manager.detect_region(entry)
            region_spec = self.region_manager.get_region_spec(result.region_code)

            if region_spec:
                order_key = region_spec.order_key(entry)
                order_keys.append((entry["CanonicalLatin"], order_key))

        # Quality gate: All entries should have order keys
        assert len(order_keys) == len(test_entries), "Some entries missing order keys"

        # Order keys should be deterministic
        for name, order_key in order_keys:
            assert isinstance(
                order_key, str
            ), f"Order key for {name} is not string: {order_key}"
            assert len(order_key) > 0, f"Empty order key for {name}"


class TestPerformanceQualityGates:
    """Test performance requirements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = GMNAPConfig()
        self.process = psutil.Process()

    def test_memory_usage_limits(self):
        """Test memory usage limits."""
        # Create test dataset
        temp_dir = tempfile.mkdtemp()
        input_dir = Path(temp_dir) / "input"
        input_dir.mkdir(parents=True)

        # Create 10k entries
        entries = {}
        for i in range(10000):
            canonical = f"Test{i:06d}, Person{i:03d}"
            entries[canonical] = {
                "GlobalID": f"ABCDEFGHIJKLMNOPQR{i:05d}",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": canonical,
                "CanonicalNative": canonical,
                "BirthYear": 1950 + (i % 50),
                "CountryCodes": ["US"],
                "Confidence": 80 + (i % 20),
            }

        test_file = input_dir / "test_entries.yaml"
        with open(test_file, "w") as f:
            yaml.dump(entries, f)

        # Monitor memory usage
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        # Process with pipeline
        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        # Mock external dependencies
        with pytest.mock.patch("src.authorities.tier0.openalex.OpenAlexFetcher"):
            pipeline._stage_0_config()
            pipeline._stage_1_ingest(input_dir)
            pipeline._stage_2_detect_region()
            pipeline._stage_3_region_hooks()

        peak_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # Quality gate: Memory usage ≤ 2GB for processing
        assert (
            memory_increase <= 2048
        ), f"Memory usage {memory_increase:.1f}MB exceeds 2GB limit"

        # Clean up
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_processing_speed_targets(self):
        """Test processing speed targets."""
        # Test GlobalID generation speed
        generator = GlobalIDGenerator()
        entries = [
            {"CanonicalNative": f"Test{i:06d}, Person", "BirthYear": 1950 + i}
            for i in range(1000)
        ]

        start_time = time.time()
        for entry in entries:
            generator.generate(entry)
        end_time = time.time()

        total_time = end_time - start_time
        time_per_entry = total_time / len(entries)

        # Quality gate: GlobalID generation ≤ 0.1ms per entry
        assert (
            time_per_entry <= 0.0001
        ), f"GlobalID generation {time_per_entry:.6f}s > 0.1ms per entry"

        # Test Unicode normalization speed
        handler = UnicodeHandler()
        test_names = [
            "García, José María",
            "李明",
            "Владимир Петров",
            "محمد الأحمد",
            "Σωκράτης",
        ] * 200  # 1000 total

        start_time = time.time()
        for name in test_names:
            handler.normalize(name)
        end_time = time.time()

        total_time = end_time - start_time
        time_per_entry = total_time / len(test_names)

        # Quality gate: Unicode normalization ≤ 1ms per entry
        assert (
            time_per_entry <= 0.001
        ), f"Unicode normalization {time_per_entry:.6f}s > 1ms per entry"

    def test_concurrent_processing_performance(self):
        """Test concurrent processing performance."""
        import concurrent.futures

        # Test concurrent GlobalID generation
        generator = GlobalIDGenerator()

        def generate_batch(batch_id):
            entries = [
                {
                    "CanonicalNative": f"Batch{batch_id:03d}Test{i:03d}, Person",
                    "BirthYear": 1950 + i,
                }
                for i in range(100)
            ]
            return [generator.generate(entry) for entry in entries]

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(generate_batch, i) for i in range(10)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        end_time = time.time()
        total_time = end_time - start_time

        # Quality gate: Concurrent processing should be faster than sequential
        # (This is more of a performance regression test)
        assert total_time < 5.0, f"Concurrent processing took {total_time:.2f}s > 5s"

        # Verify all results are valid
        all_ids = [global_id for batch in results for global_id in batch]
        assert len(all_ids) == 1000
        assert all(validate_global_id(global_id) for global_id in all_ids)


class TestValidationQualityGates:
    """Test validation quality requirements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SchemaValidator()

    def test_schema_validation_coverage(self):
        """Test schema validation coverage."""
        # Test valid entries
        valid_entries = [
            {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
            },
            {
                "GlobalID": "BCDEFGHIJKLMNOPQRSTUVW",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "García, José",
                "CanonicalNative": "García, José",
                "BirthYear": 1980,
                "CountryCodes": ["ES"],
                "Confidence": 85,
            },
        ]

        for entry in valid_entries:
            is_valid = self.validator.validate_entry(entry)
            assert is_valid, f"Valid entry failed validation: {entry}"

        # Test invalid entries
        invalid_entries = [
            {},  # Empty entry
            {"GlobalID": "INVALID"},  # Invalid GlobalID
            {"GlobalID": "ABCDEFGHIJKLMNOPQRSTUV"},  # Missing required fields
            {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "BirthYear": 1980,
                "DeathYear": 1970,  # Death before birth
            },
        ]

        for entry in invalid_entries:
            is_valid = self.validator.validate_entry(entry)
            assert not is_valid, f"Invalid entry passed validation: {entry}"

    def test_external_id_validation(self):
        """Test external ID validation."""
        # Test ORCID validation
        orcid_test_cases = [
            ("0000-0003-1234-5678", True),
            ("0000-0003-1234-567X", True),
            ("invalid-orcid", False),
            ("0000-0003-1234-5678X", False),
        ]

        for orcid, should_be_valid in orcid_test_cases:
            entry = {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "AuthorityIDs": {"ORCID": orcid},
            }

            is_valid = self.validator.validate_entry(entry)
            if should_be_valid:
                assert is_valid, f"Valid ORCID {orcid} failed validation"
            else:
                assert not is_valid, f"Invalid ORCID {orcid} passed validation"

    def test_consistency_validation(self):
        """Test consistency validation across fields."""
        # Test birth/death year consistency
        inconsistent_entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "BirthYear": 1980,
            "DeathYear": 1970,  # Death before birth
        }

        is_valid = self.validator.validate_entry(inconsistent_entry)
        assert not is_valid, "Inconsistent birth/death years should be invalid"

        # Test name consistency

        # Note: This might be valid if native/latin can differ
        # The test would depend on specific validation rules


class TestSystemIntegrationQualityGates:
    """Test system integration quality requirements."""

    def test_end_to_end_pipeline_quality(self):
        """Test end-to-end pipeline quality."""
        # Create test dataset
        temp_dir = tempfile.mkdtemp()
        input_dir = Path(temp_dir) / "input"
        input_dir.mkdir(parents=True)

        # Mixed region entries
        entries = {
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
            "李明": {
                "GlobalID": "CDEFGHIJKLMNOPQRSTUVWX",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Li, Ming",
                "CanonicalNative": "李明",
                "BirthYear": 1985,
                "CountryCodes": ["CN"],
                "Confidence": 80,
            },
        }

        test_file = input_dir / "test_entries.yaml"
        with open(test_file, "w", encoding="utf-8") as f:
            yaml.dump(entries, f, allow_unicode=True)

        # Run pipeline
        config = GMNAPConfig()
        pipeline = GMNAPPipeline(config, PipelineMode.QUICK)

        with pytest.mock.patch("src.authorities.tier0.openalex.OpenAlexFetcher"):
            result = pipeline.run(input_dir)

        # Quality gates
        assert result.total_entries == 3
        assert result.mode == PipelineMode.QUICK
        assert len(result.stage_metrics) > 0

        # No critical errors
        critical_errors = [
            error
            for stage_metrics in result.stage_metrics.values()
            for error in stage_metrics.errors
            if "critical" in error.lower()
        ]
        assert len(critical_errors) == 0, f"Critical errors found: {critical_errors}"

        # Clean up
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_system_reliability_requirements(self):
        """Test system reliability requirements."""
        # Test graceful error handling
        config = GMNAPConfig()
        pipeline = GMNAPPipeline(config, PipelineMode.QUICK)

        # Test with invalid input
        temp_dir = tempfile.mkdtemp()
        input_dir = Path(temp_dir) / "input"
        input_dir.mkdir(parents=True)

        # Create invalid YAML
        invalid_file = input_dir / "invalid.yaml"
        with open(invalid_file, "w") as f:
            f.write("invalid: yaml: content: [")

        # Should handle gracefully
        try:
            result = pipeline.run(input_dir)
            # Should not crash, but might have errors
            assert result is not None
        except Exception as e:
            pytest.fail(f"Pipeline crashed on invalid input: {e}")

        # Clean up
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
