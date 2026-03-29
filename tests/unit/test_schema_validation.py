"""
Unit tests for YAML schema validation.

Tests JSON schema v1.5 validation and custom validation rules.
"""

from datetime import datetime

import pytest

from src.validation.schema import SchemaValidator, validate_entry


class TestSchemaValidator:
    """Test YAML schema validation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SchemaValidator()

    def test_valid_minimal_entry(self):
        """Test minimal valid entry."""
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert is_valid, f"Validation failed: {errors}"

    def test_valid_complete_entry(self):
        """Test complete valid entry with all fields."""
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "García, José",
            "CanonicalNative": "García, José",
            "LanguageOfPublication": ["en", "es"],
            "AffiliationTimeline": [
                {"country": "US", "from": 2010, "to": 2020},
                {"country": "ES", "from": 2020, "to": None},
            ],
            "Variants": {
                "Observed": [
                    {
                        "str": "Garcia, Jose",
                        "source": "OpenAlex",
                        "accessed": "2025-01-01",
                    }
                ],
                "Synthesised": [{"str": "Garcia, Jose", "type": "ascii-lossy"}],
            },
            "FamilyNameType": "surname",
            "Gender": "male",
            "GenderProvided": True,
            "PreferredPronouns": ["he", "him"],
            "BirthYear": 1980,
            "DeathYear": None,
            "CountryCodes": ["ES"],
            "DiasporaCodes": ["US:2010-2020"],
            "PrimaryMSC": [{"code": "60G15", "source": "zbMATH"}],
            "NameEvents": [
                {
                    "type": "marriage",
                    "year": 2010,
                    "from": "José García",
                    "to": "José García Martín",
                }
            ],
            "Advisors": ["BCDEFGHIJKLMNOPQRSTUVW"],
            "ShortFormClusters": {"García": 5, "J. García": 3},
            "AuthorityIDs": {
                "ORCID": "0000-0003-1234-5678",
                "OpenAlex": "A1234567890",
                "Scopus": {"id": "123456789", "license": "Elsevier"},
            },
            "Confidence": 85,
            "RegionalExtras": {"primary_surname": "García", "ipa": "garˈθia"},
            "Historic": False,
            "GDPR_DATA": False,
            "SourceNote": "OpenAlex import",
            "Comments": "Test entry",
        }

        file_data = {"García, José": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert is_valid, f"Validation failed: {errors}"

    def test_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        # Missing GlobalID
        entry = {
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("GlobalID" in error for error in errors)

    def test_globalid_format_validation(self):
        """Test GlobalID format validation."""
        test_cases = [
            ("ABCDEFGHIJKLMNOPQRSTUV", True),  # Valid
            ("ABCDEFGHIJKLMNOPQRSTUV--1", True),  # With collision
            ("ABCDEFGHIJKLMNOPQRSTUV--42", True),  # Large collision
            ("ABCDEFGHIJKLMNOPQRSTU", False),  # Too short
            ("ABCDEFGHIJKLMNOPQRSTUVW", False),  # Too long
            ("ABCDEFGHIJKLMNOPQRSTU1", False),  # Invalid Base32
            ("ABCDEFGHIJKLMNOPQRSTUV--", False),  # Missing suffix
            ("ABCDEFGHIJKLMNOPQRSTUV--0", False),  # Zero suffix
            ("ABCDEFGHIJKLMNOPQRSTUV--abc", False),  # Non-numeric suffix
        ]

        for global_id, should_be_valid in test_cases:
            entry = {
                "GlobalID": global_id,
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "LanguageOfPublication": ["en"],
                "FamilyNameType": "surname",
                "Gender": "male",
                "CountryCodes": ["US"],
                "Confidence": 95,
                "Historic": False,
                "GDPR_DATA": False,
            }

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert (
                    is_valid
                ), f"Expected valid GlobalID: {global_id}, errors: {errors}"
            else:
                assert not is_valid, f"Expected invalid GlobalID: {global_id}"

    def test_birth_death_year_consistency(self):
        """Test birth/death year consistency validation."""
        # Death before birth (invalid)
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "BirthYear": 1980,
            "DeathYear": 1970,
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("DeathYear" in error and "BirthYear" in error for error in errors)

    def test_birth_year_formats(self):
        """Test various birth year formats."""
        test_cases = [
            (1980, True),  # Integer
            ("1970s", True),  # Decade
            ("-500", True),  # BCE
            ("c1150", True),  # Circa
            ("1150/1160", True),  # Range
            ("invalid", False),  # Invalid format
        ]

        for birth_year, should_be_valid in test_cases:
            entry = {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "BirthYear": birth_year,
            }

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert (
                    is_valid
                ), f"Expected valid birth year: {birth_year}, errors: {errors}"
            else:
                assert not is_valid, f"Expected invalid birth year: {birth_year}"

    def test_msc_code_validation(self):
        """Test MSC code format validation."""
        test_cases = [
            ("60G15", True),  # Valid
            ("03B25", True),  # Valid
            ("60g15", False),  # Lowercase letter
            ("6G15", False),  # Too short
            ("600G15", False),  # Too long
            ("60G1A", False),  # Invalid digit
            ("60615", False),  # Missing letter
        ]

        for msc_code, should_be_valid in test_cases:
            entry = {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "PrimaryMSC": [{"code": msc_code, "source": "zbMATH"}],
            }

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert (
                    is_valid
                ), f"Expected valid MSC code: {msc_code}, errors: {errors}"
            else:
                assert not is_valid, f"Expected invalid MSC code: {msc_code}"

    def test_msc_code_missing_source(self):
        """Test MSC code requires source field."""
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "PrimaryMSC": [{"code": "60G15"}],  # Missing source
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("missing source" in error for error in errors)

    def test_orcid_validation(self):
        """Test ORCID format validation."""
        test_cases = [
            ("0000-0003-1234-5678", True),  # Valid
            ("0000-0003-1234-567X", True),  # Valid with X
            ("0000-0003-1234-5678X", False),  # Invalid X position
            ("0000-0003-1234-56789", False),  # Too long
            ("0000-0003-1234-567", False),  # Too short
            ("0000-0003-1234", False),  # Missing parts
            ("abcd-0003-1234-5678", False),  # Invalid characters
        ]

        for orcid, should_be_valid in test_cases:
            entry = {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "AuthorityIDs": {"ORCID": orcid},
            }

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert is_valid, f"Expected valid ORCID: {orcid}, errors: {errors}"
            else:
                assert not is_valid, f"Expected invalid ORCID: {orcid}"

    def test_proprietary_license_validation(self):
        """Test proprietary sources require license field."""
        # Scopus without license (invalid)
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "AuthorityIDs": {"Scopus": "123456789"},  # String instead of object
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("Scopus" in error and "license" in error for error in errors)

    def test_proprietary_license_valid(self):
        """Test proprietary sources with proper license field."""
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "AuthorityIDs": {
                "Scopus": {"id": "123456789", "license": "Elsevier"},
                "Dimensions": {"id": "987654321", "license": "Digital Science"},
            },
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert is_valid, f"Validation failed: {errors}"

    def test_language_code_validation(self):
        """Test language code validation."""
        test_cases = [
            (["en"], True),  # Valid
            (["en", "es", "fr"], True),  # Multiple valid
            (["eng"], True),  # 3-letter valid
            (["e"], False),  # Too short
            (["english"], False),  # Too long
            (["EN"], False),  # Uppercase
            (["en", "es"] * 6, False),  # Too many (>10)
        ]

        for languages, should_be_valid in test_cases:
            entry = {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "LanguageOfPublication": languages,
            }

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert (
                    is_valid
                ), f"Expected valid languages: {languages}, errors: {errors}"
            else:
                assert not is_valid, f"Expected invalid languages: {languages}"

    def test_confidence_score_validation(self):
        """Test confidence score range validation."""
        test_cases = [
            (0, True),  # Min valid
            (50, True),  # Mid valid
            (100, True),  # Max valid
            (-1, False),  # Below min
            (101, False),  # Above max
            (50.5, True),  # Float valid
        ]

        for confidence, should_be_valid in test_cases:
            entry = {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "Confidence": confidence,
            }

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert (
                    is_valid
                ), f"Expected valid confidence: {confidence}, errors: {errors}"
            else:
                assert not is_valid, f"Expected invalid confidence: {confidence}"

    def test_name_events_chronology(self):
        """Test name events chronological order."""
        # Events out of order (invalid)
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "NameEvents": [
                {
                    "type": "marriage",
                    "year": 2010,
                    "from": "John Smith",
                    "to": "John Smith-Jones",
                },
                {
                    "type": "legal_change",
                    "year": 2005,
                    "from": "John Doe",
                    "to": "John Smith",
                },
            ],
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("chronological" in error for error in errors)

    def test_affiliation_timeline_validation(self):
        """Test affiliation timeline validation."""
        # Invalid country code
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "AffiliationTimeline": [
                {"country": "USA", "from": 2010, "to": 2020}
            ],  # Should be US
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("country" in error for error in errors)

    def test_affiliation_timeline_date_consistency(self):
        """Test affiliation timeline date consistency."""
        # 'To' before 'from' (invalid)
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "AffiliationTimeline": [{"country": "US", "from": 2020, "to": 2010}],
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("to" in error and "from" in error for error in errors)

    def test_synthesised_variant_types(self):
        """Test synthesised variant type validation."""
        valid_types = [
            "ascii-lossy",
            "tone-number",
            "diac-drop",
            "order-swap",
            "romanisation-alt",
            "particle-drop",
            "initial-collapse",
        ]

        # Test valid types
        for variant_type in valid_types:
            entry = {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "Variants": {
                    "Synthesised": [{"str": "Smith, J", "type": variant_type}]
                },
            }

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            assert (
                is_valid
            ), f"Valid variant type failed: {variant_type}, errors: {errors}"

        # Test invalid type
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "Variants": {"Synthesised": [{"str": "Smith, J", "type": "invalid-type"}]},
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("variant type" in error for error in errors)

    def test_advisor_references_validation(self):
        """Test advisor GlobalID reference validation."""
        # Invalid advisor GlobalID
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "Advisors": ["INVALID_GLOBALID"],
        }

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("advisor" in error and "GlobalID" in error for error in errors)

    def test_canonical_name_consistency(self):
        """Test consistency between key and CanonicalLatin."""
        # Mismatched canonical name
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Johnson, Mary",  # Different from key
            "CanonicalNative": "Johnson, Mary",
        }

        file_data = {"Smith, John": entry}  # Key doesn't match
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("mismatch" in error for error in errors)

    def test_single_entry_validation(self):
        """Test validation of single entry (not full file)."""
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
        }

        is_valid = self.validator.validate_entry(entry)
        assert is_valid

    def test_convenience_function(self):
        """Test module-level convenience function."""
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
        }

        is_valid = validate_entry(entry)
        assert is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
