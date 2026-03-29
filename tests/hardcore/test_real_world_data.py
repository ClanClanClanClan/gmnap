"""
Hardcore real-world data testing for GMNAP.

Tests with actual problematic mathematician names, real API response patterns,
and data that has caused failures in similar systems.
"""

import json
import unicodedata
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.globalid import GlobalIDGenerator
from src.core.unicode_handler import UnicodeNormalizer
from src.regions.manager import RegionManager
from src.validation.schema import SchemaValidator


class TestRealWorldMathematicianNames:
    """Test with actual problematic mathematician names."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GlobalIDGenerator()
        self.unicode_handler = UnicodeNormalizer()
        self.region_manager = RegionManager(Path("./config"))
        self.validator = SchemaValidator()

        # Clear any existing state
        self.generator.clear()

    def test_historical_arabic_mathematicians(self):
        """Test historical Arabic mathematician names with complex Unicode."""
        # Real names from history that cause processing issues
        arabic_mathematicians = [
            {
                "name": "الخوارزمي، محمد بن موسى",
                "latin": "al-Khwārizmī, Muḥammad ibn Mūsā",
                "birth": "c780",
                "issues": ["mixed_scripts", "diacritics", "ibn_particle", "historical_dating"],
            },
            {
                "name": "أبو عبد الله محمد بن جابر بن سنان البتاني",
                "latin": "al-Battānī, Abū ʿAbd Allāh Muḥammad ibn Jābir ibn Sinān",
                "birth": "858",
                "issues": ["very_long_name", "multiple_ibn", "complex_patronymic"],
            },
            {
                "name": "ابن الهيثم، أبو علي الحسن بن الحسن",
                "latin": "Ibn al-Haytham, Abū ʿAlī al-Ḥasan ibn al-Ḥasan",
                "birth": "965",
                "issues": ["ibn_prefix", "abu_prefix", "repeated_hassan"],
            },
            {
                "name": "عمر الخيام",
                "latin": "ʿUmar al-Khayyām",
                "birth": "1048",
                "issues": ["ayn_initial", "short_name", "persian_origin"],
            },
            {
                "name": "ابن رشد، أبو الوليد محمد بن أحمد",
                "latin": "Ibn Rushd, Abū al-Walīd Muḥammad ibn Aḥmad",
                "birth": "1126",
                "issues": ["ibn_prefix", "abu_prefix", "different_ahmad"],
            },
        ]

        processing_failures = []
        normalization_failures = []
        validation_failures = []

        for mathematician in arabic_mathematicians:
            try:
                # Test Unicode normalization
                normalized_native = self.unicode_handler.normalize(mathematician["name"])
                normalized_latin = self.unicode_handler.normalize(mathematician["latin"])

                # Check for normalization issues
                if not normalized_native or not normalized_latin:
                    normalization_failures.append(mathematician["name"])
                    continue

                # Test GlobalID generation
                entry = {
                    "CanonicalNative": normalized_native,
                    "CanonicalLatin": normalized_latin,
                    "BirthYear": mathematician["birth"],
                }

                global_id = self.generator.generate(entry)

                # Verify GlobalID is valid
                if not global_id or len(global_id) < 22:
                    processing_failures.append(mathematician["name"])
                    continue

                # Test schema validation
                full_entry = {
                    "GlobalID": global_id,
                    "UpdatedAt": "2025-01-01T00:00:00Z",
                    "CanonicalNative": normalized_native,
                    "CanonicalLatin": normalized_latin,
                    "BirthYear": mathematician["birth"],
                    "CountryCodes": ["IQ", "IR", "SA"],  # Historical regions
                    "Confidence": 70,  # Historical uncertainty
                }

                if not self.validator.validate_entry(full_entry):
                    validation_failures.append(mathematician["name"])

            except Exception as e:
                processing_failures.append(f"{mathematician['name']}: {str(e)}")

        # Report failures
        if processing_failures:
            pytest.fail(f"Processing failures on real Arabic names: {processing_failures}")
        if normalization_failures:
            pytest.fail(f"Normalization failures on real Arabic names: {normalization_failures}")
        if validation_failures:
            pytest.fail(f"Validation failures on real Arabic names: {validation_failures}")

    def test_complex_russian_mathematicians(self):
        """Test complex Russian mathematician names with patronymics."""
        russian_mathematicians = [
            {
                "name": "Александр Александрович Ляпунов",
                "latin": "Aleksandr Aleksandrovich Lyapunov",
                "birth": 1857,
                "issues": ["patronymic", "double_aleksandr", "soft_sign"],
            },
            {
                "name": "Пафну́тий Льво́вич Чебышёв",
                "latin": "Pafnuty Lvovich Chebyshev",
                "birth": 1821,
                "issues": ["stress_marks", "unusual_first_name", "ё_character"],
            },
            {
                "name": "Андрей Николаевич Колмогоров",
                "latin": "Andrey Nikolaevich Kolmogorov",
                "birth": 1903,
                "issues": ["patronymic", "spelling_variants"],
            },
            {
                "name": "Софья Васильевна Ковалевская",
                "latin": "Sofia Vasilyevna Kovalevskaya",
                "birth": 1850,
                "issues": ["feminine_patronymic", "feminine_surname", "sofia_sofya"],
            },
            {
                "name": "Николай Иванович Лобачевский",
                "latin": "Nikolai Ivanovich Lobachevsky",
                "birth": 1792,
                "issues": ["patronymic", "transliteration_variants"],
            },
        ]

        for mathematician in russian_mathematicians:
            # Test both Cyrillic and Latin forms
            for name_form in [mathematician["name"], mathematician["latin"]]:
                try:
                    normalized = self.unicode_handler.normalize(name_form)

                    entry = {
                        "CanonicalNative": normalized,
                        "CanonicalLatin": mathematician["latin"],
                        "BirthYear": mathematician["birth"],
                    }

                    global_id = self.generator.generate(entry)

                    # Verify processing succeeded
                    assert global_id is not None, f"Failed to generate GlobalID for {name_form}"
                    assert len(global_id) >= 22, f"Invalid GlobalID length for {name_form}"

                    # Test deterministic generation (clear state first)
                    self.generator.clear()
                    global_id2 = self.generator.generate(entry)
                    assert global_id == global_id2, f"Non-deterministic GlobalID for {name_form}"

                except Exception as e:
                    pytest.fail(f"Failed processing Russian mathematician {name_form}: {str(e)}")

    def test_chinese_mathematician_names(self):
        """Test Chinese mathematician names with various complexities."""
        chinese_mathematicians = [
            {
                "name": "陈省身",
                "latin": "Chen, Shiing-Shen",
                "birth": 1911,
                "issues": ["traditional_chinese", "hyphenated_given"],
            },
            {
                "name": "华罗庚",
                "latin": "Hua, Luogeng",
                "birth": 1910,
                "issues": ["simplified_chinese", "compound_given"],
            },
            {
                "name": "苏步青",
                "latin": "Su, Buchin",
                "birth": 1902,
                "issues": ["pinyin_variations", "generational_name"],
            },
            {
                "name": "李善兰",
                "latin": "Li, Shanlan",
                "birth": 1811,
                "issues": ["historical_chinese", "virtue_name"],
            },
            {
                "name": "祖冲之",
                "latin": "Zu, Chongzhi",
                "birth": 429,
                "issues": ["ancient_chinese", "ancestral_name"],
            },
        ]

        for mathematician in chinese_mathematicians:
            # Test CJK processing
            try:
                normalized_native = self.unicode_handler.normalize(mathematician["name"])
                normalized_latin = self.unicode_handler.normalize(mathematician["latin"])

                # Verify both forms are preserved
                assert normalized_native, f"Lost Chinese name: {mathematician['name']}"
                assert normalized_latin, f"Lost Latin name: {mathematician['latin']}"

                # Test script detection
                detected_script = self.unicode_handler.detect_primary_script(normalized_native)
                assert (
                    detected_script == "CJK"
                ), f"Wrong script detected for {mathematician['name']}: {detected_script}"

                # Test GlobalID generation
                entry = {
                    "CanonicalNative": normalized_native,
                    "CanonicalLatin": normalized_latin,
                    "BirthYear": mathematician["birth"],
                }

                global_id = self.generator.generate(entry)
                assert global_id, f"Failed to generate GlobalID for {mathematician['name']}"

                # Test region detection
                region_result = self.region_manager.detect_region(
                    {
                        "CanonicalNative": normalized_native,
                        "CanonicalLatin": normalized_latin,
                        "CountryCodes": ["CN", "TW"],
                    }
                )

                # Should detect as E1 (Chinese) or fallback appropriately
                assert region_result.region_code in [
                    "E1",
                    "R0",
                    "Z0",
                ], f"Wrong region for {mathematician['name']}: {region_result.region_code}"

            except Exception as e:
                pytest.fail(
                    f"Failed processing Chinese mathematician {mathematician['name']}: {str(e)}"
                )

    def test_unicode_homograph_attacks(self):
        """Test detection and handling of Unicode homograph attacks."""
        # These are visually identical but different Unicode characters
        homograph_attacks = [
            {
                "attack": "Sмith, John",  # Cyrillic 'м' instead of Latin 'm'
                "legitimate": "Smith, John",
                "description": "Cyrillic/Latin homograph",
            },
            {
                "attack": "Мüller, Hans",  # Cyrillic 'М' instead of Latin 'M'
                "legitimate": "Müller, Hans",
                "description": "Mixed script homograph",
            },
            {
                "attack": "Gаrcía, José",  # Cyrillic 'а' instead of Latin 'a'
                "legitimate": "García, José",
                "description": "Subtle Cyrillic substitution",
            },
            {
                "attack": "Ѕmith, John",  # Macedonian 'Ѕ' instead of Latin 'S'
                "legitimate": "Smith, John",
                "description": "Macedonian homograph",
            },
        ]

        for attack_case in homograph_attacks:
            attack_name = attack_case["attack"]
            legitimate_name = attack_case["legitimate"]

            # Generate GlobalIDs for both
            attack_entry = {"CanonicalNative": attack_name}
            legitimate_entry = {"CanonicalNative": legitimate_name}

            attack_id = self.generator.generate(attack_entry)
            legitimate_id = self.generator.generate(legitimate_entry)

            # They should generate different GlobalIDs
            assert (
                attack_id != legitimate_id
            ), f"Homograph attack not detected: {attack_case['description']}"

            # Test normalization differences
            attack_normalized = self.unicode_handler.normalize(attack_name)
            legitimate_normalized = self.unicode_handler.normalize(legitimate_name)

            # Normalization should preserve the differences
            assert (
                attack_normalized != legitimate_normalized
            ), f"Normalization failed to preserve homograph differences: {attack_case['description']}"

    def test_mixed_script_mathematician_names(self):
        """Test mathematician names with mixed scripts."""
        mixed_script_cases = [
            {
                "name": "Владимир Voevodsky",  # Russian + Latin
                "issues": ["cyrillic_latin_mix", "surname_transliteration"],
            },
            {
                "name": "陈省身 Chen",  # Chinese + Latin
                "issues": ["cjk_latin_mix", "name_order_confusion"],
            },
            {
                "name": "محمد Al-Khwarizmi",  # Arabic + Latin
                "issues": ["arabic_latin_mix", "prefix_confusion"],
            },
            {
                "name": "Γαλουά Évariste",  # Greek + Latin
                "issues": ["greek_latin_mix", "accent_preservation"],
            },
            {
                "name": "राम Ramanujan",  # Devanagari + Latin
                "issues": ["devanagari_latin_mix", "pronunciation_variants"],
            },
        ]

        for case in mixed_script_cases:
            name = case["name"]

            try:
                # Test Unicode processing
                normalized = self.unicode_handler.normalize(name)
                assert normalized, f"Failed to normalize mixed script name: {name}"

                # Test script detection
                scripts = self.unicode_handler.get_script_info(name)
                assert len(scripts) > 1, f"Failed to detect mixed scripts in: {name}"

                # Test GlobalID generation
                entry = {"CanonicalNative": normalized}
                global_id = self.generator.generate(entry)
                assert global_id, f"Failed to generate GlobalID for mixed script name: {name}"

                # Test region detection (should likely go to Z0 for mixed scripts)
                region_result = self.region_manager.detect_region(
                    {"CanonicalNative": normalized, "CanonicalLatin": normalized}
                )

                # Mixed script names should be handled carefully
                assert (
                    region_result.confidence < 0.8
                ), f"Too high confidence for mixed script name: {name}"

            except Exception as e:
                pytest.fail(f"Failed processing mixed script name {name}: {str(e)}")

    def test_problematic_punctuation_cases(self):
        """Test mathematician names with problematic punctuation."""
        punctuation_cases = [
            {
                "name": "d'Alembert, Jean le Rond",
                "issues": ["apostrophe_in_surname", "article_prefix"],
            },
            {"name": "O'Sullivan, Denis", "issues": ["irish_apostrophe", "ambiguous_parsing"]},
            {
                "name": "van 't Hoff, Jacobus",
                "issues": ["dutch_contraction", "particle_with_apostrophe"],
            },
            {"name": "Łukasiewicz, Jan", "issues": ["polish_l_stroke", "pronunciation_variants"]},
            {"name": "Erdős, Paul", "issues": ["hungarian_double_acute", "umlaut_variants"]},
            {"name": "Pólya, George", "issues": ["hungarian_acute", "name_anglicization"]},
        ]

        for case in punctuation_cases:
            name = case["name"]

            try:
                # Test normalization preserves critical punctuation
                normalized = self.unicode_handler.normalize(name)
                assert normalized, f"Normalization failed for: {name}"

                # Test that family name parsing works correctly
                parts = normalized.split(", ")
                assert len(parts) == 2, f"Failed to parse family/given for: {name}"

                family_name, given_name = parts
                assert family_name and given_name, f"Empty name parts for: {name}"

                # Test GlobalID generation
                entry = {"CanonicalNative": normalized}
                global_id = self.generator.generate(entry)
                assert global_id, f"Failed to generate GlobalID for: {name}"

                # Test deterministic generation with punctuation
                # Clear generator to test true determinism
                self.generator.clear()
                global_id2 = self.generator.generate(entry)
                assert global_id == global_id2, f"Non-deterministic GlobalID for: {name}"

            except Exception as e:
                pytest.fail(f"Failed processing punctuation case {name}: {str(e)}")

    def test_extreme_unicode_edge_cases(self):
        """Test extreme Unicode edge cases that could break processing."""
        extreme_cases = [
            {
                "name": "A\u0300\u0301\u0302\u0303\u0304, B\u0305\u0306\u0307\u0308\u0309",
                "description": "Multiple combining characters",
            },
            {"name": "𝕊𝕞𝕚𝕥𝕙, 𝕁𝕠𝕙𝕟", "description": "Mathematical alphanumeric symbols"},
            {"name": "Ｓｍｉｔｈ，Ｊｏｈｎ", "description": "Full-width characters"},
            {"name": "Smith\u200b, \u200cJohn\u200d", "description": "Zero-width characters"},
            {"name": "Smith\ufeff, John\u061c", "description": "Invisible formatting characters"},
        ]

        for case in extreme_cases:
            name = case["name"]
            description = case["description"]

            try:
                # Test that extreme Unicode doesn't break processing
                normalized = self.unicode_handler.normalize(name)

                # Should handle gracefully - either normalize or reject cleanly
                if normalized:
                    # If it normalizes, should be valid
                    entry = {"CanonicalNative": normalized}
                    global_id = self.generator.generate(entry)
                    assert (
                        global_id
                    ), f"Failed to generate GlobalID after normalization: {description}"
                else:
                    # If it rejects, should be clean rejection
                    assert True, f"Clean rejection of extreme Unicode: {description}"

            except Exception as e:
                # Should never crash - extreme Unicode should be handled gracefully
                pytest.fail(f"Crashed on extreme Unicode case {description}: {str(e)}")

    def test_real_database_corruption_patterns(self):
        """Test patterns that have caused corruption in real databases."""
        # These are actual patterns that have caused issues in production systems
        corruption_patterns = [
            {"name": "Smith, John\x00", "issue": "null_byte_injection"},
            {"name": "Smith, John\r\n", "issue": "crlf_injection"},
            {"name": "Smith, John\t\t\t", "issue": "tab_injection"},
            {"name": "Smith, John" + "\u0000" * 10, "issue": "multiple_null_bytes"},
            {"name": "Smith, John" + "\ufffe\uffff", "issue": "unicode_noncharacters"},
        ]

        for pattern in corruption_patterns:
            name = pattern["name"]
            issue = pattern["issue"]

            try:
                # Test that corruption patterns are handled safely
                normalized = self.unicode_handler.normalize(name)

                # Should either clean the input or reject it
                if normalized:
                    # If cleaned, should be safe
                    assert "\x00" not in normalized, f"Null bytes not cleaned: {issue}"
                    assert "\r" not in normalized, f"CR not cleaned: {issue}"
                    assert "\n" not in normalized, f"LF not cleaned: {issue}"

                    # Should be able to process safely
                    entry = {"CanonicalNative": normalized}
                    global_id = self.generator.generate(entry)
                    assert global_id, f"Failed to generate GlobalID after cleaning: {issue}"

            except Exception as e:
                # Should handle gracefully, not crash
                assert (
                    "safely handled" in str(e).lower() or "rejected" in str(e).lower()
                ), f"Unsafe handling of corruption pattern {issue}: {str(e)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
