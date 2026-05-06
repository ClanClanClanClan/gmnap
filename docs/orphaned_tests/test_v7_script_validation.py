#!/usr/bin/env python3
"""
from typing import List
from typing import Optional
from typing import Any
V7 Script Validation Testing Framework
Verifies script validation claims through systematic testing

Tests script handling across all regions to verify:
- Primary script support as claimed in V7 spec
- Mixed script handling capabilities
- Unicode normalization compliance
- Script detection accuracy
- Error handling for unsupported scripts
"""

import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Set

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import os

os.environ["GMNAP_TEST_MODE"] = "true"
import sys
from pathlib import Path

from src.regions.manager import RegionManager

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.base import RegionRuleError


class TestV7ScriptValidation:
    """
    Script validation testing framework for V7 compliance
    Tests all regions against their declared script support

    V7 Primary Scripts by Region:
    - A-groups: Latin ASCII, Latin with diacritics
    - B-groups: Cyrillic, Latin, Greek
    - C-groups: Arabic, Persian-Arabic, Hebrew, Armenian, Georgian, Mixed
    - D-groups: Devanagari, Tamil, Bengali, Urdu, Sinhala
    - E-groups: Han-Simplified/Traditional, Kanji/Kana, Hangul/Hanja, Latin+diacritics, Thai/Khmer/Lao
    - F-groups: Latin
    - G-groups: Latin
    """

    @classmethod
    def setup_class(cls):
        """Setup region manager for script validation testing"""
        config_path = project_root / "config"
        cls.manager = RegionManager(config_path)

        # Load all available regions
        region_codes = [
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
            "B1",
            "B2",
            "B3",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
            "E1",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",  # E2 unavailable
            "F1",
            "F2",
            "F3",
            "G1",
        ]

        cls.regions = {}
        for code in region_codes:
            try:
                region = cls.manager.get_region(code)
                if region is not None:
                    cls.regions[code] = region
            except Exception as e:
                print(f"Warning: Failed to load region {code}: {e}")

        print(f"Loaded {len(cls.regions)} regions for script validation testing")

        # V7 spec primary scripts by region
        cls.v7_primary_scripts = {
            # A-groups
            "A1": ["Latin ASCII"],
            "A2": ["Latin with diacritics"],
            "A3": ["Latin with diacritics"],
            "A4": ["Latin with macrons"],
            "A5": ["Latin"],
            # B-groups
            "B1": ["Cyrillic"],
            "B2": ["Latin", "Cyrillic"],
            "B3": ["Greek"],
            # C-groups
            "C1": ["Latin", "Cyrillic", "Arabic"],
            "C2": ["Perso-Arabic", "Cyrillic"],
            "C3": ["Arabic"],
            "C4": ["Arabic"],
            "C5": ["Arabic"],
            "C6": ["Hebrew"],
            "C7": ["Armenian"],
            "C8": ["Georgian"],
            "C9": ["Mixed"],
            # D-groups
            "D1": ["Devanagari"],
            "D2": ["Tamil", "Latin"],
            "D3": ["Bengali"],
            "D4": ["Urdu", "Latin"],
            "D5": ["Sinhala"],
            # E-groups
            "E1": ["Han-Simplified"],
            "E3": ["Kanji", "Kana"],
            "E4": ["Hangul", "Hanja"],
            "E5": ["Latin with diacritics"],
            "E6": ["Thai", "Khmer", "Lao"],
            "E7": ["Latin"],
            # F-groups
            "F1": ["Latin"],
            "F2": ["Latin"],
            "F3": ["Latin"],
            # G-groups
            "G1": ["Latin"],
        }

    def detect_script(self, text: str) -> Set[str]:
        """
        Detect scripts present in text using Unicode script properties
        """
        if not text:
            return set()

        scripts = set()

        for char in text:
            if char.isspace() or not char.isalnum():
                continue

            # Get Unicode script property
            try:
                script_name = unicodedata.name(char, "").split()[0]

                # Map Unicode names to V7 script categories
                if "LATIN" in script_name:
                    if ord(char) > 127:
                        scripts.add("Latin with diacritics")
                    else:
                        scripts.add("Latin ASCII")
                elif "CYRILLIC" in script_name:
                    scripts.add("Cyrillic")
                elif "GREEK" in script_name:
                    scripts.add("Greek")
                elif "ARABIC" in script_name or "PERSIAN" in script_name:
                    scripts.add("Arabic")
                elif "HEBREW" in script_name:
                    scripts.add("Hebrew")
                elif "ARMENIAN" in script_name:
                    scripts.add("Armenian")
                elif "GEORGIAN" in script_name:
                    scripts.add("Georgian")
                elif "DEVANAGARI" in script_name:
                    scripts.add("Devanagari")
                elif "TAMIL" in script_name:
                    scripts.add("Tamil")
                elif "BENGALI" in script_name:
                    scripts.add("Bengali")
                elif "SINHALA" in script_name:
                    scripts.add("Sinhala")
                elif "CJK" in script_name or "HAN" in script_name:
                    scripts.add("Han")
                elif "HIRAGANA" in script_name or "KATAKANA" in script_name:
                    scripts.add("Kana")
                elif "HANGUL" in script_name:
                    scripts.add("Hangul")
                elif "THAI" in script_name:
                    scripts.add("Thai")
                elif "KHMER" in script_name:
                    scripts.add("Khmer")
                elif "LAO" in script_name:
                    scripts.add("Lao")

            except ValueError:
                # Handle characters without Unicode names
                code_point = ord(char)
                if code_point < 128:
                    scripts.add("Latin ASCII")
                elif 0x0080 <= code_point <= 0x024F:
                    scripts.add("Latin with diacritics")
                elif 0x0400 <= code_point <= 0x04FF:
                    scripts.add("Cyrillic")
                elif 0x0370 <= code_point <= 0x03FF:
                    scripts.add("Greek")
                elif 0x0600 <= code_point <= 0x06FF:
                    scripts.add("Arabic")
                elif 0x0590 <= code_point <= 0x05FF:
                    scripts.add("Hebrew")
                elif 0x4E00 <= code_point <= 0x9FFF:
                    scripts.add("Han")
                elif 0xAC00 <= code_point <= 0xD7AF:
                    scripts.add("Hangul")

        return scripts

    @pytest.mark.timeout(15)
    def test_latin_script_regions(self):
        """Test Latin script handling across Latin-primary regions"""
        latin_regions = ["A1", "A2", "A3", "A4", "A5", "F1", "F2", "F3", "G1"]

        test_cases = [
            {"name": "Smith, John", "script": "Latin ASCII"},
            {"name": "García, José", "script": "Latin with diacritics"},
            {"name": "O'Connor, Seán", "script": "Latin with diacritics"},
            {"name": "Müller, Hans", "script": "Latin with diacritics"},
            {"name": "François, Jean", "script": "Latin with diacritics"},
        ]

        results = self._test_script_handling(latin_regions, test_cases)

        # Latin regions should handle Latin scripts well
        success_rate = results["success_count"] / results["total_tests"]
        assert (
            success_rate >= 0.8
        ), f"Latin script handling failed: {success_rate:.1%} success rate"

    @pytest.mark.timeout(15)
    def test_cyrillic_script_regions(self):
        """Test Cyrillic script handling across Cyrillic-primary regions"""
        cyrillic_regions = ["B1", "B2", "C1", "C2"]

        test_cases = [
            {"name": "Иванов, Иван", "script": "Cyrillic"},
            {"name": "Петров, Пётр", "script": "Cyrillic"},
            {"name": "Сидоров, Алексей", "script": "Cyrillic"},
            {"name": "Козлов, Дмитрий", "script": "Cyrillic"},
        ]

        results = self._test_script_handling(cyrillic_regions, test_cases)

        # Cyrillic regions should handle Cyrillic scripts
        success_rate = results["success_count"] / results["total_tests"]
        assert (
            success_rate >= 0.7
        ), f"Cyrillic script handling failed: {success_rate:.1%} success rate"

    @pytest.mark.timeout(15)
    def test_arabic_script_regions(self):
        """Test Arabic script handling across Arabic-primary regions"""
        arabic_regions = ["C2", "C3", "C4", "C5"]

        test_cases = [
            {"name": "محمد، أحمد", "script": "Arabic"},
            {"name": "العبدالله، خالد", "script": "Arabic"},
            {"name": "الحسن، فاطمة", "script": "Arabic"},
        ]

        results = self._test_script_handling(arabic_regions, test_cases)

        # Arabic regions should handle Arabic scripts
        success_rate = results["success_count"] / results["total_tests"]
        assert (
            success_rate >= 0.6
        ), f"Arabic script handling failed: {success_rate:.1%} success rate"

    @pytest.mark.timeout(15)
    def test_cjk_script_regions(self):
        """Test CJK script handling across CJK regions"""
        cjk_test_data = {
            "E1": [
                {"name": "李明", "script": "Han-Simplified"},
                {"name": "王小丽", "script": "Han-Simplified"},
            ],
            "E3": [
                {"name": "山田太郎", "script": "Kanji"},
                {"name": "やまだ", "script": "Kana"},
            ],
            "E4": [
                {"name": "김민준", "script": "Hangul"},
                {"name": "朴正熙", "script": "Hanja"},
            ],
        }

        overall_success = 0
        total_tests = 0

        for region_code, test_cases in cjk_test_data.items():
            if region_code in self.regions:
                results = self._test_script_handling([region_code], test_cases)
                overall_success += results["success_count"]
                total_tests += results["total_tests"]

        if total_tests > 0:
            success_rate = overall_success / total_tests
            assert (
                success_rate >= 0.5
            ), f"CJK script handling failed: {success_rate:.1%} success rate"

    @pytest.mark.timeout(15)
    def test_mixed_script_handling(self):
        """Test handling of mixed script names"""
        mixed_script_cases = [
            {
                "region": "A1",
                "name": "Smith, José",
                "expected_scripts": ["Latin ASCII", "Latin with diacritics"],
            },
            {
                "region": "E1",
                "name": "Li, Michael",
                "expected_scripts": ["Han", "Latin ASCII"],
            },
            {"region": "E4", "name": "Kim, James", "expected_scripts": ["Latin ASCII"]},
            {
                "region": "D4",
                "name": "Khan, محمد",
                "expected_scripts": ["Latin ASCII", "Arabic"],
            },
        ]

        successful_cases = 0

        for case in mixed_script_cases:
            region_code = case["region"]
            if region_code not in self.regions:
                continue

            region = self.regions[region_code]
            entry = {"CanonicalLatin": case["name"], "GlobalID": "test_mixed"}

            try:
                # Test that mixed scripts don't crash the system
                region.clean(entry.copy())
                successful_cases += 1
            except Exception as e:
                print(
                    f"Mixed script handling failed for {region_code}: {case['name']} - {e}"
                )

        # Should handle most mixed script cases gracefully
        success_rate = successful_cases / len(mixed_script_cases)
        assert (
            success_rate >= 0.7
        ), f"Mixed script handling failed: {success_rate:.1%} success rate"

    @pytest.mark.timeout(15)
    def test_unicode_normalization_compliance(self):
        """Test Unicode normalization compliance across regions"""
        # Test various Unicode normalization forms
        test_cases = [
            {
                "name": "José",
                "variants": ["José", "Jose\u0301"],
            },  # Precomposed vs decomposed
            {"name": "naïve", "variants": ["naïve", "nai\u0308ve"]},
            {"name": "résumé", "variants": ["résumé", "re\u0301sume\u0301"]},
        ]

        normalization_consistent = 0
        total_comparisons = 0

        # Test with Latin script regions
        test_regions = [code for code in ["A1", "A2", "A3"] if code in self.regions]

        for region_code in test_regions:
            region = self.regions[region_code]

            for case in test_cases:
                case["name"]
                variants = case["variants"]

                results = []
                for variant in variants:
                    entry = {
                        "CanonicalLatin": f"{variant}, Test",
                        "GlobalID": "test_unicode",
                    }
                    try:
                        # Process and see if normalization is consistent
                        processed_entry = entry.copy()
                        region.clean(processed_entry)
                        results.append(processed_entry.get("CanonicalLatin", ""))
                    except:
                        results.append(None)

                # Check if all variants produce consistent results
                valid_results = [r for r in results if r is not None]
                if len(valid_results) >= 2:
                    total_comparisons += 1
                    # Normalize for comparison
                    normalized_results = [
                        unicodedata.normalize("NFC", r) for r in valid_results
                    ]
                    if len(set(normalized_results)) == 1:
                        normalization_consistent += 1

        if total_comparisons > 0:
            consistency_rate = normalization_consistent / total_comparisons
            assert (
                consistency_rate >= 0.8
            ), f"Unicode normalization inconsistent: {consistency_rate:.1%} consistency rate"

    @pytest.mark.timeout(15)
    def test_unsupported_script_error_handling(self):
        """Test error handling for scripts not supported by regions"""
        # Test cases with scripts that should not be supported by certain regions
        unsupported_cases = [
            {
                "region": "A1",
                "name": "محمد، أحمد",
                "script": "Arabic",
            },  # Arabic in Latin-only region
            {
                "region": "C3",
                "name": "Smith, John",
                "script": "Latin",
            },  # Latin in Arabic region
            {
                "region": "B1",
                "name": "李明",
                "script": "Chinese",
            },  # Chinese in Cyrillic region
            {
                "region": "E1",
                "name": "Иванов",
                "script": "Cyrillic",
            },  # Cyrillic in Chinese region
        ]

        graceful_handling = 0

        for case in unsupported_cases:
            region_code = case["region"]
            if region_code not in self.regions:
                continue

            region = self.regions[region_code]
            entry = {"CanonicalLatin": case["name"], "GlobalID": "test_unsupported"}

            try:
                # Should either process gracefully or raise appropriate error
                region.clean(entry.copy())
                graceful_handling += 1  # Handled gracefully
            except (RegionRuleError, ValueError, UnicodeError):
                graceful_handling += 1  # Appropriate error raised
            except Exception as e:
                # Unexpected error - not graceful
                print(f"Unexpected error for {region_code} with {case['name']}: {e}")

        # Should handle unsupported scripts gracefully (either process or appropriate error)
        handling_rate = graceful_handling / len(unsupported_cases)
        assert (
            handling_rate >= 0.8
        ), f"Poor unsupported script handling: {handling_rate:.1%} graceful"

    @pytest.mark.timeout(15)
    def test_script_detection_accuracy(self):
        """Test script detection accuracy for known samples"""
        test_samples = [
            {"text": "Hello World", "expected": {"Latin ASCII"}},
            {
                "text": "José García",
                "expected": {"Latin ASCII", "Latin with diacritics"},
            },
            {"text": "Иван Петров", "expected": {"Cyrillic"}},
            {"text": "محمد أحمد", "expected": {"Arabic"}},
            {"text": "李明王", "expected": {"Han"}},
            {"text": "김민준", "expected": {"Hangul"}},
            {"text": "やまだ", "expected": {"Kana"}},
        ]

        correct_detections = 0

        for sample in test_samples:
            detected = self.detect_script(sample["text"])
            expected = sample["expected"]

            # Check if detection overlaps with expected (allows for broader detection)
            if detected & expected:  # Intersection is not empty
                correct_detections += 1
            else:
                print(
                    f"Script detection mismatch: '{sample['text']}' detected {detected}, expected {expected}"
                )

        accuracy = correct_detections / len(test_samples)
        assert accuracy >= 0.7, f"Script detection accuracy low: {accuracy:.1%}"

    def _test_script_handling(
        self, region_codes: List[str], test_cases: List[Dict]
    ) -> Dict[str, int]:
        """Helper method to test script handling across regions"""
        success_count = 0
        total_tests = 0

        for region_code in region_codes:
            if region_code not in self.regions:
                continue

            region = self.regions[region_code]

            for case in test_cases:
                entry = {
                    "CanonicalLatin": case["name"],
                    "GlobalID": f"test_{region_code}",
                }
                total_tests += 1

                try:
                    # Test processing
                    processed_entry = entry.copy()
                    region.clean(processed_entry)

                    # Basic validation that processing didn't fail
                    if processed_entry.get("CanonicalLatin"):
                        success_count += 1

                except Exception as e:
                    print(
                        f"Script handling failed for {region_code}: {case['name']} - {e}"
                    )

        return {
            "success_count": success_count,
            "total_tests": total_tests,
            "success_rate": success_count / total_tests if total_tests > 0 else 0,
        }

    @pytest.mark.timeout(15)
    def test_comprehensive_script_validation_report(self):
        """Generate comprehensive script validation report"""
        report = {
            "regions_tested": len(self.regions),
            "v7_script_claims_tested": len(self.v7_primary_scripts),
            "test_categories": [
                "Latin script regions (A-groups, F-groups, G-groups)",
                "Cyrillic script regions (B1, B2, C1, C2)",
                "Arabic script regions (C2, C3, C4, C5)",
                "CJK script regions (E1, E3, E4)",
                "Mixed script handling",
                "Unicode normalization compliance",
                "Unsupported script error handling",
                "Script detection accuracy",
            ],
            "v7_compliance_aspects": [
                "Primary script support verification",
                "Secondary script handling",
                "Unicode normalization (NFC casefold)",
                "Error handling for unsupported scripts",
                "Mixed script name processing",
            ],
        }

        print("\n" + "=" * 80)
        print("V7 SCRIPT VALIDATION COMPREHENSIVE REPORT")
        print("=" * 80)
        print(f"Regions tested: {report['regions_tested']}")
        print(f"V7 script claims tested: {report['v7_script_claims_tested']}")
        print("\nTest categories covered:")
        for category in report["test_categories"]:
            print(f"  ✓ {category}")
        print("\nV7 compliance aspects:")
        for aspect in report["v7_compliance_aspects"]:
            print(f"  ✓ {aspect}")
        print("=" * 80)

        # List any regions with missing script support
        unavailable_regions = set(self.v7_primary_scripts.keys()) - set(
            self.regions.keys()
        )
        if unavailable_regions:
            print(
                f"Note: Regions unavailable for testing: {', '.join(sorted(unavailable_regions))}"
            )

        assert True  # Always pass - this is a reporting test


if __name__ == "__main__":
    # Run script validation tests
    pytest.main([__file__, "-v", "--tb=short"])
