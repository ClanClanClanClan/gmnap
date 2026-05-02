import pytest

#!/usr/bin/env python3
"""
Test suite for F3 Horn of Africa region processor
Tests Ethiopian and Eritrean mathematician name processing
"""

import sys
import unittest
from pathlib import Path

# Add the source directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.f_groups.f3_horn_of_africa.processor import F3_HornOfAfrica


class TestF3HornOfAfricaProcessor(unittest.TestCase):
    """Test F3 Horn of Africa processor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = F3_HornOfAfrica()

    @pytest.mark.timeout(15)
    def test_processor_initialization(self):
        """Test processor initializes correctly."""
        self.assertEqual(self.processor.code, "F3")
        self.assertIn("Ethiopic", self.processor.scripts)
        self.assertIn("Latin", self.processor.scripts)
        self.assertEqual(self.processor.canonical_order, "Patronymic")

    @pytest.mark.timeout(15)
    def test_ethiopic_script_detection(self):
        """Test Ethiopic script detection."""
        # Test Ethiopic text
        ethiopic_text = "ገብረ ማርያም"
        self.assertTrue(self.processor._contains_ethiopic(ethiopic_text))

        # Test Latin text
        latin_text = "Gebre Mariam"
        self.assertFalse(self.processor._contains_ethiopic(latin_text))

        # Test mixed text
        mixed_text = "ገብረ Mariam"
        self.assertTrue(self.processor._contains_ethiopic(mixed_text))

    @pytest.mark.timeout(15)
    def test_clean_ethiopic_name(self):
        """Test cleaning of Ethiopic names."""
        # Test basic cleaning
        dirty_name = "  አባ  ገብረ፡ማርያም  "
        cleaned = self.processor._clean_ethiopic_name(dirty_name)
        self.assertNotIn("አባ", cleaned)  # Title removed
        self.assertEqual(cleaned.count("፡"), 1)  # Word separator normalized

    @pytest.mark.timeout(15)
    def test_clean_latin_name(self):
        """Test cleaning of Latin names."""
        # Test title removal
        dirty_name = "Dr. Gebre Mariam Tekle"
        cleaned = self.processor._clean_latin_name(dirty_name)
        self.assertNotIn("Dr.", cleaned)
        self.assertEqual(cleaned, "Gebre Mariam Tekle")

        # Test multiple titles
        complex_name = "Professor Ato Haile Selassie Bekele"
        cleaned = self.processor._clean_latin_name(complex_name)
        self.assertNotIn("Professor", cleaned)
        self.assertNotIn("Ato", cleaned)
        self.assertEqual(cleaned, "Haile Selassie Bekele")

    @pytest.mark.timeout(15)
    def test_patronymic_structure_analysis(self):
        """Test patronymic structure analysis."""
        # Test standard three-name pattern
        entry = {"CanonicalLatin": "Gebre Mariam Tekle"}
        analysis = self.processor._analyze_patronymic_structure(entry)

        self.assertEqual(analysis["given_name"], "Gebre")
        self.assertEqual(analysis["father_name"], "Mariam")
        self.assertEqual(analysis["grandfather_name"], "Tekle")
        self.assertEqual(analysis["structure"], "given_father_grandfather")

        # Test two-name pattern
        entry = {"CanonicalLatin": "Haile Selassie"}
        analysis = self.processor._analyze_patronymic_structure(entry)
        self.assertEqual(analysis["structure"], "given_father")

    @pytest.mark.timeout(15)
    def test_ethnic_background_analysis(self):
        """Test ethnic background analysis."""
        # Test Amhara patterns
        amhara_entry = {
            "CanonicalLatin": "Abebe Bekele",
            "Affiliation": "Addis Ababa University",
        }
        analysis = self.processor._analyze_ethnic_background(amhara_entry)
        self.assertIn("amhara", analysis.get("ethnicity_scores", {}))

        # Test Oromo patterns
        oromo_entry = {
            "CanonicalLatin": "Gemechu Lemma",
            "Affiliation": "Jimma University",
        }
        analysis = self.processor._analyze_ethnic_background(oromo_entry)
        self.assertIn("oromo", analysis.get("ethnicity_scores", {}))

    @pytest.mark.timeout(15)
    def test_country_determination(self):
        """Test country determination (Ethiopia vs Eritrea)."""
        # Test Ethiopian indicators
        eth_entry = {
            "CanonicalLatin": "Desta Haile",
            "Affiliation": "Addis Ababa University",
            "Email": "desta@aau.edu.et",
        }
        country = self.processor._determine_country(eth_entry, {})
        self.assertEqual(country, "ET")

        # Test Eritrean indicators
        eri_entry = {
            "CanonicalLatin": "Berhe Kiros",
            "Affiliation": "University of Asmara",
            "Email": "berhe@uoa.edu.er",
        }
        country = self.processor._determine_country(eri_entry, {})
        self.assertEqual(country, "ER")

    @pytest.mark.timeout(15)
    def test_variant_generation(self):
        """Test variant generation."""
        entry = {
            "CanonicalLatin": "Gebre Mariam Tekle",
            "CanonicalNative": "ገብረ ማርያም ተክለ",
        }

        ethnic_analysis = {"primary_ethnicity": "amhara"}
        patronymic_analysis = {
            "given_name": "Gebre",
            "father_name": "Mariam",
            "grandfather_name": "Tekle",
            "structure": "given_father_grandfather",
        }

        variants = self.processor._generate_variants(
            entry, ethnic_analysis, patronymic_analysis
        )

        # Should have various types of variants
        variant_types = [v.get("type") for v in variants]
        self.assertIn("patronymic_given_father", variant_types)
        self.assertIn("mononym_given", variant_types)
        self.assertIn("academic_initial", variant_types)

    @pytest.mark.timeout(15)
    def test_full_processing_workflow(self):
        """Test complete processing workflow."""
        entry = {
            "CanonicalLatin": "Professor Ato Gebre Mariam Tekle",
            "CanonicalNative": "አባ ገብረ ማርያም ተክለ",
            "Affiliation": "Addis Ababa University",
            "Email": "gebre@aau.edu.et",
        }

        # Test cleaning
        self.processor.clean(entry)
        self.assertNotIn("Professor", entry.get("CanonicalLatin", ""))
        self.assertNotIn("Ato", entry.get("CanonicalLatin", ""))
        self.assertNotIn("አባ", entry.get("CanonicalNative", ""))

        # Test augmentation
        self.processor.augment(entry)
        self.assertIn("RegionalExtras", entry)
        self.assertIn("Variants", entry)

        regional_extras = entry["RegionalExtras"]
        self.assertEqual(regional_extras["likely_country"], "ET")
        self.assertIn("ethnic_background", regional_extras)
        self.assertIn("patronymic_structure", regional_extras)

        # Test validation (should not raise)
        try:
            self.processor.validate(entry)
        except Exception as e:
            self.fail(f"Validation failed: {e}")

    @pytest.mark.timeout(15)
    def test_order_key_generation(self):
        """Test sort key generation."""
        entry = {
            "CanonicalLatin": "Gebre Mariam Tekle",
            "RegionalExtras": {
                "patronymic_structure": {
                    "given_name": "Gebre",
                    "father_name": "Mariam",
                    "grandfather_name": "Tekle",
                    "structure": "given_father_grandfather",
                }
            },
        }

        order_key = self.processor.order_key(entry)
        self.assertEqual(order_key, "gebre mariam tekle")

    @pytest.mark.timeout(15)
    def test_security_validation(self):
        """Test security validation."""
        # Test malicious input
        malicious_entry = {
            "CanonicalLatin": "<script>alert('xss')</script>",
            "CanonicalNative": "'; DROP TABLE names; --",
        }

        with self.assertRaises(Exception):
            self.processor.clean(malicious_entry)

    @pytest.mark.timeout(15)
    def test_religious_elements_detection(self):
        """Test detection of religious elements."""
        # Christian elements
        christian_entry = {"CanonicalLatin": "Gebre Mariam Michael"}
        self.assertTrue(self.processor._has_religious_elements(christian_entry))

        # Islamic elements
        islamic_entry = {"CanonicalLatin": "Ahmed Hassan Ibrahim"}
        self.assertTrue(self.processor._has_religious_elements(islamic_entry))

        # Secular elements
        # This might still return True due to common religious names

    @pytest.mark.timeout(15)
    def test_transliteration(self):
        """Test Ethiopic transliteration."""
        ethiopic_text = "ገብረ"
        mapping = {"ገ": "ge", "ብ": "b", "ረ": "re"}

        result = self.processor._transliterate_ethiopic(ethiopic_text, mapping)
        self.assertEqual(result, "gebre")

    @pytest.mark.timeout(15)
    def test_script_validation(self):
        """Test script validation."""
        # Valid Ethiopic
        valid_ethiopic = "ገብረ ማርያም"
        self.assertTrue(self.processor._is_valid_ethiopic_text(valid_ethiopic))

        # Valid Latin
        valid_latin = "Gebre Mariam"
        self.assertTrue(self.processor._is_valid_latin_text(valid_latin))

        # Invalid mixed (depends on implementation)
        # This test depends on specific validation rules

    @pytest.mark.timeout(15)
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty entry — F3 must handle "gracefully" (no raise),
        # leaving the entry mostly empty. Round-21 de-bandaid:
        # was `try/except: pass`, which would silently mask any
        # regression that introduced an unhandled exception.
        empty_entry = {}
        self.processor.clean(empty_entry)
        self.processor.augment(empty_entry)
        # Empty in → empty out (or with augmented metadata fields,
        # but no CanonicalLatin since it wasn't supplied).
        assert isinstance(empty_entry, dict)

        # Single name
        single_name_entry = {"CanonicalLatin": "Gebre"}
        analysis = self.processor._analyze_patronymic_structure(single_name_entry)
        self.assertEqual(analysis["structure"], "mononym")

        # Very long name
        long_name_entry = {
            "CanonicalLatin": "Gebre Mariam Tekle Haile Selassie Desta Bekele"
        }
        analysis = self.processor._analyze_patronymic_structure(long_name_entry)
        self.assertEqual(analysis["structure"], "extended_patronymic")


def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
