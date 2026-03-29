"""
from typing import Any
Tests for Thai script processing in E6 Mainland SEA region.

Test coverage:
- Thai script detection and validation
- RTGS romanization accuracy
- Name structure parsing (given/family optional)
- Tone mark preservation
- Common Thai surname recognition
"""

import pytest
from processor import E6_MainlandSEA


class TestThaiProcessing:
    """Test Thai-specific processing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = E6_MainlandSEA()

    @pytest.mark.timeout(15)
    def test_thai_script_detection(self):
        """Test detection of Thai script characters."""
        thai_names = ["สมชาย", "พิมพ์ใจ", "อนุชา ศรีสุข", "ดร.วิทยา จันทร์เพ็ญ"]

        for name in thai_names:
            entry = {"CanonicalNative": name, "GlobalID": "test"}
            self.processor.augment(entry)

            assert "RegionalExtras" in entry
            script = entry["RegionalExtras"].get("detected_script")
            assert script in ["Thai", "Mixed"]

    @pytest.mark.timeout(15)
    def test_thai_surname_recognition(self):
        """Test recognition of common Thai surnames."""
        test_cases = [
            {"name": "สมชาย จันทร์", "expected_family": "จันทร์"},
            {"name": "พิมพ์ใจ วงศ์", "expected_family": "วงศ์"},
            {"name": "อนุชา ศรีสุข", "expected_family": "ศรีสุข"},
        ]

        for case in test_cases:
            entry = {"CanonicalNative": case["name"], "GlobalID": "test"}
            self.processor.augment(entry)

            family = entry.get("RegionalExtras", {}).get("family_name")
            assert family == case["expected_family"]

    @pytest.mark.timeout(15)
    def test_thai_rtgs_romanization(self):
        """Test RTGS romanization generation."""
        test_cases = [
            {"thai": "สมชาย", "rtgs": "Somchai"},
            {"thai": "จันทร์", "rtgs": "Chan"},
            {"thai": "ศรีสุข", "rtgs": "Srisuk"},
        ]

        for case in test_cases:
            entry = {"CanonicalNative": case["thai"], "GlobalID": "test"}
            self.processor.augment(entry)

            # Check if RTGS variant was generated
            variants = entry.get("Variants", {}).get("Synthesised", [])
            rtgs_variants = [v for v in variants if v.get("type") == "rtgs"]

            assert len(rtgs_variants) > 0
            assert any(case["rtgs"] in v["str"] for v in rtgs_variants)

    @pytest.mark.timeout(15)
    def test_thai_tone_preservation(self):
        """Test preservation of Thai tone marks."""
        tone_names = [
            "สมหมาย",  # Contains tone marks
            "พิมพ์ใจ",  # Contains tone marks
            "เจริญศรี",  # Contains tone marks
        ]

        for name in tone_names:
            entry = {"CanonicalNative": name, "GlobalID": "test"}
            self.processor.clean(entry)

            # After cleaning, tone marks should be preserved
            cleaned = entry.get("CanonicalNative", "")
            assert cleaned == name  # Should preserve original tone marks

    @pytest.mark.timeout(15)
    def test_thai_mixed_script(self):
        """Test handling of Thai-Latin mixed names."""
        mixed_names = ["สมชาย Smith", "John ศรีสุข", "ดร.วิทยา Johnson"]

        for name in mixed_names:
            entry = {"CanonicalLatin": name, "GlobalID": "test"}
            self.processor.augment(entry)

            script = entry.get("RegionalExtras", {}).get("detected_script")
            assert script == "Mixed"

    @pytest.mark.timeout(15)
    def test_thai_name_structure_validation(self):
        """Test Thai name structure validation."""
        # Thai names can be given-only or given-family
        valid_structures = [
            "สมชาย",  # Given only
            "สมชาย จันทร์",  # Given Family
            "พิมพ์ใจ ศรีสุข",  # Given Family
        ]

        for name in valid_structures:
            entry = {"CanonicalNative": name, "GlobalID": "test"}
            # Should not raise validation errors
            self.processor.validate(entry)

    @pytest.mark.timeout(15)
    def test_thai_honorific_removal(self):
        """Test removal of Thai honorifics."""
        test_cases = [
            {"input": "คุณสมชาย จันทร์", "expected": "สมชาย จันทร์"},
            {"input": "ดร.วิทยา ศรีสุข", "expected": "วิทยา ศรีสุข"},
            {"input": "พระอาจารย์สมหมาย", "expected": "สมหมาย"},
        ]

        for case in test_cases:
            entry = {"CanonicalNative": case["input"], "GlobalID": "test"}
            self.processor.clean(entry)

            cleaned = entry.get("CanonicalNative", "")
            assert case["expected"] in cleaned

    @pytest.mark.timeout(15)
    def test_thai_royal_elements(self):
        """Test recognition of Thai royal name elements."""
        royal_names = ["พระสมหมาย", "เจ้าวิทยา", "หลวงพิมพ์ใจ"]

        for name in royal_names:
            entry = {"CanonicalNative": name, "GlobalID": "test"}
            self.processor.augment(entry)

            extras = entry.get("RegionalExtras", {})
            assert extras.get("has_royal_elements", False) is True

    @pytest.mark.timeout(15)
    def test_thai_buddhist_elements(self):
        """Test recognition of Thai Buddhist name elements."""
        buddhist_names = ["ธรรมชาติ", "บุญศรี", "กรรมพล"]

        for name in buddhist_names:
            entry = {"CanonicalNative": name, "GlobalID": "test"}
            self.processor.augment(entry)

            extras = entry.get("RegionalExtras", {})
            assert extras.get("has_buddhist_elements", False) is True

    @pytest.mark.timeout(15)
    def test_thai_security_validation(self):
        """Test security validation for Thai text."""
        # Test that security risks are properly detected
        malicious_inputs = [
            "สมชาย\x00",  # NULL character
            "จันทร์\x1f",  # Control character
            "ศรี\ufeffสุข",  # Zero-width character
        ]

        for malicious in malicious_inputs:
            entry = {"CanonicalNative": malicious, "GlobalID": "test"}

            with pytest.raises(Exception):  # Should raise security error
                self.processor.validate(entry)
