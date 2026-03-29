"""
Tests for YAML schema validation.
"""

import pytest

from src.validation.schema import SchemaValidator, validate_entry


class TestSchemaValidator:
    """Test schema validation functionality."""

    def test_valid_entry(self):
        """Test validation of a valid entry."""
        entry_data = {
            "García, Juan Carlos": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "García, Juan Carlos",
                "CanonicalNative": "García, Juan Carlos",
                "LanguageOfPublication": ["en", "es"],
                "FamilyNameType": "surname",
                "Gender": "male",
                "GenderProvided": True,
                "CountryCodes": ["ES"],
                "Confidence": 96,
                "Historic": False,
                "GDPR_DATA": False,
            }
        }

        validator = SchemaValidator()
        is_valid, errors = validator.validate_entry(entry_data)

        assert is_valid, f"Entry should be valid, but got errors: {errors}"
        assert len(errors) == 0

    def test_invalid_global_id(self):
        """Test validation with invalid GlobalID."""
        entry_data = {
            "Smith, John": {
                "GlobalID": "INVALID_ID",  # Invalid format
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

        validator = SchemaValidator()
        is_valid, errors = validator.validate_entry(entry_data)

        assert not is_valid
        assert any("GlobalID" in error for error in errors)

    def test_missing_required_field(self):
        """Test validation with missing required field."""
        entry_data = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                # Missing LanguageOfPublication (required)
                "FamilyNameType": "surname",
                "Gender": "male",
                "GenderProvided": True,
                "CountryCodes": ["US"],
                "Confidence": 95,
                "Historic": False,
                "GDPR_DATA": False,
            }
        }

        validator = SchemaValidator()
        is_valid, errors = validator.validate_entry(entry_data)

        assert not is_valid
        assert any("LanguageOfPublication" in error for error in errors)

    def test_invalid_msc_code(self):
        """Test validation with invalid MSC code."""
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
                "PrimaryMSC": [
                    {"code": "INVALID", "source": "zbMATH"}
                ],  # Invalid MSC format
                "Confidence": 95,
                "Historic": False,
                "GDPR_DATA": False,
            }
        }

        validator = SchemaValidator()
        is_valid, errors = validator.validate_entry(entry_data)

        assert not is_valid
        assert any("MSC code" in error for error in errors)

    def test_invalid_orcid(self):
        """Test validation with invalid ORCID."""
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
                "AuthorityIDs": {
                    "ORCID": "0000-0000-0000-000X"
                },  # Invalid ORCID format
                "Confidence": 95,
                "Historic": False,
                "GDPR_DATA": False,
            }
        }

        validator = SchemaValidator()
        is_valid, errors = validator.validate_entry(entry_data)

        assert not is_valid
        assert any("ORCID" in error for error in errors)

    def test_birth_death_year_consistency(self):
        """Test validation of birth/death year consistency."""
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
                "BirthYear": 1950,
                "DeathYear": 1940,  # Death before birth
                "CountryCodes": ["US"],
                "Confidence": 95,
                "Historic": False,
                "GDPR_DATA": False,
            }
        }

        validator = SchemaValidator()
        is_valid, errors = validator.validate_entry(entry_data)

        assert not is_valid
        assert any("DeathYear" in error and "BirthYear" in error for error in errors)

    def test_confidence_score_range(self):
        """Test validation of confidence score range."""
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
                "Confidence": 150,  # Out of range
                "Historic": False,
                "GDPR_DATA": False,
            }
        }

        validator = SchemaValidator()
        is_valid, errors = validator.validate_entry(entry_data)

        assert not is_valid
        assert any("Confidence" in error for error in errors)

    def test_canonical_name_mismatch(self):
        """Test validation when canonical name doesn't match key."""
        entry_data = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "Doe, John",  # Doesn't match key
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

        validator = SchemaValidator()
        is_valid, errors = validator.validate_entry(entry_data)

        assert not is_valid
        assert any("mismatch" in error for error in errors)

    def test_valid_optional_fields(self):
        """Test validation with optional fields."""
        entry_data = {
            "García, Juan Carlos": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-07-15T10:30:00Z",
                "CanonicalLatin": "García, Juan Carlos",
                "CanonicalNative": "García, Juan Carlos",
                "LanguageOfPublication": ["en", "es"],
                "AffiliationTimeline": [
                    {"country": "ES", "from": 2000, "to": 2010},
                    {"country": "US", "from": 2010, "to": None},
                ],
                "Variants": {
                    "Observed": [
                        {
                            "str": "J. C. García",
                            "source": "MathSciNet",
                            "accessed": "2025-07-15",
                        }
                    ],
                    "Synthesised": [
                        {"str": "Garcia Juan Carlos", "type": "ascii-lossy"}
                    ],
                },
                "FamilyNameType": "surname",
                "Gender": "male",
                "GenderProvided": True,
                "PreferredPronouns": ["he", "him"],
                "BirthYear": 1975,
                "DeathYear": None,
                "CountryCodes": ["ES"],
                "DiasporaCodes": ["US:2010-"],
                "PrimaryMSC": [{"code": "60G15", "source": "zbMATH"}],
                "NameEvents": [
                    {
                        "type": "marriage",
                        "year": 2005,
                        "from": "Juan Carlos García",
                        "to": "Juan Carlos García Marín",
                    }
                ],
                "Advisors": ["XYZABCDEFGHIJKLMNOPQRS"],
                "ShortFormClusters": {"J. C. García": 4, "García": 38},
                "AuthorityIDs": {
                    "ORCID": "0000-0003-1111-2222",
                    "MathSciNet": "203000",
                },
                "Confidence": 96,
                "RegionalExtras": {
                    "primary_surname": "García",
                    "secondary_surname": "Marín",
                },
                "Historic": False,
                "GDPR_DATA": False,
                "SourceNote": "zbMATH scrape 2025-07-15",
                "Comments": "Free-form curator notes.",
            }
        }

        validator = SchemaValidator()
        is_valid, errors = validator.validate_entry(entry_data)

        assert is_valid, f"Entry should be valid, but got errors: {errors}"

    def test_schema_info(self):
        """Test schema information retrieval."""
        validator = SchemaValidator()
        info = validator.get_schema_info()

        assert "schema_version" in info
        assert "title" in info
        assert "required_fields" in info
        assert "optional_fields" in info

        # Check that required fields are present
        required_fields = info["required_fields"]
        assert "GlobalID" in required_fields
        assert "CanonicalLatin" in required_fields
        assert "LanguageOfPublication" in required_fields

    def test_convenience_functions(self):
        """Test convenience functions."""
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

        # Test validate_entry convenience function
        is_valid, errors = validate_entry(entry_data)
        assert is_valid
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__])
