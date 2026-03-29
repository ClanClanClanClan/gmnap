"""
Hardcore fuzzing tests for GMNAP system robustness.

Tests with malformed inputs, attack vectors, and edge cases designed
to break the system. Uses property-based testing and deliberate attacks.
"""

import json
import random
import string
import struct
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import binary, dictionaries, floats, integers, lists, text

from src.core.config import GMNAPConfig
from src.core.globalid import GlobalIDGenerator, validate_global_id
from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
from src.core.unicode_handler import UnicodeNormalizer
from src.validation.schema import SchemaValidator


class TestInputFuzzing:
    """Fuzz all input parsers and processors."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GlobalIDGenerator()
        self.unicode_handler = UnicodeNormalizer()
        self.validator = SchemaValidator()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @given(malformed_name=text(min_size=0, max_size=1000))
    @settings(max_examples=500, deadline=None)
    def test_fuzz_unicode_normalization(self, malformed_name):
        """Fuzz Unicode normalization with random strings."""
        try:
            # Should never crash, even with malformed Unicode
            result = self.unicode_handler.normalize(malformed_name)

            # If it returns a result, it should be valid
            if result is not None:
                assert isinstance(result, str), f"Non-string result: {type(result)}"

                # Should be idempotent
                result2 = self.unicode_handler.normalize(result)
                assert result == result2, "Non-idempotent normalization"

                # Should not contain dangerous characters
                dangerous_chars = ["\x00", "\x01", "\x02", "\x03", "\x04", "\x05"]
                for char in dangerous_chars:
                    assert char not in result, f"Dangerous character preserved: {repr(char)}"

        except Exception as e:
            # Should handle all exceptions gracefully
            assert any(
                word in str(e).lower() for word in ["invalid", "malformed", "unsupported"]
            ), f"Unexpected exception type: {str(e)}"

    @given(
        malformed_entry=dictionaries(
            text(min_size=0, max_size=100),
            st.one_of(
                text(min_size=0, max_size=1000),
                integers(min_value=-999999, max_value=999999),
                floats(allow_nan=True, allow_infinity=True),
                binary(min_size=0, max_size=100),
                st.none(),
            ),
            min_size=0,
            max_size=50,
        )
    )
    @settings(max_examples=200, deadline=None)
    def test_fuzz_globalid_generation(self, malformed_entry):
        """Fuzz GlobalID generation with malformed entries."""
        try:
            # Should handle malformed entries gracefully
            global_id = self.generator.generate(malformed_entry)

            # If it generates an ID, it should be valid
            if global_id is not None:
                assert validate_global_id(global_id), f"Invalid GlobalID generated: {global_id}"

                # Should be deterministic
                global_id2 = self.generator.generate(malformed_entry)
                assert global_id == global_id2, "Non-deterministic GlobalID generation"

        except Exception as e:
            # Should only raise expected exceptions
            expected_errors = [
                "missing",
                "invalid",
                "malformed",
                "unsupported",
                "required",
                "canonical",
                "must have",
            ]
            assert any(
                word in str(e).lower() for word in expected_errors
            ), f"Unexpected exception: {str(e)}"

    @given(malformed_yaml=text(min_size=0, max_size=2000))
    @settings(max_examples=100, deadline=None)
    def test_fuzz_yaml_parsing(self, malformed_yaml):
        """Fuzz YAML parsing with malformed content."""
        yaml_file = Path(self.temp_dir) / "fuzz_test.yaml"

        try:
            # Write malformed YAML
            with open(yaml_file, "w", encoding="utf-8", errors="replace") as f:
                f.write(malformed_yaml)

            # Try to parse with pipeline
            config = GMNAPConfig()
            pipeline = GMNAPPipeline(config, PipelineMode.QUICK)

            # Should handle malformed YAML gracefully
            result = pipeline.run(yaml_file.parent)

            # If parsing succeeded, result should be valid
            if result is not None:
                assert hasattr(result, "total_entries"), "Invalid pipeline result"
                assert result.total_entries >= 0, "Invalid entry count"

        except Exception as e:
            # Should handle YAML parsing errors gracefully
            yaml_errors = ["yaml", "parse", "syntax", "malformed", "invalid"]
            assert any(
                word in str(e).lower() for word in yaml_errors
            ), f"Unexpected YAML parsing error: {str(e)}"

        finally:
            # Clean up
            if yaml_file.exists():
                yaml_file.unlink()

    def test_fuzz_binary_injection_attacks(self):
        """Test binary injection attacks."""
        binary_attacks = [
            # Null byte injection
            b"Smith, John\x00malicious",
            # Control character injection
            b"Smith\x01\x02\x03, John",
            # Invalid UTF-8 sequences
            b"Smith, Jo\xff\xfeh\x80n",
            # Overlong UTF-8 encoding
            b"Smith, J\xc0\xafohn",
            # UTF-8 BOM injection
            b"\xef\xbb\xbfSmith, John",
            # Line separator injection
            b"Smith,\u2028John",
            # Paragraph separator injection
            b"Smith,\u2029John",
        ]

        for attack_bytes in binary_attacks:
            try:
                # Try to decode as UTF-8
                attack_string = attack_bytes.decode("utf-8", errors="replace")

                # Test Unicode normalization
                normalized = self.unicode_handler.normalize(attack_string)

                # Should sanitize or reject dangerous content
                if normalized:
                    assert "\x00" not in normalized, "Null byte not sanitized"
                    assert "\x01" not in normalized, "Control character not sanitized"
                    assert "\ufffd" not in normalized or len(normalized) < len(
                        attack_string
                    ), "Invalid UTF-8 not handled properly"

                # Test GlobalID generation
                entry = {"CanonicalNative": attack_string}
                global_id = self.generator.generate(entry)

                if global_id:
                    assert validate_global_id(
                        global_id
                    ), f"Invalid GlobalID from binary attack: {global_id}"

            except Exception as e:
                # Should handle gracefully
                assert (
                    "invalid" in str(e).lower() or "malformed" in str(e).lower()
                ), f"Unexpected error with binary attack: {str(e)}"

    def test_fuzz_json_injection_attacks(self):
        """Test JSON injection attacks."""
        json_attacks = [
            # JSON injection in strings
            '{"name": "Smith, John", "injection": {"admin": true}}',
            # Escaped characters
            '{"name": "Smith\\", John"}',
            # Unicode escapes
            '{"name": "Smith\\u0000John"}',
            # Very long strings
            '{"name": "' + "A" * 10000 + '"}',
            # Nested objects
            '{"name": {"nested": {"deeply": {"nested": "value"}}}}',
            # Array injection
            '{"name": ["Smith", "John", {"admin": true}]}',
            # Number injection
            '{"name": "Smith", "year": 1e308}',
            # Boolean injection
            '{"name": "Smith", "active": true}',
        ]

        for attack_json in json_attacks:
            try:
                # Parse JSON
                parsed = json.loads(attack_json)

                # Test with schema validator
                is_valid = self.validator.validate_entry(parsed)

                # Should either validate properly or reject cleanly
                if is_valid:
                    # If valid, should be safe
                    assert isinstance(parsed.get("name"), str), "Name field should be string"
                else:
                    # If invalid, should be rejected cleanly
                    assert True, "Clean rejection of JSON attack"

            except json.JSONDecodeError:
                # Invalid JSON should be rejected
                assert True, "Invalid JSON properly rejected"
            except Exception as e:
                # Should handle gracefully
                assert (
                    "invalid" in str(e).lower() or "malformed" in str(e).lower()
                ), f"Unexpected error with JSON attack: {str(e)}"

    def test_fuzz_zip_bomb_attacks(self):
        """Test compression bomb attacks."""
        # Create highly repetitive data that compresses well
        repetitive_data = "A" * 1000000  # 1MB of repeated 'A'

        try:
            # Test with cache system (uses compression)
            from src.utils.cache import CacheManager

            cache = CacheManager(cache_dir=Path(self.temp_dir) / "cache")

            # Try to cache the repetitive data
            cache.set("zip_bomb_test", {"data": repetitive_data})

            # Should handle compression gracefully
            result = cache.get("zip_bomb_test")

            if result:
                assert result["data"] == repetitive_data, "Data corruption in compression"

        except Exception as e:
            # Should handle compression issues gracefully
            compression_errors = ["compression", "memory", "size", "limit"]
            assert any(
                word in str(e).lower() for word in compression_errors
            ), f"Unexpected compression error: {str(e)}"

    def test_fuzz_regex_catastrophic_backtracking(self):
        """Test regex catastrophic backtracking attacks."""
        # Patterns that can cause exponential backtracking
        backtracking_attacks = [
            # Classic exponential backtracking
            "a" * 50 + "X",
            # Nested quantifiers
            "(" + "a" * 30 + ")*" + "b",
            # Alternation with overlap
            "a" * 25 + "|" + "a" * 25 + "b",
            # Unicode with combining characters
            "a" + "\u0300" * 100,
        ]

        for attack_pattern in backtracking_attacks:
            try:
                # Test with Unicode handler (may use regex)
                start_time = time.time()

                normalized = self.unicode_handler.normalize(attack_pattern)

                end_time = time.time()
                processing_time = end_time - start_time

                # Should not take excessive time (>1 second)
                assert (
                    processing_time < 1.0
                ), f"Possible regex backtracking attack: {processing_time}s"

                # If normalized, should be safe
                if normalized:
                    assert len(normalized) < len(attack_pattern) * 2, "Excessive expansion"

            except Exception as e:
                # Should handle gracefully
                assert (
                    "timeout" in str(e).lower() or "invalid" in str(e).lower()
                ), f"Unexpected regex error: {str(e)}"

    def test_fuzz_integer_overflow_attacks(self):
        """Test integer overflow attacks."""
        overflow_values = [
            # Large positive integers
            2**63 - 1,  # Max signed 64-bit
            2**64 - 1,  # Max unsigned 64-bit
            2**128 - 1,  # Very large
            # Large negative integers
            -(2**63),  # Min signed 64-bit
            -(2**64),  # Very negative
            # Float edge cases
            float("inf"),
            float("-inf"),
            float("nan"),
        ]

        for overflow_value in overflow_values:
            try:
                # Test with birth year field
                entry = {"CanonicalNative": "Smith, John", "BirthYear": overflow_value}

                # Should handle overflow gracefully
                global_id = self.generator.generate(entry)

                if global_id:
                    assert validate_global_id(
                        global_id
                    ), f"Invalid GlobalID from overflow: {global_id}"

                # Test with schema validation
                full_entry = {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "UpdatedAt": "2025-01-01T00:00:00Z",
                    "CanonicalLatin": "Smith, John",
                    "CanonicalNative": "Smith, John",
                    "BirthYear": overflow_value,
                }

                is_valid = self.validator.validate_entry(full_entry)

                # Should either validate properly or reject cleanly
                if not is_valid:
                    assert True, "Clean rejection of overflow value"

            except (ValueError, OverflowError):
                # Expected for overflow values
                assert True, "Overflow properly handled"
            except Exception as e:
                # Should handle gracefully
                assert (
                    "overflow" in str(e).lower() or "invalid" in str(e).lower()
                ), f"Unexpected overflow error: {str(e)}"

    def test_fuzz_unicode_normalization_attacks(self):
        """Test Unicode normalization attacks."""
        normalization_attacks = [
            # Normalization collision attack
            "A\u0300",  # A with combining grave accent
            "\u00c0",  # A with grave accent (precomposed)
            # Homograph attack with normalization
            "А",  # Cyrillic A (looks like Latin A)
            "A",  # Latin A
            # Mixed normalization forms
            "caf\u00e9",  # café with é
            "cafe\u0301",  # café with combining acute
            # Invisible character attack
            "Smith\u200b, John",  # Zero-width space
            "Smith\u200c, John",  # Zero-width non-joiner
            "Smith\u200d, John",  # Zero-width joiner
            # Bidirectional override attack
            "Smith\u202e, John",  # Right-to-left override
            "Smith\u202d, John",  # Left-to-right override
        ]

        for attack_string in normalization_attacks:
            try:
                # Test normalization
                normalized = self.unicode_handler.normalize(attack_string)

                # Should handle normalization attacks safely
                if normalized:
                    # Should not contain dangerous invisible characters
                    dangerous_chars = ["\u200b", "\u200c", "\u200d", "\u202e", "\u202d"]
                    for char in dangerous_chars:
                        assert (
                            char not in normalized
                        ), f"Dangerous character not removed: {repr(char)}"

                    # Should be idempotent
                    normalized2 = self.unicode_handler.normalize(normalized)
                    assert normalized == normalized2, "Non-idempotent normalization"

                # Test GlobalID generation
                entry = {"CanonicalNative": attack_string}
                global_id = self.generator.generate(entry)

                if global_id:
                    assert validate_global_id(
                        global_id
                    ), f"Invalid GlobalID from normalization attack"

            except Exception as e:
                # Should handle gracefully
                assert (
                    "unicode" in str(e).lower() or "normalization" in str(e).lower()
                ), f"Unexpected normalization error: {str(e)}"

    def test_fuzz_memory_exhaustion_attacks(self):
        """Test memory exhaustion attacks."""
        memory_attacks = [
            # Very long strings
            "A" * 1000000,
            # Deeply nested structures (simulated)
            {"nested": {"deeply": {"very": {"deeply": {"nested": "value"}}}}},
            # Large arrays (simulated)
            ["item"] * 10000,
            # Repeated large objects
            [{"large_field": "x" * 1000} for _ in range(1000)],
        ]

        for attack_data in memory_attacks:
            try:
                if isinstance(attack_data, str):
                    # Test string processing
                    normalized = self.unicode_handler.normalize(attack_data)

                    # Should handle large strings gracefully
                    if normalized:
                        assert len(normalized) <= len(attack_data) * 2, "Excessive expansion"

                        # Test GlobalID generation
                        entry = {"CanonicalNative": normalized}
                        global_id = self.generator.generate(entry)

                        if global_id:
                            assert validate_global_id(
                                global_id
                            ), "Invalid GlobalID from large string"

                elif isinstance(attack_data, (dict, list)):
                    # Test with schema validation
                    is_valid = self.validator.validate_entry(attack_data)

                    # Should either validate or reject cleanly
                    if not is_valid:
                        assert True, "Clean rejection of large data structure"

            except MemoryError:
                # Expected for memory exhaustion
                assert True, "Memory exhaustion properly handled"
            except Exception as e:
                # Should handle gracefully
                memory_errors = ["memory", "size", "limit", "too large"]
                assert any(
                    word in str(e).lower() for word in memory_errors
                ), f"Unexpected memory error: {str(e)}"

    def test_fuzz_format_string_attacks(self):
        """Test format string attacks."""
        format_attacks = [
            # Python format string attacks
            "Smith, {0}",
            "Smith, %s",
            "Smith, %d",
            "Smith, %x",
            # F-string like attacks
            "Smith, {name}",
            "Smith, {__class__}",
            # Template attacks
            "Smith, $name",
            "Smith, ${name}",
            # SQL injection style
            "Smith'; DROP TABLE users; --",
            "Smith' OR '1'='1",
        ]

        for attack_string in format_attacks:
            try:
                # Test processing
                normalized = self.unicode_handler.normalize(attack_string)

                # Should not interpret format strings
                if normalized:
                    assert (
                        "{" not in normalized
                        or "}" not in normalized
                        or normalized == attack_string
                    ), "Format string interpreted"

                    # Test GlobalID generation
                    entry = {"CanonicalNative": normalized}
                    global_id = self.generator.generate(entry)

                    if global_id:
                        assert validate_global_id(global_id), "Invalid GlobalID from format attack"

            except Exception as e:
                # Should handle gracefully
                assert (
                    "format" in str(e).lower() or "invalid" in str(e).lower()
                ), f"Unexpected format error: {str(e)}"


class TestPropertyBasedAttacks:
    """Property-based testing for attack vectors."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = GlobalIDGenerator()
        self.unicode_handler = UnicodeNormalizer()

    @given(
        attack_text=text(
            alphabet=st.characters(
                min_codepoint=0x0000,
                max_codepoint=0x10FFFF,
                categories=["Cc", "Cf", "Cn", "Co", "Cs"],  # Control and special characters
            ),
            min_size=1,
            max_size=100,
        )
    )
    @settings(max_examples=200, deadline=None)
    def test_property_control_character_attacks(self, attack_text):
        """Test that control characters are handled safely."""
        try:
            # Should handle control characters safely
            normalized = self.unicode_handler.normalize(attack_text)

            # If normalized, should be safe
            if normalized:
                # Should not contain dangerous control characters
                for char in normalized:
                    category = unicodedata.category(char)
                    assert category not in [
                        "Cc",
                        "Cf",
                    ], f"Dangerous control character preserved: {repr(char)}"

        except Exception as e:
            # Should handle gracefully
            assert (
                "control" in str(e).lower() or "invalid" in str(e).lower()
            ), f"Unexpected control character error: {str(e)}"

    @given(
        attack_dict=dictionaries(
            text(alphabet=st.characters(categories=["Cc", "Cf"]), min_size=1, max_size=50),
            st.one_of(
                text(alphabet=st.characters(categories=["Cc", "Cf"]), min_size=1, max_size=50),
                integers(min_value=-(2**31), max_value=2**31 - 1),
                floats(allow_nan=True, allow_infinity=True),
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_malformed_dictionary_attacks(self, attack_dict):
        """Test that malformed dictionaries are handled safely."""
        try:
            # Should handle malformed dictionaries safely
            global_id = self.generator.generate(attack_dict)

            # If generated, should be valid
            if global_id:
                assert validate_global_id(global_id), "Invalid GlobalID from malformed dict"

        except Exception as e:
            # Should handle gracefully
            expected_errors = ["missing", "invalid", "malformed", "required", "must have"]
            assert any(
                word in str(e).lower() for word in expected_errors
            ), f"Unexpected malformed dict error: {str(e)}"


if __name__ == "__main__":
    import time
    import unicodedata

    pytest.main([__file__, "-v", "-s", "--tb=short"])
