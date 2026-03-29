"""
Security testing for schema validation.
Tests against injection attacks, malformed data, and edge cases.
"""

import json

import pytest

from src.validation.schema import SchemaValidator


@pytest.mark.security
class TestSchemaSecurityValidation:
    """Security tests for schema validation."""

    def test_sql_injection_in_names(self, injection_test_payloads):
        """Test SQL injection payloads in name fields."""
        validator = SchemaValidator()

        for payload in injection_test_payloads["sql_injection"]:
            entry_data = {
                payload: {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": payload,
                    "CanonicalNative": payload,
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": 95,
                    "Historic": False,
                    "GDPR_DATA": False,
                }
            }

            # Should handle injection payloads safely
            is_valid, errors = validator.validate_entry(entry_data)
            # May or may not be valid depending on payload, but should not crash
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)

    def test_xss_injection_in_fields(self, injection_test_payloads):
        """Test XSS injection payloads in various fields."""
        validator = SchemaValidator()

        for payload in injection_test_payloads["xss_injection"]:
            entry_data = {
                "Smith, John": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": "Smith, John",
                    "CanonicalNative": "Smith, John",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": 95,
                    "Historic": False,
                    "GDPR_DATA": False,
                    "Comments": payload,  # Inject into comments field
                    "SourceNote": payload,  # Inject into source note
                }
            }

            # Should handle XSS payloads safely
            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)

    def test_path_traversal_in_schema_path(self, injection_test_payloads, temp_dir):
        """Test path traversal attacks in schema file path."""
        # Create a fake schema file
        fake_schema = {"type": "object"}
        schema_path = temp_dir / "schema.json"
        with open(schema_path, "w") as f:
            json.dump(fake_schema, f)

        for payload in injection_test_payloads["path_traversal"]:
            try:
                # Should not allow path traversal
                SchemaValidator(str(temp_dir / payload))
                # If it doesn't crash, that's fine, but should not access outside files
            except (FileNotFoundError, ValueError, OSError):
                # Expected for invalid paths
                pass
            except Exception as e:
                # Should not crash with unexpected exceptions
                pytest.fail(f"Unexpected exception with path traversal {payload}: {e}")

    def test_command_injection_in_fields(self, injection_test_payloads):
        """Test command injection payloads."""
        validator = SchemaValidator()

        for payload in injection_test_payloads["command_injection"]:
            entry_data = {
                "Smith, John": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": "Smith, John",
                    "CanonicalNative": "Smith, John",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": 95,
                    "Historic": False,
                    "GDPR_DATA": False,
                    "Comments": payload,
                }
            }

            # Should not execute commands
            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)

    def test_format_string_attacks(self, injection_test_payloads):
        """Test format string attack payloads."""
        validator = SchemaValidator()

        for payload in injection_test_payloads["format_string"]:
            entry_data = {
                "Smith, John": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": "Smith, John",
                    "CanonicalNative": "Smith, John",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": 95,
                    "Historic": False,
                    "GDPR_DATA": False,
                    "SourceNote": payload,
                }
            }

            # Should handle format strings safely
            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)

    def test_unicode_attacks(self, injection_test_payloads):
        """Test Unicode-based attacks."""
        validator = SchemaValidator()

        for payload in injection_test_payloads["unicode_attacks"]:
            entry_data = {
                f"Smith{payload}John": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": f"Smith{payload}John",
                    "CanonicalNative": f"Smith{payload}John",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": 95,
                    "Historic": False,
                    "GDPR_DATA": False,
                }
            }

            # Should handle Unicode attacks safely
            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)

    def test_extremely_large_payloads(self):
        """Test extremely large payloads that might cause DoS."""
        validator = SchemaValidator()

        # Very long strings
        long_string = "A" * 1000000  # 1MB string

        entry_data = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "LanguageOfPublication": ["en"],
                "FamilyNameType": "surname",
                "Gender": "male",
                "GenderProvided": True,
                "CountryCodes": ["US"],
                "Confidence": 95,
                "Historic": False,
                "GDPR_DATA": False,
                "Comments": long_string,
            }
        }

        # Should handle large payloads without crashing
        try:
            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)
        except MemoryError:
            # Acceptable to run out of memory on very large inputs
            pass

    def test_deeply_nested_structures(self):
        """Test deeply nested structures that might cause stack overflow."""
        validator = SchemaValidator()

        # Create deeply nested RegionalExtras
        nested_dict = {}
        current = nested_dict
        for i in range(1000):  # Deep nesting
            current["level"] = {}
            current = current["level"]
        current["value"] = "deep"

        entry_data = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "LanguageOfPublication": ["en"],
                "FamilyNameType": "surname",
                "Gender": "male",
                "GenderProvided": True,
                "CountryCodes": ["US"],
                "Confidence": 95,
                "Historic": False,
                "GDPR_DATA": False,
                "RegionalExtras": nested_dict,
            }
        }

        # Should handle deep nesting safely
        try:
            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)
        except RecursionError:
            # Acceptable to hit recursion limits
            pass

    def test_malformed_json_schema(self, temp_dir):
        """Test handling of malformed JSON schema files."""
        # Create malformed schema file
        malformed_schema_path = temp_dir / "malformed.json"
        with open(malformed_schema_path, "w") as f:
            f.write('{"invalid": json, "missing": quotes}')

        # Should handle malformed schema gracefully
        with pytest.raises(ValueError, match="Invalid JSON"):
            SchemaValidator(str(malformed_schema_path))

    def test_schema_file_not_found(self, temp_dir):
        """Test handling of missing schema file."""
        nonexistent_path = temp_dir / "nonexistent.json"

        # Should handle missing file gracefully
        with pytest.raises(FileNotFoundError):
            SchemaValidator(str(nonexistent_path))

    def test_invalid_yaml_file_security(self, temp_dir):
        """Test security with invalid YAML files."""
        # Create YAML file with potential security issues
        yaml_content = """
Smith, John:
  GlobalID: !!python/object/apply:os.system ["rm -rf /"]
  UpdatedAt: "2025-07-15T10:30:00Z"
  CanonicalLatin: "Smith, John"
  CanonicalNative: "Smith, John"
  LanguageOfPublication: ["en"]
  FamilyNameType: "surname"
  Gender: "male"
  GenderProvided: true
  CountryCodes: ["US"]
  Confidence: 95
  Historic: false
  GDPR_DATA: false
"""

        yaml_path = temp_dir / "malicious.yaml"
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        # Should not execute arbitrary code
        validator = SchemaValidator()
        is_valid, errors = validator.validate_yaml_file(str(yaml_path))

        # Should fail validation but not execute code
        assert not is_valid
        assert len(errors) > 0

    def test_circular_references(self):
        """Test handling of circular references in data."""
        validator = SchemaValidator()

        # Create circular reference
        circular_dict = {"ref": None}
        circular_dict["ref"] = circular_dict

        entry_data = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "LanguageOfPublication": ["en"],
                "FamilyNameType": "surname",
                "Gender": "male",
                "GenderProvided": True,
                "CountryCodes": ["US"],
                "Confidence": 95,
                "Historic": False,
                "GDPR_DATA": False,
                "RegionalExtras": circular_dict,
            }
        }

        # Should handle circular references safely
        try:
            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)
        except (ValueError, RecursionError):
            # Acceptable to fail on circular references
            pass

    def test_special_numeric_values(self):
        """Test handling of special numeric values."""
        validator = SchemaValidator()

        special_values = [
            float("inf"),
            float("-inf"),
            float("nan"),
            999999999999999999999999999999,  # Very large number
            -999999999999999999999999999999,  # Very large negative
        ]

        for value in special_values:
            entry_data = {
                "Smith, John": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": "Smith, John",
                    "CanonicalNative": "Smith, John",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": value,  # Use special value
                    "Historic": False,
                    "GDPR_DATA": False,
                }
            }

            # Should handle special numeric values safely
            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)

    def test_memory_exhaustion_arrays(self):
        """Test arrays that might cause memory exhaustion."""
        validator = SchemaValidator()

        # Very large array
        large_array = ["item"] * 100000

        entry_data = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "LanguageOfPublication": large_array[:10],  # Limit to valid size
                "FamilyNameType": "surname",
                "Gender": "male",
                "GenderProvided": True,
                "CountryCodes": large_array[:2],  # Would be invalid
                "Confidence": 95,
                "Historic": False,
                "GDPR_DATA": False,
            }
        }

        # Should handle large arrays safely
        try:
            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)
        except MemoryError:
            # Acceptable to run out of memory
            pass

    def test_regex_dos_attacks(self):
        """Test ReDoS (Regular Expression Denial of Service) attacks."""
        validator = SchemaValidator()

        # Patterns that might cause catastrophic backtracking
        redos_patterns = [
            "a" * 1000 + "X",  # Pattern that doesn't match after long string
            "(" + "a" * 100 + ")*" + "X",  # Nested quantifiers
            "a" * 10000,  # Very long string
        ]

        for pattern in redos_patterns:
            entry_data = {
                "Smith, John": {
                    "GlobalID": pattern[:22] if len(pattern) >= 22 else "A" * 22,
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": "Smith, John",
                    "CanonicalNative": "Smith, John",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": 95,
                    "Historic": False,
                    "GDPR_DATA": False,
                }
            }

            # Should complete in reasonable time
            import time

            start_time = time.time()

            is_valid, errors = validator.validate_entry(entry_data)

            elapsed = time.time() - start_time
            assert elapsed < 5.0, f"Validation took too long: {elapsed}s"

    def test_type_confusion_attacks(self):
        """Test type confusion attacks."""
        validator = SchemaValidator()

        # Wrong types for fields
        type_confusion_data = {
            "Smith, John": {
                "GlobalID": 12345,  # Should be string
                "UpdatedAt": ["not", "a", "date"],  # Should be string
                "CanonicalLatin": {"not": "a string"},  # Should be string
                "CanonicalNative": True,  # Should be string
                "LanguageOfPublication": "en",  # Should be array
                "FamilyNameType": 123,  # Should be string enum
                "Gender": ["male"],  # Should be string
                "GenderProvided": "true",  # Should be boolean
                "CountryCodes": "US",  # Should be array
                "Confidence": "95",  # Should be integer
                "Historic": 0,  # Should be boolean
                "GDPR_DATA": "false",  # Should be boolean
            }
        }

        # Should handle type confusion safely
        is_valid, errors = validator.validate_entry(type_confusion_data)
        assert not is_valid  # Should be invalid
        assert len(errors) > 0  # Should have errors
        assert isinstance(errors, list)

    def test_encoding_attacks(self, temp_dir):
        """Test various encoding attacks."""
        validator = SchemaValidator()

        # Different encodings that might cause issues
        encoding_tests = [
            b"\xff\xfe\x00\x00",  # UTF-32 BOM
            b"\xff\xfe",  # UTF-16 BOM
            b"\xef\xbb\xbf",  # UTF-8 BOM
            b"\x00\x00\xfe\xff",  # UTF-32 BE BOM
        ]

        for encoding_bytes in encoding_tests:
            yaml_path = temp_dir / f"encoding_test_{len(encoding_bytes)}.yaml"

            # Write binary data
            with open(yaml_path, "wb") as f:
                f.write(encoding_bytes)
                f.write(b'Smith, John: {GlobalID: "ABCDEFGHIJKLMNOPQRSTUV"}')

            # Should handle encoding issues gracefully
            try:
                is_valid, errors = validator.validate_yaml_file(str(yaml_path))
                assert isinstance(is_valid, bool)
                assert isinstance(errors, list)
            except UnicodeDecodeError:
                # Acceptable to fail on invalid encoding
                pass


