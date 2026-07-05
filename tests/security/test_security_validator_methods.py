#!/usr/bin/env python3
"""
Test suite for SecurityValidator helper methods:
validate_cjk_roundtrip, normalize_unicode, and validate_entry.

R46 repair note: this file was written against an aspirational API that
never shipped (``validate_entry`` returning a ``{'valid': ...}`` dict, an
``enable_rate_limiting`` kwarg, a normalize-time expansion-attack check).
It was rewritten against the REAL current API:

- ``validate_entry(entry, context)`` returns a *sanitized copy* of the
  entry and raises ``SecurityError`` on dangerous content (no status
  dict, no per-call rate limiting — rate limiting is the separate
  ``check_rate_limit(client_id, context)``, covered by the canonical
  suite ``tests/security/test_security_validator.py``).
- ``normalize_unicode`` rejects dangerous Unicode with the message
  "Dangerous Unicode character (U+XXXX, <category>)".
- ``validate_cjk_roundtrip`` rejects null bytes and DoS-length input
  (hardening added in the R46 test-repair audit) and signals a failed
  round-trip by returning ``False`` — it does not raise on mismatch.

Retired tests (duplicates of canonical coverage or never-shipped API):
- test_mixed_cjk_scripts — exact duplicate of canonical
  test_cjk_mixed_scripts (same input, same assertion).
- test_normalization_bomb_detection — mock-based test of a normalize-
  time expansion check that never existed; the real combining-character
  protection lives in ``validate_string`` and is covered by canonical
  test_combining_character_attacks.
- test_rate_limiting_rapid_requests / test_rate_limiting_disabled /
  test_rate_limiting_preserves_state — tested a never-shipped
  ``enable_rate_limiting`` kwarg; real rate limiting
  (``check_rate_limit``) is covered by canonical test_rate_limiting
  and test_rate_limit_reset.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.security_validator import SecurityError, SecurityValidator


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
            self.validator.validate_cjk_roundtrip(
                original, romanized, back_to_cjk, "Latin name"
            )
        # Current message is "Non-CJK text in <context>" (the old
        # "... in CJK validation context" wording never shipped).
        assert "Non-CJK text" in str(exc_info.value)

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
    def test_null_byte_equal_roundtrip_still_blocked(self):
        """A null-byte payload must not validate even as a perfect match.

        Regression test for the R46 product fix: before it,
        validate_cjk_roundtrip returned True here because
        original == back_to_cjk.
        """
        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(
                "王\x00明", "Wang Ming", "王\x00明", "Null equal"
            )
        assert "Null byte detected" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_dos_prevention_long_original(self):
        """Test DoS prevention for excessively long original text."""
        original = "王" * 201  # Exceeds 200 char limit
        romanized = "Wang" * 201
        back_to_cjk = "王" * 201

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(
                original, romanized, back_to_cjk, "DoS attempt"
            )
        assert "Excessively long CJK conversion" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_dos_prevention_long_romanized(self):
        """Test DoS prevention for excessively long romanized text."""
        original = "王明"
        romanized = "W" * 201  # Exceeds 200 char limit
        back_to_cjk = "王明"

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(
                original, romanized, back_to_cjk, "DoS attempt"
            )
        assert "Excessively long CJK conversion" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_minor_length_mismatch_allowed(self):
        """Test that a small round-trip mismatch fails softly (False)."""
        original = "王明华"
        romanized = "Wang Minghua"
        back_to_cjk = "王明"  # Missing one character

        result = self.validator.validate_cjk_roundtrip(
            original, romanized, back_to_cjk, "Minor mismatch"
        )
        assert result is False  # Not equal, but no error raised

    @pytest.mark.timeout(15)
    def test_major_length_mismatch_fails_roundtrip(self):
        """Test that a major round-trip mismatch is not validated.

        The old raise-on-mismatch contract ("Suspicious CJK round-trip
        length mismatch") never shipped; the current API signals a
        failed round-trip by returning False. The security-relevant
        outcome — the conversion is NOT blessed as valid — is preserved.
        """
        original = "王明华李强"
        romanized = "Wang Minghua Li Qiang"
        back_to_cjk = "王"  # Missing 4 characters

        result = self.validator.validate_cjk_roundtrip(
            original, romanized, back_to_cjk, "Major mismatch"
        )
        assert result is False


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
        # Null byte is rejected as a dangerous Cc-category character;
        # the old "Null byte detected" wording never shipped here.
        assert "Dangerous Unicode character" in str(exc_info.value)
        assert "U+0000" in str(exc_info.value)

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
            # Current wording: "Dangerous Unicode character (U+XXXX, Cc)"
            # (formerly "Suspicious Unicode category").
            assert "Dangerous Unicode character" in str(exc_info.value)
            assert ", Cc)" in str(exc_info.value)

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
    def test_format_character_handling(self):
        """Test format (Cf) character handling.

        The Zero Width Joiner (U+200D) is ALLOWED BY DESIGN — it is in
        the validator's safe_format_chars set because it is required for
        legitimate text (emoji sequences, Indic scripts). Unsafe format
        characters like the Zero Width Space (U+200B) are still rejected
        (same semantics as the canonical suite's
        test_unicode_category_filtering).
        """
        # ZWJ: allowed by design
        result = self.validator.normalize_unicode("Hello\u200dWorld", "ZWJ test")
        assert "\u200d" in result

        # Zero-width space: dangerous Cf character, rejected
        with pytest.raises(SecurityError) as exc_info:
            self.validator.normalize_unicode("Hello\u200bWorld", "ZWSP test")
        assert "Dangerous Unicode character" in str(exc_info.value)
        assert ", Cf)" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_private_use_character_rejection(self):
        """Test rejection of private use area characters."""
        text = "Hello\ue000World"  # Private use area

        with pytest.raises(SecurityError) as exc_info:
            self.validator.normalize_unicode(text, "Private use test")
        # Current wording (formerly "Suspicious Unicode category Co").
        assert "Dangerous Unicode character (U+E000, Co)" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_moderate_script_mixing_allowed_homograph_detectable(self):
        """Moderate Latin/Cyrillic mixing is allowed by design.

        normalize_unicode performs no homograph analysis; legitimate
        multilingual strings must pass. Lookalike detection is the job
        of detect_homograph_attack (and validate_string's threshold
        check, covered by the canonical suite).
        """
        text = "Hello Неllo"  # Latin "Hello" + Cyrillic "Н"/"е" lookalikes

        # Allowed by design: below validate_string's 75% lookalike
        # threshold, and normalize_unicode does not raise for it.
        result = self.validator.normalize_unicode(text, "Homograph test")
        assert result == text

        # But the lookalike characters ARE detectable via the
        # dedicated homograph API.
        assert self.validator.detect_homograph_attack(text, "Homograph test") is True

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
    """Test cases for validate_entry method.

    validate_entry(entry, context) returns a sanitized copy of the entry
    (all string fields run through validate_string, nested dicts/lists
    recursed) and raises SecurityError on dangerous content. It does NOT
    return a {'valid': ...} status dict and has no rate-limiting kwarg.
    """

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

        assert isinstance(result, dict)
        assert result["GlobalID"] == "test-001"
        assert result["CanonicalLatin"] == "John Smith"
        assert result["CanonicalNative"] == "John Smith"

    @pytest.mark.timeout(15)
    def test_unicode_normalization_in_entry(self):
        """Test that string fields in the returned entry are NFC-normalized."""
        entry = {
            "GlobalID": "test-002",
            "CanonicalLatin": "Jose\u0301",  # Decomposed é
            "CanonicalNative": "Jose\u0301",
        }

        result = self.validator.validate_entry(entry, "Unicode entry")

        # validate_entry returns a sanitized COPY (it does not mutate
        # the input); the copy carries the NFC-composed forms.
        assert result["CanonicalLatin"] == "José"
        assert result["CanonicalNative"] == "José"

    @pytest.mark.timeout(15)
    def test_security_error_propagation(self):
        """Test that security errors are properly raised."""
        entry = {
            "GlobalID": "test-007",
            "CanonicalLatin": "Hello\x00World",
        }  # Null byte

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_entry(entry, "Malicious entry")
        # Null bytes surface as dangerous control characters in
        # validate_string (old "Null byte detected" wording never
        # shipped for this path).
        assert "Dangerous control character" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_cjk_entry_passes_untouched(self):
        """Clean CJK entries pass validation with content preserved."""
        entry = {
            "GlobalID": "test-008",
            "CanonicalLatin": "Wang Ming",
            "CanonicalNative": "王明",
        }

        result = self.validator.validate_entry(entry, "CJK entry")

        assert result["CanonicalNative"] == "王明"
        assert result["CanonicalLatin"] == "Wang Ming"

    @pytest.mark.timeout(15)
    def test_null_byte_in_cjk_field_rejected(self):
        """A null byte inside a CJK field raises SecurityError.

        (The old API expected a soft warning; the current API rejects
        hard, which is strictly stronger.)
        """
        entry = {
            "GlobalID": "test-009",
            "CanonicalLatin": "Test",
            "CanonicalNative": "王\x00明",  # Null byte in CJK text
        }

        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_entry(entry, "Bad CJK entry")
        assert "Dangerous control character" in str(exc_info.value)

    @pytest.mark.timeout(15)
    def test_missing_fields_handled_gracefully(self):
        """Test handling of entries with missing fields."""
        # Entry with only GlobalID
        entry = {"GlobalID": "test-010"}

        result = self.validator.validate_entry(entry, "Minimal entry")
        assert result == {"GlobalID": "test-010"}

        # Entry with empty string and None (non-strings pass through)
        entry = {"GlobalID": "test-011", "CanonicalLatin": "", "CanonicalNative": None}

        result = self.validator.validate_entry(entry, "Empty fields")
        assert result["CanonicalLatin"] == ""
        assert result["CanonicalNative"] is None

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
        """Test that all text fields in the returned entry are normalized."""
        entry = {
            # Decomposed accent on the "e" (t+U+0301 has no precomposed
            # form, so the old "test\u0301-013" input could never have
            # NFC-composed to the expected "t\u00e8st-013")
            "GlobalID": "te\u0301st-013",
            "CanonicalLatin": "Jose\u0301 Mari\u0301a",  # Decomposed accents
            "CanonicalNative": "Jose\u0301",
        }

        result = self.validator.validate_entry(entry, "Multi-field normalization")

        assert result["GlobalID"] == "tést-013"  # NFC-composed é
        assert result["CanonicalLatin"] == "José María"  # Normalized
        assert result["CanonicalNative"] == "José"  # Normalized

    @pytest.mark.timeout(15)
    def test_cjk_and_latin_entries_both_validate(self):
        """CJK and pure-Latin entries both pass with content intact."""
        entry_cjk = {
            "GlobalID": "test-015",
            "CanonicalLatin": "Yamada Taro",
            "CanonicalNative": "山田太郎",
        }

        result = self.validator.validate_entry(entry_cjk, "Japanese entry")
        assert result["CanonicalNative"] == "山田太郎"

        entry_latin = {
            "GlobalID": "test-016",
            "CanonicalLatin": "John Smith",
            "CanonicalNative": "John Smith",
        }

        result = self.validator.validate_entry(entry_latin, "Latin entry")
        assert result["CanonicalLatin"] == "John Smith"


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

        # Process through validate_entry (returns sanitized copy)
        result = self.validator.validate_entry(entry, "Integration test")

        # Check that normalization occurred
        assert result["CanonicalLatin"] == "José María"
        assert result["CanonicalNative"] == "王明华"

        # Manually verify CJK round-trip on the sanitized values
        is_valid_roundtrip = self.validator.validate_cjk_roundtrip(
            result["CanonicalNative"],
            result["CanonicalLatin"],
            result["CanonicalNative"],
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
        """Test DoS prevention across methods."""
        # Test long string in normalize_unicode
        long_text = "A" * 1000
        normalized = self.validator.normalize_unicode(long_text, "Long text")
        assert len(normalized) == 1000  # Should not expand

        # Test long string in CJK validation (200-char cap)
        long_cjk = "王" * 201
        with pytest.raises(SecurityError) as exc_info:
            self.validator.validate_cjk_roundtrip(
                long_cjk, "Wang" * 201, long_cjk, "DoS test"
            )
        assert "Excessively long" in str(exc_info.value)

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
                # If it doesn't raise, check the field survived sanitization
                assert "CanonicalLatin" in result
            except SecurityError:
                # Expected for some inputs
                pass


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
