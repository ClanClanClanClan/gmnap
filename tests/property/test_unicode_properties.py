"""
Property-based testing for Unicode normalization.
Uses Hypothesis to generate exhaustive test cases.
"""

import re
import unicodedata

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import characters, composite, integers, lists, text

from src.core.unicode_handler import (
    UnicodeHandlerConfig as UnicodeConfig,
    UnicodeNormalizer,
    normalize_name,
)


# Custom strategies for name generation
@composite
def name_strategy(draw):
    """Generate realistic name-like strings."""
    family_name = draw(
        text(
            alphabet=characters(
                min_codepoint=0x0020,
                max_codepoint=0x017F,  # Basic Latin + Latin-1
                categories=["Lu", "Ll", "Pd", "Po"],
            ),
            min_size=1,
            max_size=30,
        )
    )

    given_name = draw(
        text(
            alphabet=characters(
                min_codepoint=0x0020,
                max_codepoint=0x017F,
                categories=["Lu", "Ll", "Pd", "Po"],
            ),
            min_size=1,
            max_size=30,
        )
    )

    # Filter out problematic characters
    assume(family_name.strip() and given_name.strip())
    assume(not any(c in family_name for c in ["\x00", "\x01", "\x02", "\x03"]))
    assume(not any(c in given_name for c in ["\x00", "\x01", "\x02", "\x03"]))

    return f"{family_name.strip()}, {given_name.strip()}"


@composite
def unicode_text_strategy(draw):
    """Generate Unicode text from multiple scripts."""
    script_ranges = {
        "Latin": (0x0000, 0x024F),
        "Greek": (0x0370, 0x03FF),
        "Cyrillic": (0x0400, 0x04FF),
        "Arabic": (0x0600, 0x06FF),
        "Hebrew": (0x0590, 0x05FF),
        "Devanagari": (0x0900, 0x097F),
        "Bengali": (0x0980, 0x09FF),
        "Tamil": (0x0B80, 0x0BFF),
        "Thai": (0x0E00, 0x0E7F),
        "Khmer": (0x1780, 0x17FF),
        "CJK": (0x4E00, 0x9FFF),
        "Hangul": (0xAC00, 0xD7AF),
    }

    # Choose a random script
    script = draw(st.sampled_from(list(script_ranges.keys())))
    min_cp, max_cp = script_ranges[script]

    return draw(
        text(
            alphabet=characters(min_codepoint=min_cp, max_codepoint=max_cp),
            min_size=1,
            max_size=50,
        )
    )


@composite
def combining_text_strategy(draw):
    """Generate text with combining characters."""
    base_char = draw(characters(min_codepoint=0x0041, max_codepoint=0x005A))  # A-Z
    combining_chars = draw(
        lists(
            characters(categories=["Mn", "Mc"]), min_size=0, max_size=5
        )  # Combining marks
    )

    return base_char + "".join(combining_chars)


@composite
def problematic_unicode_strategy(draw):
    """Generate potentially problematic Unicode strings."""
    strategies = [
        # Null and control characters
        text(alphabet=characters(min_codepoint=0x0000, max_codepoint=0x001F)),
        # Surrogates (will be filtered)
        text(alphabet=characters(min_codepoint=0x10000, max_codepoint=0x10FFFF)),
        # Private use area
        text(alphabet=characters(min_codepoint=0xE000, max_codepoint=0xF8FF)),
        # Specials
        text(alphabet=characters(min_codepoint=0xFFF0, max_codepoint=0xFFFF)),
        # Bidirectional text — mix LTR Latin + RTL Hebrew/Arabic so
        # the normalizer's BIDI handling gets exercised. The earlier
        # `categories=["L", "R", "AL"]` used the BIDI class names; in
        # hypothesis those have to be Unicode *general* categories,
        # so the strategy failed to construct. Sample from explicit
        # codepoint ranges instead: ASCII letters (LTR) + Hebrew
        # (U+0590-05FF, RTL) + Arabic (U+0600-06FF, RTL).
        st.one_of(
            text(alphabet=characters(min_codepoint=0x0041, max_codepoint=0x007A)),
            text(alphabet=characters(min_codepoint=0x0590, max_codepoint=0x05FF)),
            text(alphabet=characters(min_codepoint=0x0600, max_codepoint=0x06FF)),
        ),
        # Zero-width characters
        st.just("\u200b\u200c\u200d\u2060\ufeff"),
        # Normalization test cases
        combining_text_strategy(),
    ]

    return draw(st.one_of(strategies))