@pytest.mark.security
@pytest.mark.paranoid
class TestSchemaEdgeCases:
    """Edge case testing for schema validation."""

    def test_empty_and_whitespace_only_fields(self):
        """Test empty and whitespace-only fields."""
        validator = SchemaValidator()

        test_cases = [
            "",
            " ",
            "\t",
            "\n",
            "\r\n",
            "   \t\n\r   ",
            "\x00",
            "\x20",
        ]

        for test_value in test_cases:
            entry_data = {
                f"Smith{test_value}John": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": f"Smith{test_value}John",
                    "CanonicalNative": f"Smith{test_value}John",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": 95,
                    "Historic": False,
                    "GDPR_DATA": False,
                    "Comments": test_value,
                }
            }

            # Should handle edge case values
            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)

    def test_boundary_values(self):
        """Test boundary values for numeric fields."""
        validator = SchemaValidator()

        boundary_tests = [
            ("Confidence", -1),  # Below minimum
            ("Confidence", 0),  # Minimum
            ("Confidence", 100),  # Maximum
            ("Confidence", 101),  # Above maximum
            ("BirthYear", -3001),  # Below minimum
            ("BirthYear", -3000),  # Minimum
            ("BirthYear", 2100),  # Maximum
            ("BirthYear", 2101),  # Above maximum
        ]

        for field, value in boundary_tests:
            entry_data = {
                "Smith, John": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": "Smith, John",
                    "CanonicalNative": "Smith, John",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": 95,
                    "Historic": False,
                    "GDPR_DATA": False,
                }
            }

            # Set the test value
            entry_data["Smith, John"][field] = value

            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)

    def test_array_length_boundaries(self):
        """Test array length boundaries."""
        validator = SchemaValidator()

        # Test LanguageOfPublication max length (10)
        entry_data = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "LanguageOfPublication": ["en"] * 11,  # Too many
                "FamilyNameType": "surname",
                "Gender": "male",
                "GenderProvided": True,
                "CountryCodes": ["US"],
                "Confidence": 95,
                "Historic": False,
                "GDPR_DATA": False,
            }
        }

        is_valid, errors = validator.validate_entry(entry_data)
        assert not is_valid  # Should be invalid
        assert any("LanguageOfPublication" in error for error in errors)

    def test_special_characters_in_ids(self):
        """Test special characters in ID fields."""
        validator = SchemaValidator()

        special_chars = [
            "ABCDEFGHIJKLMNOPQRSTUV",  # Valid
            "abcdefghijklmnopqrstuv",  # Lowercase (invalid)
            "ABCDEFGHIJKLMNOPQRSTU0",  # Contains 0 (invalid in Base32)
            "ABCDEFGHIJKLMNOPQRSTU1",  # Contains 1 (invalid in Base32)
            "ABCDEFGHIJKLMNOPQRSTU@",  # Special character
            "ABCDEFGHIJKLMNOPQRSTUV=",  # Padding character
            "ABCDEFGHIJKLMNOPQRST",  # Too short
            "ABCDEFGHIJKLMNOPQRSTUVW",  # Too long
        ]

        for global_id in special_chars:
            entry_data = {
                "Smith, John": {
                    "GlobalID": global_id,
                    "UpdatedAt": "2025-07-15T10:30:00Z",
                    "CanonicalLatin": "Smith, John",
                    "CanonicalNative": "Smith, John",
                    "LanguageOfPublication": ["en"],
                    "FamilyNameType": "surname",
                    "Gender": "male",
                    "GenderProvided": True,
                    "CountryCodes": ["US"],
                    "Confidence": 95,
                    "Historic": False,
                    "GDPR_DATA": False,
                }
            }

            is_valid, errors = validator.validate_entry(entry_data)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)

            # Only the first should be valid
            if global_id == "ABCDEFGHIJKLMNOPQRSTUV":
                assert is_valid
            else:
                assert not is_valid
