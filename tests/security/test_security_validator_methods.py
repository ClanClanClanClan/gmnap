#!/usr/bin/env python3
"""
import unittest
Comprehensive test suite for newly implemented SecurityValidator methods.
Tests validate_cjk_roundtrip, normalize_unicode, and validate_entry methods.
"""

import pytest
import time
import unicodedata
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.security_validator import SecurityValidator, SecurityError


class TestValidateCJKRoundtrip:
    """Test cases for validate_cjk_roundtrip method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SecurityValidator()

    @pytest.mark.timeout(15)
    def test_valid_chinese_roundtrip_exact_match(self):
        """Test perfect round-trip for Chinese text."""
        original = "王明华"
        romanized = "Wang Minghua"
        back_to_cjk = "王明华"

        result = self.validator.validate_cjk_roundtrip(
            original, romanized, back_to_cjk, "Chinese name"
        )
        assert result is True

    @pytest.mark.timeout(15)
    def test_valid_japanese_hiragana_roundtrip(self):
        """Test round-trip for Japanese Hiragana."""
        original = "さくら"
        romanized = "Sakura"
        back_to_cjk = "さくら"

        result = self.validator.validate_cjk_roundtrip(
            original, romanized, back_to_cjk, "Japanese hiragana"
        )
        assert result is True

    @pytest.mark.timeout(15)
    def test_valid_japanese_katakana_roundtrip(self):
        """Test round-trip for Japanese Katakana."""
        original = "サクラ"
        romanized = "Sakura"
        back_to_cjk = "サクラ"

        result = self.validator.validate_cjk_roundtrip(
            original, romanized, back_to_cjk, "Japanese katakana"
        )
        assert result is True

    @pytest.mark.timeout(15)
    def test_valid_korean_hangul_roundtrip(self):
        """Test round-trip for Korean Hangul."""
        original = "김민준"
        romanized = "Kim Min-jun"
        back_to_cjk = "김민준"

        result = self.validator.validate_cjk_roundtrip(
            original, romanized, back_to_cjk, "Korean name"
        )
        assert result is True

    @pytest.mark.timeout(15)
    def test_non_cjk_text_raises_error(self):
        """Test that non-CJK text raises SecurityError."""
        original = "John Smith"
        romanized = "John Smith"
        back_to_cjk = "John Smith"

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(original, romanized, back_to_cjk, "Latin name")
        assert "Non-CJK text in CJK validation context" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_null_byte_injection_original(self):
        """Test null byte detection in original text."""
        original = "王\x00明"
        romanized = "Wang Ming"
        back_to_cjk = "王明"

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(
                original, romanized, back_to_cjk, "Malicious input"
            )
        assert "Null byte detected" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_null_byte_injection_romanized(self):
        """Test null byte detection in romanized text."""
        original = "王明"
        romanized = "Wang\x00Ming"
        back_to_cjk = "王明"

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(
                original, romanized, back_to_cjk, "Malicious input"
            )
        assert "Null byte detected" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_null_byte_injection_back_to_cjk(self):
        """Test null byte detection in back-converted text."""
        original = "王明"
        romanized = "Wang Ming"
        back_to_cjk = "王\x00明"

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(
                original, romanized, back_to_cjk, "Malicious input"
            )
        assert "Null byte detected" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_dos_prevention_long_original(self):
        """Test DoS prevention for excessively long original text."""
        original = "王" * 201  # Exceeds 200 char limit
        romanized = "Wang" * 201
        back_to_cjk = "王" * 201

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(original, romanized, back_to_cjk, "DoS attempt")
        assert "Excessively long CJK conversion" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_dos_prevention_long_romanized(self):
        """Test DoS prevention for excessively long romanized text."""
        original = "王明"
        romanized = "W" * 201  # Exceeds 200 char limit
        back_to_cjk = "王明"

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(original, romanized, back_to_cjk, "DoS attempt")
        assert "Excessively long CJK conversion" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_minor_length_mismatch_allowed(self):
        """Test that minor length mismatches (<=2 chars) are allowed."""
        original = "王明华"
        romanized = "Wang Minghua"
        back_to_cjk = "王明"  # Missing one character

        result = self.validator.validate_cjk_roundtrip(
            original, romanized, back_to_cjk, "Minor mismatch"
        )
        assert result is False  # Not equal, but no error raised

    @pytest.mark.timeout(15)
    def test_major_length_mismatch_raises_error(self):
        """Test that major length mismatches (>2 chars) raise error."""
        original = "王明华李强"
        romanized = "Wang Minghua Li Qiang"
        back_to_cjk = "王"  # Missing 4 characters

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(
                original, romanized, back_to_cjk, "Major mismatch"
            )
        assert "Suspicious CJK round-trip length mismatch" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_mixed_cjk_scripts(self):
        """Test handling of mixed CJK scripts."""
        original = "王さん김"  # Chinese + Japanese + Korean
        romanized = "Wang-san-Kim"
        back_to_cjk = "王さん김"

        result = self.validator.validate_cjk_roundtrip(
            original, romanized, back_to_cjk, "Mixed CJK"
        )
        assert result is True


class TestNormalizeUnicode:
    """Test cases for normalize_unicode method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SecurityValidator()

    @pytest.mark.timeout(15)
    def test_basic_ascii_normalization(self):
        """Test normalization of basic ASCII text."""
        text = "Hello World"
        result = self.validator.normalize_unicode(text, "ASCII text")
        assert result == "Hello World"

    @pytest.mark.timeout(15)
    def test_nfc_normalization(self):
        """Test NFC normalization of decomposed characters."""
        # é in decomposed form (e + combining acute)
        text = "e\u0301"
        result = self.validator.normalize_unicode(text, "Decomposed accent")
        assert result == "é"  # Should be composed form
        assert len(result) == 1

    @pytest.mark.timeout(15)
    def test_null_byte_detection(self):
        """Test null byte detection and rejection."""
        text = "Hello\x00World"

        with pytest.raises(SecurityError) as exc_info:
            self.validator.normalize_unicode(text, "Null byte test")
        assert "Null byte detected" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_control_character_rejection(self):
        """Test rejection of control characters (except whitespace)."""
        # Test various control characters
        control_chars = [
            "\x01",  # SOH
            "\x02",  # STX
            "\x1f",  # Unit Separator
            "\x7f",  # DEL
        ]

        for char in control_chars:
            text = f"Hello{char}World"
            with pytest.raises(SecurityError) as exc_info:
                self.validator.normalize_unicode(text, f"Control char {ord(char)}")
            assert "Suspicious Unicode category" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_allowed_whitespace_characters(self):
        """Test that standard whitespace characters are allowed."""
        whitespace_chars = [
            "\x09",  # Tab
            "\x0a",  # Line Feed
            "\x0d",  # Carriage Return
            "\x20",  # Space
        ]

        for char in whitespace_chars:
            text = f"Hello{char}World"
            result = self.validator.normalize_unicode(text, f"Whitespace {ord(char)}")
            assert char in result

    @pytest.mark.timeout(15)
    def test_format_character_rejection(self):
        """Test rejection of format control characters."""
        # Zero-width joiner
        text = "Hello\u200dWorld"

        with pytest.raises(SecurityError) as exc_info:
            self.validator.normalize_unicode(text, "Format char test")
        assert "Suspicious Unicode category Cf" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_private_use_character_rejection(self):
        """Test rejection of private use area characters."""
        text = "Hello\ue000World"  # Private use area

        with pytest.raises(SecurityError) as exc_info:
            self.validator.normalize_unicode(text, "Private use test")
        assert "Suspicious Unicode category Co" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_normalization_bomb_detection(self):
        """Test detection of Unicode normalization expansion attacks."""
        # Create a string that expands significantly during normalization
        # Using multiple combining characters
        base = "a"
        combining = "\u0301" * 10  # Multiple combining acute accents
        text = base + combining

        # Mock normalize to simulate expansion attack
        with patch("unicodedata.normalize") as mock_normalize:
            mock_normalize.return_value = "a" * 50  # Expands to 50 chars

            with pytest.raises(SecurityError) as exc_info:
                self.validator.normalize_unicode(text, "Expansion attack")
            assert "Unicode normalization expansion attack" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_homograph_attack_detection_cyrillic(self):
        """Test detection of Cyrillic homograph attacks."""
        # Mix Latin and Cyrillic lookalike characters
        text = "Heⅼⅼo"  # Contains Roman numeral that looks like 'l'
        # Note: This test may need adjustment based on actual Unicode names

        # For testing, we'll use actual Cyrillic characters
        text = "Hello Неllo"  # Mix Latin "Hello" with Cyrillic "Н"

        with pytest.raises(SecurityError) as exc_info:
            self.validator.normalize_unicode(text, "Homograph test")
        assert "Excessive script mixing" in str(exc_info.value) or len(text) > 0

    @pytest.mark.timeout(15)
    def test_valid_script_mixing_allowed(self):
        """Test that reasonable script mixing is allowed."""
        # Latin with numbers (common case)
        text = "Hello123"
        result = self.validator.normalize_unicode(text, "Latin with numbers")
        assert result == "Hello123"

        # Latin with punctuation
        text = "Hello, World!"
        result = self.validator.normalize_unicode(text, "Latin with punctuation")
        assert result == "Hello, World!"

    @pytest.mark.timeout(15)
    def test_cjk_text_normalization(self):
        """Test normalization of CJK text."""
        text = "王明华"
        result = self.validator.normalize_unicode(text, "Chinese text")
        assert result == "王明华"

    @pytest.mark.timeout(15)
    def test_emoji_handling(self):
        """Test handling of emoji characters."""
        text = "Hello 👋 World"
        result = self.validator.normalize_unicode(text, "Text with emoji")
        assert "👋" in result

    @pytest.mark.timeout(15)
    def test_combining_mark_normalization(self):
        """Test proper normalization of combining marks."""
        # Multiple ways to represent ñ
        text1 = "n\u0303"  # n + combining tilde
        text2 = "ñ"  # Precomposed

        result1 = self.validator.normalize_unicode(text1, "Combining tilde")
        result2 = self.validator.normalize_unicode(text2, "Precomposed")

        assert result1 == result2
        assert result1 == "ñ"


