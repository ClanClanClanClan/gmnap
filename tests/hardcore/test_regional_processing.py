"""
Hardcore regional processing system testing for GMNAP.

Tests all 43 regional groups, region detection accuracy, regional rules,
name normalization, and all scenarios that could cause regional processing failures.
"""

import random
import tempfile
import threading
import time
from pathlib import Path
from queue import Empty, Queue

import pytest

from src.core.unicode_handler import UnicodeNormalizer
from src.regions.manager_optimized import RegionManager


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
        """Test region detection based on script analysis."""
        # Test cases with expected regions
        script_test_cases = [
            # Latin script regions
            ("Smith, John", ["A1", "A2", "A3", "A4", "A5", "A6"]),
            ("García, José", ["A2", "D3"]),  # Spanish-speaking
            ("Müller, Hans", ["A3", "D1"]),  # German-speaking
            ("Dubois, Jean", ["A4", "D2"]),  # French-speaking
            ("Silva, João", ["A2", "D4"]),  # Portuguese-speaking
            # Cyrillic script regions
            ("Иванов, Петр", ["B1", "E6"]),  # Russian/Slavic
            ("Петров, Александр", ["B1", "E6"]),
            ("Николаев, Дмитрий", ["B1", "E6"]),
            # Arabic script regions
            ("محمد, أحمد", ["B2", "E1"]),  # Arabic
            ("الخوارزمي, محمد", ["B2", "E1"]),
            ("ابن سينا, أبو علي", ["B2", "E1"]),
            # Greek script regions
            ("Παπαδόπουλος, Γιάννης", ["A6", "E6"]),  # Greek
            ("Αρχιμήδης", ["G1"]),  # Ancient Greek
            # Hebrew script regions
            ("כהן, דוד", ["B2", "E2"]),  # Hebrew
            ("רבין, יצחק", ["B2", "E2"]),
            # CJK script regions
            ("李明", ["C1", "C2", "F1"]),  # Chinese
            ("王伟", ["C1", "C2", "F1"]),
            ("田中太郎", ["C3", "F1"]),  # Japanese
            ("김민수", ["C4", "F1"]),  # Korean
            # Indian script regions
            ("गुप्ता, राम", ["B5", "E5"]),  # Devanagari
            ("শর্মা, অমিত", ["B5", "E5"]),  # Bengali
            ("குமார், ராம்", ["B5", "E5"]),  # Tamil
            # Southeast Asian scripts
            ("สมิท, จอห์น", ["B6", "F2"]),  # Thai
            ("ស្មីត, ចន", ["B6", "F2"]),  # Khmer
            ("မမ, ဂျွန်", ["B6", "F2"]),  # Myanmar
            # Mixed scripts (diaspora/multiregional)
            ("Smith, 李明", ["H1", "H3"]),  # Mixed Latin/Chinese
            ("García, محمد", ["H1", "H3"]),  # Mixed Latin/Arabic
            ("Müller, Александр", ["H1", "H3"]),  # Mixed Latin/Cyrillic
        ]

        for name, expected_regions in script_test_cases:
            # Detect region
            entry = {"canonical_name": name, "CanonicalLatin": name}
            detection = self.region_manager.detect_region(entry)

            # Should detect one of the expected regions
            assert (
                detection.region_code in expected_regions
            ), f"Unexpected region {detection.region_code} for {name}, expected one of {expected_regions}"

            # Should have reasonable confidence
            assert (
                detection.confidence >= 0.1
            ), f"Low confidence {detection.confidence} for {name}"

    def test_region_detection_by_country(self):
        """Test region detection based on country information."""
        country_test_cases = [
            # North America
            ("Smith, John", "US", "A1"),
            ("Smith, John", "CA", "A1"),
            ("García, José", "MX", "A2"),
            # Europe
            ("Müller, Hans", "DE", "A3"),
            ("Dubois, Jean", "FR", "A4"),
            ("Rossi, Marco", "IT", "A6"),
            ("Johnson, Erik", "SE", "A5"),
            ("Kowalski, Jan", "PL", "A7"),
            # Asia
            ("李明", "CN", "C2"),
            ("田中太郎", "JP", "C3"),
            ("김민수", "KR", "C4"),
            ("Gupta, Ram", "IN", "B5"),
            ("Smith, John", "TH", "B6"),
            # Middle East
            ("محمد, أحمد", "SA", "B2"),
            ("כהן, דוד", "IL", "B2"),
            ("احمدی, علی", "IR", "B2"),
            ("Yılmaz, Mehmet", "TR", "B2"),
            # Africa
            ("الطاهر, محمد", "EG", "B3"),
            ("Okafor, Chukwu", "NG", "B4"),
            ("Mandela, Nelson", "ZA", "B4"),
            # Oceania
            ("Smith, John", "AU", "C5"),
            ("Smith, John", "NZ", "C5"),
            ("Tanaka, Kenji", "FJ", "C6"),
        ]

        for name, country, expected_region in country_test_cases:
            # Create entry with country information
            entry = {
                "canonical_name": name,
                "CanonicalLatin": name,
                "countries": [country],
                "affiliations": [{"country": country}],
            }

            detection = self.region_manager.detect_region(entry)

            # Should detect expected region
            assert (
                detection.region_code == expected_region
            ), f"Expected region {expected_region} for {name} in {country}, got {detection.region_code}"

            # Should have high confidence for country-based detection
            assert (
                detection.confidence >= 0.7
            ), f"Low confidence {detection.confidence} for country-based detection"

    def test_region_detection_by_institution(self):
        """Test region detection based on institutional affiliation."""
        institution_test_cases = [
            # US institutions
            ("Smith, John", "Harvard University", "A1"),
            ("Johnson, Mary", "MIT", "A1"),
            ("Brown, David", "Stanford University", "A1"),
            ("Wilson, Sarah", "University of California", "A1"),
            # UK institutions
            ("Smith, John", "University of Oxford", "A1"),
            ("Johnson, Mary", "University of Cambridge", "A1"),
            ("Brown, David", "Imperial College London", "A1"),
            # German institutions
            ("Müller, Hans", "Max Planck Institute", "A3"),
            ("Schmidt, Klaus", "Technical University of Munich", "A3"),
            ("Weber, Anna", "University of Heidelberg", "A3"),
            # French institutions
            ("Dubois, Jean", "Sorbonne University", "A4"),
            ("Martin, Pierre", "École Normale Supérieure", "A4"),
            ("Durand, Marie", "CNRS", "A4"),
            # Chinese institutions
            ("李明", "Tsinghua University", "C2"),
            ("王伟", "Peking University", "C2"),
            ("张三", "Chinese Academy of Sciences", "C2"),
            # Japanese institutions
            ("田中太郎", "University of Tokyo", "C3"),
            ("山田花子", "Kyoto University", "C3"),
            ("佐藤一郎", "RIKEN", "C3"),
            # Mixed/International institutions
            ("Smith, John", "CERN", "H3"),  # International
            ("García, José", "International Mathematical Union", "H3"),
        ]

        for name, institution, expected_region in institution_test_cases:
            # Create entry with institutional affiliation
            entry = {
                "canonical_name": name,
                "CanonicalLatin": name,
                "affiliations": [{"name": institution}],
            }

            detection = self.region_manager.detect_region(entry)

            # Should detect expected region
            assert (
                detection.region_code == expected_region
            ), f"Expected region {expected_region} for {name} at {institution}, got {detection.region_code}"

    def test_region_detection_edge_cases(self):
        """Test region detection edge cases."""
        edge_cases = [
            # Empty/minimal data
            ({}, "Z0"),  # Should quarantine
            ({"canonical_name": ""}, "Z0"),  # Empty name
            ({"canonical_name": "???"}, "Z0"),  # Invalid characters
            # Conflicting signals
            (
                {"canonical_name": "Smith, John", "countries": ["CN"]},
                ["A1", "C2"],
            ),  # English name, Chinese country
            (
                {"canonical_name": "李明", "countries": ["US"]},
                ["C2", "A1"],
            ),  # Chinese name, US country
            # Ancient/Historical names
            (
                {"canonical_name": "Archimedes", "birth_year": -287},
                "G1",
            ),  # Ancient Greek
            (
                {"canonical_name": "Al-Khwarizmi", "birth_year": 780},
                "G2",
            ),  # Medieval Islamic
            (
                {"canonical_name": "Fibonacci", "birth_year": 1170},
                "G3",
            ),  # Medieval European
            # Stateless/Diaspora
            (
                {"canonical_name": "Einstein, Albert", "countries": ["DE", "US", "CH"]},
                ["H1", "H2"],
            ),  # Multiple countries
            (
                {"canonical_name": "Refugee, John", "countries": []},
                ["H2", "Z0"],
            ),  # No country
            # Mixed scripts with high confidence
            (
                {"canonical_name": "García-李, José-Ming"},
                ["H1", "H3"],
            ),  # Mixed Latin-Chinese
            (
                {"canonical_name": "Müller-Иванов, Hans-Петр"},
                ["H1", "H3"],
            ),  # Mixed Latin-Cyrillic
            # Transliteration variants
            (
                {
                    "canonical_name": "Gorbachev, Mikhail",
                    "name_variants": ["Горбачёв, Михаил"],
                },
                ["B1", "E6"],
            ),
            (
                {"canonical_name": "Mao, Zedong", "name_variants": ["毛泽东"]},
                ["C2", "F1"],
            ),
        ]

        for entry, expected in edge_cases:
            detection = self.region_manager.detect_region(entry)

            if isinstance(expected, str):
                assert (
                    detection.region_code == expected
                ), f"Expected region {expected} for {entry}, got {detection.region_code}"
            else:
                assert (
                    detection.region_code in expected
                ), f"Expected region in {expected} for {entry}, got {detection.region_code}"

    def test_region_detection_confidence_scoring(self):
        """Test region detection confidence scoring."""
        confidence_test_cases = [
            # High confidence cases
            (
                {
                    "canonical_name": "Smith, John",
                    "countries": ["US"],
                    "affiliations": [{"name": "Harvard University"}],
                },
                0.9,
            ),
            (
                {
                    "canonical_name": "李明",
                    "countries": ["CN"],
                    "affiliations": [{"name": "Tsinghua University"}],
                },
                0.9,
            ),
            (
                {
                    "canonical_name": "Müller, Hans",
                    "countries": ["DE"],
                    "affiliations": [{"name": "Max Planck Institute"}],
                },
                0.9,
            ),
            # Medium confidence cases
            ({"canonical_name": "Smith, John", "countries": ["US"]}, 0.7),
            ({"canonical_name": "李明", "countries": ["CN"]}, 0.7),
            ({"canonical_name": "García, José"}, 0.5),
            # Low confidence cases
            ({"canonical_name": "Smith, John"}, 0.3),
            ({"canonical_name": "Unknown, Person"}, 0.1),
            ({"canonical_name": "???"}, 0.0),
        ]

        for entry, min_confidence in confidence_test_cases:
            detection = self.region_manager.detect_region(entry)

            assert (
                detection.confidence >= min_confidence
            ), f"Low confidence {detection.confidence} for {entry}, expected >= {min_confidence}"

            assert (
                detection.confidence <= 1.0
            ), f"Confidence {detection.confidence} exceeds 1.0 for {entry}"