class TestUnicodeNormalizationProperties:
    """Property-based tests for Unicode normalization."""

    @given(text_input=text(min_size=0, max_size=1000))
    @settings(max_examples=200, deadline=None)
    def test_normalization_idempotency(self, text_input):
        """Test that normalization is idempotent."""
        assume(text_input is not None)

        normalizer = UnicodeNormalizer()

        # First normalization
        normalized1 = normalizer.normalize(text_input)

        # Second normalization should be identical
        normalized2 = normalizer.normalize(normalized1)

        assert (
            normalized1 == normalized2
        ), f"Normalization not idempotent: {repr(text_input)}"

    @given(text_input=text(min_size=1, max_size=100))
    @settings(max_examples=200, deadline=None)
    def test_normalization_preserves_alphanumeric(self, text_input):
        """Normalization may ADD ASCII alphanumerics (e.g. NFKD turns
        the superscript ¹ U+00B9 into a plain digit 1) but it must
        never DROP an ASCII alphanumeric that was already there.

        The earlier assertion required exact-equal sequences, which
        rejected the legitimate "¹ → 1" case (input had 0 ASCII
        digits, output had 1). The correct property is a containment
        check: ``original_alnum`` is a subsequence of
        ``normalized_alnum`` (preserving order, allowing inserts).
        """
        assume(text_input.strip())

        normalizer = UnicodeNormalizer()
        normalized = normalizer.normalize(text_input)

        original_alnum = re.findall(r"[a-zA-Z0-9]", text_input)
        normalized_alnum = re.findall(r"[a-zA-Z0-9]", normalized)

        # Subsequence check — preserves order, allows insertions
        # (which is what NFKD lossiness produces, never the reverse).
        i = 0
        for c in normalized_alnum:
            if i < len(original_alnum) and c == original_alnum[i]:
                i += 1
        assert i == len(original_alnum), (
            f"Alphanumeric NOT preserved as subsequence: "
            f"input={repr(text_input)} → orig_alnum={original_alnum} "
            f"vs norm_alnum={normalized_alnum}"
        )

    @given(text_input=unicode_text_strategy())
    @settings(max_examples=100, deadline=None)
    def test_script_detection_consistency(self, text_input):
        """Test that script detection is consistent."""
        assume(text_input.strip())

        normalizer = UnicodeNormalizer()

        # Multiple calls should return same script
        script1 = normalizer.detect_primary_script(text_input)
        script2 = normalizer.detect_primary_script(text_input)

        assert script1 == script2, f"Script detection inconsistent: {repr(text_input)}"

        # Script should be a valid script name
        valid_scripts = {
            "Latin",
            "Cyrillic",
            "Greek",
            "Arabic",
            "Hebrew",
            "Devanagari",
            "Bengali",
            "Tamil",
            "Thai",
            "Khmer",
            "CJK",
            "Hangul",
            "Kana",
            "Armenian",
            "Georgian",
            "Other",
            "Unknown",
        }
        assert script1 in valid_scripts, f"Invalid script detected: {script1}"

    @given(text_input=combining_text_strategy())
    @settings(max_examples=100, deadline=None)
    def test_combining_character_handling(self, text_input):
        """Test proper handling of combining characters."""
        normalizer = UnicodeNormalizer()
        normalized = normalizer.normalize(text_input)

        # Normalized text should be in NFC form
        assert unicodedata.normalize("NFC", normalized) == normalized

        # Length might change due to combining, but should be reasonable
        assert len(normalized) <= len(text_input) * 2  # Generous bound

    @given(text_input=problematic_unicode_strategy())
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.filter_too_much],
    )
    def test_problematic_unicode_robustness(self, text_input):
        """Test robustness against problematic Unicode."""
        assume(text_input is not None)

        normalizer = UnicodeNormalizer()

        # Should not crash on any Unicode input
        try:
            normalized = normalizer.normalize(text_input)
            assert isinstance(normalized, str)
        except Exception as e:
            pytest.fail(f"Normalization crashed on {repr(text_input)}: {e}")

    @given(text_input=text(min_size=1, max_size=100))
    @settings(max_examples=150, deadline=None)
    def test_variant_generation_properties(self, text_input):
        """Test properties of variant generation."""
        assume(text_input.strip())

        normalizer = UnicodeNormalizer()
        variants = normalizer.generate_variants(text_input)

        # Should always include original
        assert text_input in variants, f"Original not in variants: {repr(text_input)}"

        # Should not contain duplicates
        assert len(variants) == len(set(variants)), f"Duplicate variants: {variants}"

        # All variants should be strings
        assert all(
            isinstance(v, str) for v in variants
        ), f"Non-string variants: {variants}"

        # Should be reasonable number of variants
        assert len(variants) <= 10, f"Too many variants: {len(variants)}"

    @given(name=name_strategy())
    @settings(max_examples=100, deadline=None)
    def test_name_normalization_properties(self, name):
        """Test properties specific to name normalization."""
        normalized = normalize_name(name)

        # Should preserve comma structure for names
        if ", " in name:
            assert ", " in normalized, f"Comma structure lost: {name} -> {normalized}"

        # Should not introduce new commas
        assert normalized.count(", ") == name.count(
            ", "
        ), f"Comma count changed: {name} -> {normalized}"

        # Should preserve word boundaries
        name_words = name.split()
        normalized_words = normalized.split()
        assert len(name_words) == len(
            normalized_words
        ), f"Word count changed: {name} -> {normalized}"

    @given(text_input=text(min_size=0, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_validation_properties(self, text_input):
        """Test normalization validation properties."""
        normalizer = UnicodeNormalizer()
        normalized = normalizer.normalize(text_input)

        # Validation should be consistent
        valid1 = normalizer.validate_normalization(text_input, normalized)
        valid2 = normalizer.validate_normalization(text_input, normalized)

        assert valid1 == valid2, f"Validation inconsistent: {repr(text_input)}"

    @given(text_list=lists(text(min_size=1, max_size=50), min_size=1, max_size=20))
    @settings(max_examples=50, deadline=None)
    def test_batch_normalization_consistency(self, text_list):
        """Test that batch normalization is consistent with individual normalization."""
        normalizer = UnicodeNormalizer()

        # Individual normalization
        individual_results = [normalizer.normalize(text) for text in text_list]

        # Batch normalization (simulated)
        batch_results = []
        for text in text_list:
            batch_results.append(normalizer.normalize(text))

        assert individual_results == batch_results, "Batch normalization inconsistent"

    @given(text_input=text(min_size=1, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_config_consistency(self, text_input):
        """Test that configuration options work consistently."""
        assume(text_input.strip())

        # Test with different configurations
        config1 = UnicodeConfig(handle_ligatures=True, handle_sharp_s=True)
        config2 = UnicodeConfig(handle_ligatures=False, handle_sharp_s=False)

        normalizer1 = UnicodeNormalizer(config1)
        normalizer2 = UnicodeNormalizer(config2)

        result1 = normalizer1.normalize(text_input)
        result2 = normalizer2.normalize(text_input)

        # Results should be strings
        assert isinstance(result1, str) and isinstance(result2, str)

        # If text contains ligatures, results might differ
        if any(char in text_input for char in "æœßẞ"):
            # With ligatures enabled, might be different
            pass  # This is expected
        else:
            # Without ligatures, should be similar
            pass  # Results might still differ due to other processing

    @given(iterations=integers(min_value=1, max_value=10))
    @settings(max_examples=20, deadline=None)
    def test_repeated_normalization_stability(self, iterations):
        """Test that repeated normalization is stable."""
        test_text = "García, José María"
        normalizer = UnicodeNormalizer()

        result = test_text
        for _ in range(iterations):
            result = normalizer.normalize(result)

        # Should converge to stable result
        final_result = normalizer.normalize(result)
        assert (
            result == final_result
        ), f"Normalization not stable after {iterations} iterations"

    @given(text_input=text(min_size=1, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_memory_usage_properties(self, text_input):
        """Test that normalization doesn't cause memory leaks."""
        import gc

        normalizer = UnicodeNormalizer()

        # Get initial object count
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Run normalization multiple times
        for _ in range(10):
            normalized = normalizer.normalize(text_input)
            del normalized

        # Check for memory leaks
        gc.collect()
        final_objects = len(gc.get_objects())

        # Should not create excessive objects
        assert final_objects - initial_objects < 100, "Potential memory leak detected"

    @given(text_input=text(min_size=1, max_size=1000))
    @settings(max_examples=50, deadline=None)
    def test_large_text_handling(self, text_input):
        """Test handling of large text inputs."""
        normalizer = UnicodeNormalizer()

        # Should handle large inputs without crashing
        normalized = normalizer.normalize(text_input)

        # Result should be reasonable size
        assert len(normalized) <= len(text_input) * 3  # Generous bound

        # Should still be a string
        assert isinstance(normalized, str)

    @given(
        text_input=text(alphabet=characters(categories=["Cc"]), min_size=1, max_size=20)
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.filter_too_much],
    )
    def test_control_character_handling(self, text_input):
        """Test handling of control characters."""
        assume(text_input)

        normalizer = UnicodeNormalizer()

        # Should not crash on control characters
        try:
            normalized = normalizer.normalize(text_input)
            assert isinstance(normalized, str)
        except Exception as e:
            pytest.fail(f"Failed on control characters {repr(text_input)}: {e}")


@pytest.mark.property
@pytest.mark.slow
class TestUnicodeNormalizationRegression:
    """Regression tests for specific Unicode normalization issues."""

    def test_specific_ligature_cases(self):
        """Test specific ligature cases that might cause issues."""
        normalizer = UnicodeNormalizer()

        test_cases = [
            ("Cæsar", "Caesar"),
            ("Œuvre", "Oeuvre"),
            ("Weiß", "Weiss"),
            ("WEIẞ", "WEISS"),
            ("ﬁnite", "finite"),
            ("ﬂower", "flower"),
            ("ﬀect", "ffect"),
            # U+FB03 is LATIN SMALL LIGATURE FFI — NFKD decomposes
            # to f,f,i (three characters). Earlier expectation "fifth"
            # was a typo — the correct NFKD-normalized form of ﬃfth
            # is ffifth (6 chars: f,f,i,f,t,h).
            ("ﬃfth", "ffifth"),
            ("ﬄe", "ffle"),
            ("ﬆyle", "style"),
        ]

        for input_text, expected in test_cases:
            result = normalizer.normalize(input_text)
            assert (
                result == expected
            ), f"Ligature test failed: {input_text} -> {result}, expected {expected}"

    def test_specific_greek_cases(self):
        """Test specific Greek tonos/oxia cases."""
        normalizer = UnicodeNormalizer()

        # Test Greek characters with tonos
        test_cases = ["Παπαδόπουλος", "Γιάννης", "Μαρία", "Αθήνα", "Θεσσαλονίκη"]

        for text in test_cases:
            normalized = normalizer.normalize(text)
            # Should not crash and should be valid Greek
            assert isinstance(normalized, str)
            assert len(normalized) > 0

    def test_specific_arabic_cases(self):
        """Test specific Arabic cases."""
        normalizer = UnicodeNormalizer()

        test_cases = [
            "الخوارزمي",
            "محمد بن موسى",
            "أبو عبدالله",
            "ابن سينا",
            "الفارابي",
        ]

        for text in test_cases:
            normalized = normalizer.normalize(text)
            assert isinstance(normalized, str)
            assert len(normalized) > 0

    def test_bidi_text_handling(self):
        """Test bidirectional text handling."""
        normalizer = UnicodeNormalizer()

        # Mixed LTR and RTL text
        test_cases = [
            "Hello مرحبا World",
            "Smith الخوارزمي John",
            "123 العربية 456",
        ]

        for text in test_cases:
            normalized = normalizer.normalize(text)
            assert isinstance(normalized, str)
            # Should preserve basic structure
            assert len(normalized) >= len(text) * 0.5  # Allow some compression
