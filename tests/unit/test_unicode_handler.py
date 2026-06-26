"""
Tests for Unicode normalization pipeline.
"""

import pytest

from src.core.unicode_handler import UnicodeHandlerConfig as UnicodeConfig
from src.core.unicode_handler import (
    UnicodeNormalizer,
    generate_name_variants,
    normalize_name,
)


class TestUnicodeNormalizer:
    """Test Unicode normalization functionality."""

    def test_basic_normalization(self):
        """Test basic NFC normalization."""
        normalizer = UnicodeNormalizer()

        # Test basic Latin text
        assert normalizer.normalize("Smith, John") == "Smith, John"

        # Test accented characters
        assert normalizer.normalize("García, José") == "García, José"

        # Test empty string
        assert normalizer.normalize("") == ""

    def test_ligature_decomposition(self):
        """Test ligature decomposition (Rule 16)."""
        normalizer = UnicodeNormalizer()

        # Test æ/Æ ligature
        assert normalizer.normalize("Cæsar") == "Caesar"
        assert normalizer.normalize("CÆSAR") == "CAESAR"

        # Test œ/Œ ligature
        assert normalizer.normalize("Œuvre") == "Oeuvre"

        # Test ß/ẞ sharp s
        assert normalizer.normalize("Weiß") == "Weiss"
        assert normalizer.normalize("WEIẞ") == "WEISS"

        # Test fi/fl ligatures
        assert normalizer.normalize("ﬁnite") == "finite"
        assert normalizer.normalize("ﬂower") == "flower"

    def test_greek_tonos_oxia(self):
        """Test Greek tonos = oxia rule."""
        normalizer = UnicodeNormalizer()

        # Test Greek characters with tonos
        result = normalizer.normalize("Παπαδόπουλος")
        assert "ό" in result  # Should contain oxia

    def test_sharp_s_variants(self):
        """Test sharp-s variant generation."""
        normalizer = UnicodeNormalizer()

        variants = normalizer.generate_variants("Weiß")
        assert "Weiss" in variants
        assert "Weiß" in variants
        assert len(variants) >= 2

        variants = normalizer.generate_variants("WEIẞ")
        assert "WEISS" in variants
        assert "WEIẞ" in variants

    def test_script_detection(self):
        """Test script detection functionality."""
        normalizer = UnicodeNormalizer()

        # Test Latin script
        script_info = normalizer.get_script_info("Smith, John")
        assert "Latin" in script_info
        assert script_info["Latin"] > 0

        # Test Cyrillic script
        script_info = normalizer.get_script_info("Иванов")
        assert "Cyrillic" in script_info

        # Test Greek script
        script_info = normalizer.get_script_info("Παπαδόπουλος")
        assert "Greek" in script_info

        # Test Arabic script
        script_info = normalizer.get_script_info("الخوارزمي")
        assert "Arabic" in script_info

    def test_primary_script_detection(self):
        """Test primary script detection."""
        normalizer = UnicodeNormalizer()

        assert normalizer.detect_primary_script("Smith, John") == "Latin"
        assert normalizer.detect_primary_script("Иванов") == "Cyrillic"
        assert normalizer.detect_primary_script("田中") == "CJK"
        assert normalizer.detect_primary_script("") == "Unknown"

    def test_mixed_script_detection(self):
        """Test mixed script detection."""
        normalizer = UnicodeNormalizer()

        # Pure scripts should not be mixed
        assert not normalizer.is_mixed_script("Smith, John")
        assert not normalizer.is_mixed_script("Иванов")

        # Mixed scripts should be detected
        assert normalizer.is_mixed_script("Smith 田中")
        assert normalizer.is_mixed_script("José Смирнов")  # Latin + Cyrillic mixed

    def test_normalization_validation(self):
        """Test normalization validation."""
        normalizer = UnicodeNormalizer()

        # Valid normalizations
        assert normalizer.validate_normalization("Smith", "Smith")
        assert normalizer.validate_normalization("García", "Garcia")

        # Critical characters should be preserved
        original = "Smith123"
        normalized = normalizer.normalize(original)
        assert normalizer.validate_normalization(original, normalized)

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Test normalize_name
        assert normalize_name("García") == "García"
        assert normalize_name("Weiß") == "Weiss"

        # Test generate_name_variants
        variants = generate_name_variants("Weiß")
        assert "Weiss" in variants
        assert len(variants) >= 2

    def test_config_options(self):
        """Test configuration options."""
        # Test with ligatures disabled
        config = UnicodeConfig(handle_ligatures=False)
        normalizer = UnicodeNormalizer(config)

        # Ligatures should not be decomposed
        assert normalizer.normalize("Cæsar") == "Cæsar"

        # Test with sharp-s disabled
        config = UnicodeConfig(handle_sharp_s=False)
        normalizer = UnicodeNormalizer(config)

        variants = normalizer.generate_variants("Weiß")
        assert len(variants) == 1  # Only original
        assert variants[0] == "Weiß"

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        normalizer = UnicodeNormalizer()

        # Empty strings
        assert normalizer.normalize("") == ""
        assert normalizer.generate_variants("") == [""]

        # Whitespace only
        assert normalizer.normalize("   ") == "   "

        # Numbers and punctuation
        assert normalizer.normalize("123-456") == "123-456"

        # Very long strings
        long_text = "a" * 10000
        normalized = normalizer.normalize(long_text)
        assert len(normalized) == 10000
        assert normalized == long_text


if __name__ == "__main__":
    pytest.main([__file__])