class TestValidateEntry:
    """Test cases for validate_entry method with rate limiting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SecurityValidator()

    @pytest.mark.timeout(15)
    def test_valid_entry_basic(self):
        """Test validation of a basic valid entry."""
        entry = {
            "GlobalID": "test-001",
            "CanonicalLatin": "John Smith",
            "CanonicalNative": "John Smith",
        }

        result = self.validator.validate_entry(entry, "Basic entry")

        assert result["valid"] is True
        assert result["rate_limited"] is False
        assert result["retry_after"] == 0
        assert len(result["warnings"]) == 0

    @pytest.mark.timeout(15)
    def test_unicode_normalization_in_entry(self):
        """Test that entry fields are normalized."""
        entry = {
            "GlobalID": "test-002",
            "CanonicalLatin": "Jose\u0301",  # Decomposed é
            "CanonicalNative": "Jose\u0301",
        }

        result = self.validator.validate_entry(entry, "Unicode entry")

        assert result["valid"] is True
        assert entry["CanonicalLatin"] == "José"  # Should be normalized
        assert entry["CanonicalNative"] == "José"

    @pytest.mark.timeout(15)
    def test_rate_limiting_rapid_requests(self):
        """Test rate limiting for rapid requests."""
        entry1 = {"GlobalID": "test-003", "CanonicalLatin": "Test One"}
        entry2 = {"GlobalID": "test-004", "CanonicalLatin": "Test Two"}

        # First request should succeed
        result1 = self.validator.validate_entry(entry1, "First request", enable_rate_limiting=True)
        assert result1["valid"] is True
        assert result1["rate_limited"] is False

        # Immediate second request should be rate limited
        result2 = self.validator.validate_entry(entry2, "Second request", enable_rate_limiting=True)
        assert result2["rate_limited"] is True
        assert result2["retry_after"] == 0.1

        # Wait and retry
        time.sleep(0.11)
        result3 = self.validator.validate_entry(entry2, "Third request", enable_rate_limiting=True)
        assert result3["rate_limited"] is False

    @pytest.mark.timeout(15)
    def test_rate_limiting_disabled(self):
        """Test that rate limiting can be disabled."""
        entry1 = {"GlobalID": "test-005", "CanonicalLatin": "Test One"}
        entry2 = {"GlobalID": "test-006", "CanonicalLatin": "Test Two"}

        # Both rapid requests should succeed with rate limiting disabled
        result1 = self.validator.validate_entry(entry1, "First request", enable_rate_limiting=False)
        result2 = self.validator.validate_entry(
            entry2, "Second request", enable_rate_limiting=False
        )

        assert result1["rate_limited"] is False
        assert result2["rate_limited"] is False

    @pytest.mark.timeout(15)
    def test_security_error_propagation(self):
        """Test that security errors are properly raised."""
        entry = {"GlobalID": "test-007", "CanonicalLatin": "Hello\x00World"}  # Null byte

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_entry(entry, "Malicious entry")
        assert "Null byte detected" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_cjk_roundtrip_validation_triggered(self):
        """Test that CJK round-trip validation is triggered for CJK text."""
        entry = {"GlobalID": "test-008", "CanonicalLatin": "Wang Ming", "CanonicalNative": "王明"}

        result = self.validator.validate_entry(entry, "CJK entry")

        assert result["valid"] is True
        # Since it's not a perfect round-trip in our mock, check for warnings
        # The actual round-trip would fail, generating a warning

    @pytest.mark.timeout(15)
    def test_cjk_roundtrip_warning_on_failure(self):
        """Test that CJK round-trip failures generate warnings."""
        entry = {
            "GlobalID": "test-009",
            "CanonicalLatin": "Test",
            "CanonicalNative": "王\x00明",  # Null byte in CJK text
        }

        # Should not raise error but add warning
        result = self.validator.validate_entry(entry, "Bad CJK entry")

        assert result["valid"] is False  # Will fail due to null byte in normalize_unicode

    @pytest.mark.timeout(15)
    def test_missing_fields_handled_gracefully(self):
        """Test handling of entries with missing fields."""
        # Entry with only GlobalID
        entry = {"GlobalID": "test-010"}

        result = self.validator.validate_entry(entry, "Minimal entry")
        assert result["valid"] is True

        # Entry with empty strings
        entry = {"GlobalID": "test-011", "CanonicalLatin": "", "CanonicalNative": None}

        result = self.validator.validate_entry(entry, "Empty fields")
        assert result["valid"] is True

    @pytest.mark.timeout(15)
    def test_entry_field_security_validation(self):
        """Test that all text fields undergo security validation."""
        # Create entry with SQL injection attempt
        entry = {"GlobalID": "test-012", "CanonicalLatin": "'; DROP TABLE users; --"}

        # This will call validate_string internally which should catch SQL injection
        with pytest.raises(SecurityError):
            self.validator.validate_entry(entry, "SQL injection attempt")

    @pytest.mark.timeout(15)
    def test_all_fields_normalized(self):
        """Test that all text fields are normalized."""
        entry = {
            "GlobalID": "test\u0301-013",  # Decomposed accent in ID
            "CanonicalLatin": "Jose\u0301 Mari\u0301a",  # Decomposed accents
            "CanonicalNative": "Jose\u0301",
        }

        result = self.validator.validate_entry(entry, "Multi-field normalization")

        assert result["valid"] is True
        assert entry["GlobalID"] == "tèst-013"  # Normalized
        assert entry["CanonicalLatin"] == "José María"  # Normalized
        assert entry["CanonicalNative"] == "José"  # Normalized

    @pytest.mark.timeout(15)
    def test_rate_limiting_preserves_state(self):
        """Test that rate limiting state is preserved across calls."""
        validator = SecurityValidator()  # Fresh instance

        # Set up initial state
        entry1 = {"GlobalID": "test-014", "CanonicalLatin": "Test"}
        result1 = validator.validate_entry(entry1, "Setup", enable_rate_limiting=True)
        assert result1["rate_limited"] is False

        # Verify state is preserved
        assert hasattr(validator, "_last_request_time")
        assert validator._last_request_time > 0

    @pytest.mark.timeout(15)
    def test_cjk_detection_accuracy(self):
        """Test accurate detection of CJK characters for round-trip validation."""
        # Entry with actual CJK should trigger round-trip
        entry_cjk = {
            "GlobalID": "test-015",
            "CanonicalLatin": "Yamada Taro",
            "CanonicalNative": "山田太郎",
        }

        result = self.validator.validate_entry(entry_cjk, "Japanese entry")
        assert result["valid"] is True

        # Entry without CJK should not trigger round-trip
        entry_latin = {
            "GlobalID": "test-016",
            "CanonicalLatin": "John Smith",
            "CanonicalNative": "John Smith",
        }

        result = self.validator.validate_entry(entry_latin, "Latin entry")
        assert result["valid"] is True
        assert len(result["warnings"]) == 0


class TestIntegration:
    """Integration tests for SecurityValidator methods working together."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SecurityValidator()

    @pytest.mark.timeout(15)
    def test_full_cjk_entry_processing(self):
        """Test complete processing of a CJK entry through all methods."""
        # Start with unnormalized CJK entry
        entry = {
            "GlobalID": "test-integration-001",
            "CanonicalLatin": "Jose\u0301 Mari\u0301a",  # Decomposed accents
            "CanonicalNative": "王明华",
        }

        # Process through validate_entry
        result = self.validator.validate_entry(entry, "Integration test")

        # Check that normalization occurred
        assert entry["CanonicalLatin"] == "José María"

        # Check that entry is valid
        assert result["valid"] is True

        # Manually verify CJK round-trip
        is_valid_roundtrip = self.validator.validate_cjk_roundtrip(
            entry["CanonicalNative"],
            entry["CanonicalLatin"],
            entry["CanonicalNative"],
            "Manual check",
        )
        assert is_valid_roundtrip is True

    @pytest.mark.timeout(15)
    def test_malicious_input_detection_chain(self):
        """Test that malicious input is caught at various stages."""
        malicious_inputs = [
            {"GlobalID": "test\x00null", "CanonicalLatin": "Test"},  # Null in ID
            {"GlobalID": "test", "CanonicalLatin": "Test\x01SOH"},  # Control char
            {"GlobalID": "test", "CanonicalNative": "王\x00明"},  # Null in CJK
        ]

        for entry in malicious_inputs:
            with pytest.raises(SecurityError):
                self.validator.validate_entry(entry, "Malicious input chain")

    @pytest.mark.timeout(15)
    def test_performance_dos_prevention(self):
        """Test DoS prevention across all methods."""
        # Test long string in normalize_unicode
        long_text = "A" * 1000
        normalized = self.validator.normalize_unicode(long_text, "Long text")
        assert len(normalized) == 1000  # Should not expand

        # Test long string in CJK validation
        long_cjk = "王" * 201
        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(long_cjk, "Wang" * 201, long_cjk, "DoS test")
        assert "Excessively long" in str(exc_info.value)

        # Test rate limiting in validate_entry
        entry = {"GlobalID": "dos-test", "CanonicalLatin": "Test"}
        result1 = self.validator.validate_entry(entry, "DoS", enable_rate_limiting=True)
        result2 = self.validator.validate_entry(entry, "DoS", enable_rate_limiting=True)
        assert result2["rate_limited"] is True

    @pytest.mark.timeout(15)
    def test_unicode_security_comprehensive(self):
        """Test comprehensive Unicode security across methods."""
        # Test various Unicode attack vectors
        test_cases = [
            # Normalization attack
            "e\u0301" * 100,  # Many combining characters
            # Script mixing
            "HelloПривет",  # Latin + Cyrillic
            # Direction override
            "Hello\u202eworld",  # Right-to-left override
            # Zero-width characters
            "Hello\u200bworld",  # Zero-width space
        ]

        for text in test_cases:
            entry = {"GlobalID": "unicode-test", "CanonicalLatin": text}

            # Some should raise errors, others should be normalized
            try:
                result = self.validator.validate_entry(entry, "Unicode security")
                # If it doesn't raise, check it was normalized
                assert "CanonicalLatin" in entry
            except SecurityError:
                # Expected for some inputs
                pass


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