class TestRegionalRuleValidation:
    """Test regional rule validation across all regions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.region_manager = RegionManager(Path(self.temp_dir))

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_a1_region_validation(self):
        """Test A1 (Anglo-Sphere) region validation."""
        # Valid A1 entries
        valid_entries = [
            {
                "canonical_name": "Smith, John",
                "CanonicalLatin": "Smith, John",
                "countries": ["US"],
                "name_variants": ["J. Smith", "John Smith"],
                "affiliations": [{"name": "Harvard University", "country": "US"}],
            },
            {
                "canonical_name": "Johnson, Mary Elizabeth",
                "CanonicalLatin": "Johnson, Mary Elizabeth",
                "countries": ["UK"],
                "name_variants": ["M. E. Johnson", "Mary Johnson"],
                "affiliations": [{"name": "University of Cambridge", "country": "UK"}],
            },
            {
                "canonical_name": "Brown, David Jr.",
                "CanonicalLatin": "Brown, David Jr.",
                "countries": ["CA"],
                "name_variants": ["D. Brown Jr.", "David Brown"],
                "affiliations": [{"name": "University of Toronto", "country": "CA"}],
            },
        ]

        a1_region = A1Region()

        for entry in valid_entries:
            context = ProcessingContext(
                region=RegionalGroup.ANGLOPHONE,
                source_data=entry,
                metadata=a1_region.metadata,
            )

            # Should validate successfully
            is_valid = a1_region.validate(entry, context)
            assert (
                is_valid
            ), f"Valid A1 entry failed validation: {entry['canonical_name']}"

            # Should have no validation errors
            assert (
                len(context.validation_errors) == 0
            ), f"Validation errors for valid entry: {context.validation_errors}"

    def test_a1_region_invalid_entries(self):
        """Test A1 region with invalid entries."""
        invalid_entries = [
            # Non-Latin script
            {"canonical_name": "李明", "CanonicalLatin": "李明", "countries": ["US"]},
            # Mixed scripts
            {
                "canonical_name": "Smith, 李明",
                "CanonicalLatin": "Smith, 李明",
                "countries": ["US"],
            },
            # Invalid name format
            {
                "canonical_name": "JohnSmith",  # No comma
                "CanonicalLatin": "JohnSmith",
                "countries": ["US"],
            },
            # Missing required fields
            {
                "canonical_name": "Smith, John",
                "CanonicalLatin": "Smith, John",
                # Missing countries
            },
        ]

        a1_region = A1Region()

        for entry in invalid_entries:
            context = ProcessingContext(
                region=RegionalGroup.ANGLOPHONE,
                source_data=entry,
                metadata=a1_region.metadata,
            )

            # Should fail validation
            is_valid = a1_region.validate(entry, context)
            assert (
                not is_valid
            ), f"Invalid A1 entry passed validation: {entry['canonical_name']}"

            # Should have validation errors
            assert (
                len(context.validation_errors) > 0
            ), f"No validation errors for invalid entry: {entry['canonical_name']}"

    def test_regional_name_normalization(self):
        """Test regional name normalization."""
        normalization_test_cases = [
            # A1 (Anglo-Sphere) - Remove titles, normalize punctuation
            ("A1", "Dr. Smith, John Jr.", "Smith, John Jr."),
            ("A1", "Prof. Johnson, Mary, Ph.D.", "Johnson, Mary"),
            ("A1", "Mr. Brown, David, Jr.", "Brown, David Jr."),
            # A2 (Latin America) - Handle Spanish/Portuguese conventions
            ("A2", "García y López, José María", "García y López, José María"),
            ("A2", "da Silva Santos, João", "da Silva Santos, João"),
            # A3 (Germanic) - Handle German conventions
            ("A3", "von Müller, Hans-Peter", "von Müller, Hans-Peter"),
            ("A3", "Dr. med. Schmidt, Klaus", "Schmidt, Klaus"),
            # B1 (Russian/Central Asia) - Handle Cyrillic
            ("B1", "Иванов, Петр Александрович", "Иванов, Петр Александрович"),
            ("B1", "проф. Петров, Александр", "Петров, Александр"),
            # C2 (China) - Handle Chinese conventions
            ("C2", "李明", "李明"),
            ("C2", "王伟华", "王伟华"),
            # C3 (Japan) - Handle Japanese conventions
            ("C3", "田中太郎", "田中太郎"),
            ("C3", "山田花子", "山田花子"),
        ]

        for region_code, input_name, expected_output in normalization_test_cases:
            # Get region processor
            region = self.region_manager.get_region(region_code)
            if not region:
                continue  # Skip if region not implemented

            entry = {"canonical_name": input_name}
            context = ProcessingContext(
                region=RegionalGroup.ANGLOPHONE,  # Will be overridden
                source_data=entry,
                metadata=region.metadata,
            )

            # Apply normalization
            normalized_name = region.normalize_name(input_name, context)

            # Should produce expected output
            assert (
                normalized_name == expected_output
            ), f"Region {region_code} normalization failed: '{input_name}' -> '{normalized_name}', expected '{expected_output}'"

    def test_regional_script_validation(self):
        """Test regional script validation."""
        script_validation_cases = [
            # A1 should accept Latin only
            ("A1", "Smith, John", True),
            ("A1", "García, José", True),  # Latin with diacritics
            ("A1", "李明", False),  # Chinese characters
            ("A1", "Иванов, Петр", False),  # Cyrillic
            # B1 should accept Cyrillic primarily
            ("B1", "Иванов, Петр", True),
            ("B1", "Петров, Александр", True),
            ("B1", "Smith, John", False),  # Wrong script
            # C2 should accept Chinese characters
            ("C2", "李明", True),
            ("C2", "王伟", True),
            ("C2", "Smith, John", False),  # Wrong script
            # B2 should accept Arabic script
            ("B2", "محمد, أحمد", True),
            ("B2", "الخوارزمي, محمد", True),
            ("B2", "Smith, John", False),  # Wrong script
            # H1 (Diaspora) should accept mixed scripts
            ("H1", "Smith, John", True),
            ("H1", "García-李, José-Ming", True),
            ("H1", "Müller-Иванов, Hans-Петр", True),
        ]

        for region_code, name, should_be_valid in script_validation_cases:
            region = self.region_manager.get_region(region_code)
            if not region:
                continue  # Skip if region not implemented

            entry = {"canonical_name": name, "CanonicalLatin": name}
            context = ProcessingContext(
                region=RegionalGroup.ANGLOPHONE,  # Will be overridden
                source_data=entry,
                metadata=region.metadata,
            )

            # Check script validity
            is_valid = region.is_valid_for_region(name, context)

            if should_be_valid:
                assert (
                    is_valid
                ), f"Region {region_code} should accept script for: {name}"
            else:
                assert (
                    not is_valid
                ), f"Region {region_code} should reject script for: {name}"


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
        # Generate test entries
        test_entries = []

        # Different types of entries
        entry_types = [
            {"canonical_name": "Smith, John", "countries": ["US"]},
            {"canonical_name": "García, José", "countries": ["ES"]},
            {"canonical_name": "Müller, Hans", "countries": ["DE"]},
            {"canonical_name": "李明", "countries": ["CN"]},
            {"canonical_name": "田中太郎", "countries": ["JP"]},
            {"canonical_name": "Иванов, Петр", "countries": ["RU"]},
            {"canonical_name": "محمد, أحمد", "countries": ["SA"]},
            {"canonical_name": "Παπαδόπουλος, Γιάννης", "countries": ["GR"]},
            {"canonical_name": "כהן, דוד", "countries": ["IL"]},
            {"canonical_name": "Gupta, Ram", "countries": ["IN"]},
        ]

        # Create 1000 test entries
        for i in range(1000):
            base_entry = random.choice(entry_types)
            entry = base_entry.copy()
            entry["canonical_name"] = f"{base_entry['canonical_name']} {i:04d}"
            test_entries.append(entry)

        # Measure detection performance
        start_time = time.time()

        detections = []
        for entry in test_entries:
            detection = self.region_manager.detect_region(entry)
            detections.append(detection)

        end_time = time.time()

        # Performance assertions
        total_time = end_time - start_time
        entries_per_second = len(test_entries) / total_time

        assert (
            entries_per_second > 100
        ), f"Region detection too slow: {entries_per_second:.1f} entries/second"
        assert len(detections) == len(test_entries), "Not all entries processed"

        # All detections should be valid
        for detection in detections:
            assert detection.region_code is not None, "Invalid region detection"
            assert (
                0.0 <= detection.confidence <= 1.0
            ), f"Invalid confidence: {detection.confidence}"

    def test_concurrent_region_processing(self):
        """Test concurrent region processing."""
        # Generate test entries
        test_entries = []
        for i in range(500):
            entry = {
                "canonical_name": f"TestPerson{i:04d}, John",
                "CanonicalLatin": f"TestPerson{i:04d}, John",
                "countries": ["US"],
                "affiliations": [{"name": f"University{i:04d}", "country": "US"}],
            }
            test_entries.append(entry)

        results = Queue()
        errors = Queue()

        def region_worker(worker_id, entries):
            """Worker that processes region detection."""
            worker_results = []
            worker_errors = []

            for entry in entries:
                try:
                    detection = self.region_manager.detect_region(entry)
                    worker_results.append(
                        (
                            entry["canonical_name"],
                            detection.region_code,
                            detection.confidence,
                        )
                    )
                except Exception as e:
                    worker_errors.append((entry["canonical_name"], str(e)))

            results.put((worker_id, worker_results))
            if worker_errors:
                errors.put((worker_id, worker_errors))

        # Run concurrent workers
        num_workers = 8
        entries_per_worker = len(test_entries) // num_workers

        threads = []
        for i in range(num_workers):
            start_idx = i * entries_per_worker
            end_idx = (
                (i + 1) * entries_per_worker
                if i < num_workers - 1
                else len(test_entries)
            )
            worker_entries = test_entries[start_idx:end_idx]

            thread = threading.Thread(target=region_worker, args=(i, worker_entries))
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
        assert (
            len(worker_errors) == 0
        ), f"Errors during concurrent processing: {worker_errors}"

        # Check result consistency
        total_processed = sum(len(results[1]) for results in worker_results)
        assert total_processed == len(
            test_entries
        ), f"Not all entries processed: {total_processed}"

        # All results should be valid
        for worker_id, results_list in worker_results:
            for name, region_code, confidence in results_list:
                assert region_code is not None, f"Invalid region for {name}"
                assert (
                    0.0 <= confidence <= 1.0
                ), f"Invalid confidence for {name}: {confidence}"

    def test_region_processing_memory_efficiency(self):
        """Test memory efficiency of region processing."""
        import psutil

        # Monitor memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process large number of entries
        for i in range(10000):
            entry = {
                "canonical_name": f"TestPerson{i:06d}, John",
                "CanonicalLatin": f"TestPerson{i:06d}, John",
                "countries": ["US"],
                "name_variants": [f"J. TestPerson{i:06d}", f"John TestPerson{i:06d}"],
                "affiliations": [{"name": f"University{i:06d}", "country": "US"}],
            }

            # Detect region
            detection = self.region_manager.detect_region(entry)

            # Verify detection
            assert detection.region_code is not None, f"Invalid detection for entry {i}"

            # Periodic memory check
            if i % 1000 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_growth = current_memory - initial_memory

                # Should not grow excessively
                assert (
                    memory_growth < 50
                ), f"Excessive memory growth: {memory_growth}MB after {i} entries"

        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_growth = final_memory - initial_memory

        # Should not use excessive memory
        assert (
            total_memory_growth < 100
        ), f"Excessive total memory usage: {total_memory_growth}MB"


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
        """Test quarantine region (Z0) handling."""
        # Entries that should be quarantined
        quarantine_cases = [
            # Invalid/corrupted data
            {"canonical_name": "", "CanonicalLatin": ""},
            {"canonical_name": "???", "CanonicalLatin": "???"},
            {"canonical_name": "NULL", "CanonicalLatin": "NULL"},
            # Unrecognizable scripts
            {"canonical_name": "████████", "CanonicalLatin": "████████"},
            {"canonical_name": "♠♣♦♥", "CanonicalLatin": "♠♣♦♥"},
            # Suspicious entries
            {"canonical_name": "Admin, System", "CanonicalLatin": "Admin, System"},
            {"canonical_name": "Test, User", "CanonicalLatin": "Test, User"},
            {"canonical_name": "Default, Name", "CanonicalLatin": "Default, Name"},
            # Malformed entries
            {"canonical_name": "NoComma", "CanonicalLatin": "NoComma"},
            {"canonical_name": "Too,Many,Commas", "CanonicalLatin": "Too,Many,Commas"},
            {"canonical_name": "   ,   ", "CanonicalLatin": "   ,   "},
        ]

        for entry in quarantine_cases:
            detection = self.region_manager.detect_region(entry)

            # Should be quarantined
            assert (
                detection.region_code == "Z0"
            ), f"Entry should be quarantined: {entry['canonical_name']}, got {detection.region_code}"

            # Should have low confidence
            assert (
                detection.confidence <= 0.1
            ), f"Quarantined entry has high confidence: {detection.confidence}"

    def test_historical_region_handling(self):
        """Test historical region (G1-G3) handling."""
        # Historical entries
        historical_cases = [
            # Ancient (G1)
            {"canonical_name": "Archimedes", "birth_year": -287, "death_year": -212},
            {"canonical_name": "Euclid", "birth_year": -330, "death_year": -270},
            {"canonical_name": "Pythagoras", "birth_year": -570, "death_year": -495},
            # Medieval (G2)
            {"canonical_name": "Al-Khwarizmi", "birth_year": 780, "death_year": 850},
            {"canonical_name": "Fibonacci", "birth_year": 1170, "death_year": 1250},
            {
                "canonical_name": "Oresme, Nicole",
                "birth_year": 1320,
                "death_year": 1382,
            },
            # Early Modern (G3)
            {"canonical_name": "Newton, Isaac", "birth_year": 1643, "death_year": 1727},
            {
                "canonical_name": "Leibniz, Gottfried",
                "birth_year": 1646,
                "death_year": 1716,
            },
            {
                "canonical_name": "Euler, Leonhard",
                "birth_year": 1707,
                "death_year": 1783,
            },
        ]

        for entry in historical_cases:
            detection = self.region_manager.detect_region(entry)

            # Should detect historical region
            assert detection.region_code.startswith(
                "G"
            ), f"Historical entry should be in G region: {entry['canonical_name']}, got {detection.region_code}"

            # Should have reasonable confidence
            assert (
                detection.confidence >= 0.3
            ), f"Historical entry has low confidence: {detection.confidence}"

    def test_diaspora_region_handling(self):
        """Test diaspora region (H1-H3) handling."""
        # Diaspora entries
        diaspora_cases = [
            # H1 - Diaspora with clear origin
            {"canonical_name": "Einstein, Albert", "countries": ["DE", "US", "CH"]},
            {"canonical_name": "Gödel, Kurt", "countries": ["AT", "US"]},
            {"canonical_name": "von Neumann, John", "countries": ["HU", "US"]},
            # H2 - Stateless
            {"canonical_name": "Refugee, Mathematical", "countries": []},
            {"canonical_name": "Nomad, Digital", "countries": ["XX"]},
            # H3 - Multiregional
            {"canonical_name": "García-李, José-Ming", "countries": ["ES", "CN"]},
            {"canonical_name": "Müller-Иванов, Hans-Петр", "countries": ["DE", "RU"]},
            {"canonical_name": "Smith-محمد, John-Ahmad", "countries": ["US", "SA"]},
        ]

        for entry in diaspora_cases:
            detection = self.region_manager.detect_region(entry)

            # Should detect diaspora region
            assert detection.region_code.startswith(
                "H"
            ), f"Diaspora entry should be in H region: {entry['canonical_name']}, got {detection.region_code}"

            # Should have reasonable confidence
            assert (
                detection.confidence >= 0.2
            ), f"Diaspora entry has low confidence: {detection.confidence}"

    def test_region_fallback_mechanisms(self):
        """Test region fallback mechanisms."""
        # Test entries with various levels of information
        fallback_cases = [
            # Full information - should have high confidence
            {
                "canonical_name": "Smith, John",
                "CanonicalLatin": "Smith, John",
                "countries": ["US"],
                "affiliations": [{"name": "Harvard University", "country": "US"}],
                "expected_confidence": 0.8,
            },
            # Partial information - should have medium confidence
            {
                "canonical_name": "García, José",
                "CanonicalLatin": "García, José",
                "countries": ["ES"],
                "expected_confidence": 0.6,
            },
            # Minimal information - should have low confidence
            {
                "canonical_name": "Unknown, Person",
                "CanonicalLatin": "Unknown, Person",
                "expected_confidence": 0.2,
            },
            # Conflicting information - should have reduced confidence
            {
                "canonical_name": "Smith, John",
                "CanonicalLatin": "Smith, John",
                "countries": ["CN"],  # Conflicting country
                "expected_confidence": 0.4,
            },
        ]

        for entry in fallback_cases:
            expected_confidence = entry.pop("expected_confidence")
            detection = self.region_manager.detect_region(entry)

            # Should meet confidence expectations
            assert (
                detection.confidence >= expected_confidence * 0.8
            ), f"Confidence too low for {entry['canonical_name']}: {detection.confidence}, expected >= {expected_confidence * 0.8}"

            # Should have valid region
            assert (
                detection.region_code is not None
            ), f"No region detected for {entry['canonical_name']}"

            # Should have metadata
            assert (
                detection.metadata is not None
            ), f"No metadata for {entry['canonical_name']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
