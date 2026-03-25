"""
Unit tests for YAML schema validation.

Tests JSON schema v1.5 validation and custom validation rules.
"""

import pytest
from unittest.mock import patch

from src.pipeline.stage8_global_validate import (
    stage8_global_validate,
)
from src.validation.schema import SchemaValidator, validate_entry


# Helper: minimal required fields for a valid v1.5 entry
def _base_entry(**overrides):
    """Build a valid base entry with all required v1.5 fields."""
    entry = {
        "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
        "UpdatedAt": "2025-01-01T00:00:00Z",
        "CanonicalLatin": "Smith, John",
        "CanonicalNative": "Smith, John",
        "LanguageOfPublication": ["en"],
        "FamilyNameType": "surname",
        "Gender": "unspecified",
        "CountryCodes": ["US"],
        "Confidence": 90,
        "Historic": False,
        "GDPR_DATA": False,
    }
    entry.update(overrides)
    return entry


class TestSchemaValidator:
    """Test YAML schema validation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SchemaValidator()

    def test_valid_minimal_entry(self):
        """Test minimal valid entry (all required v1.5 fields)."""
        entry = _base_entry()

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
            entry = _base_entry(GlobalID=global_id)

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert is_valid, f"Expected valid GlobalID: {global_id}, errors: {errors}"
            else:
                assert not is_valid, f"Expected invalid GlobalID: {global_id}"

    def test_birth_death_year_consistency(self):
        """Test birth/death year consistency validation."""
        # Death before birth (invalid)
        entry = _base_entry(BirthYear=1980, DeathYear=1970)

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
            entry = _base_entry(BirthYear=birth_year)

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert is_valid, f"Expected valid birth year: {birth_year}, errors: {errors}"
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
            entry = _base_entry(PrimaryMSC=[{"code": msc_code, "source": "zbMATH"}])

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert is_valid, f"Expected valid MSC code: {msc_code}, errors: {errors}"
            else:
                assert not is_valid, f"Expected invalid MSC code: {msc_code}"

    def test_msc_code_missing_source(self):
        """Test MSC code requires source field."""
        entry = _base_entry(PrimaryMSC=[{"code": "60G15"}])

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
            entry = _base_entry(AuthorityIDs={"ORCID": orcid})

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert is_valid, f"Expected valid ORCID: {orcid}, errors: {errors}"
            else:
                assert not is_valid, f"Expected invalid ORCID: {orcid}"

    def test_proprietary_license_validation(self):
        """Test proprietary sources require license field."""
        # Scopus without license (invalid)
        entry = _base_entry(AuthorityIDs={"Scopus": "123456789"})

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("Scopus" in error and "license" in error for error in errors)

    def test_proprietary_license_valid(self):
        """Test proprietary sources with proper license field."""
        entry = _base_entry(
            AuthorityIDs={
                "Scopus": {"id": "123456789", "license": "Elsevier"},
                "Dimensions": {"id": "987654321", "license": "Digital Science"},
            }
        )

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
            entry = _base_entry(LanguageOfPublication=languages)

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert is_valid, f"Expected valid languages: {languages}, errors: {errors}"
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
            entry = _base_entry(Confidence=confidence)

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            if should_be_valid:
                assert is_valid, f"Expected valid confidence: {confidence}, errors: {errors}"
            else:
                assert not is_valid, f"Expected invalid confidence: {confidence}"

    def test_name_events_chronology(self):
        """Test name events chronological order."""
        # Events out of order (invalid)
        entry = _base_entry(
            NameEvents=[
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
            ]
        )

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("chronological" in error for error in errors)

    def test_affiliation_timeline_validation(self):
        """Test affiliation timeline validation."""
        # Invalid country code
        entry = _base_entry(
            AffiliationTimeline=[{"country": "USA", "from": 2010, "to": 2020}]  # Should be US
        )

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("country" in error for error in errors)

    def test_affiliation_timeline_date_consistency(self):
        """Test affiliation timeline date consistency."""
        # 'To' before 'from' (invalid)
        entry = _base_entry(AffiliationTimeline=[{"country": "US", "from": 2020, "to": 2010}])

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
            entry = _base_entry(
                Variants={"Synthesised": [{"str": "Smith, J", "type": variant_type}]}
            )

            file_data = {"Smith, John": entry}
            is_valid, errors = self.validator.validate_file_structure(file_data)

            assert is_valid, f"Valid variant type failed: {variant_type}, errors: {errors}"

        # Test invalid type
        entry = _base_entry(Variants={"Synthesised": [{"str": "Smith, J", "type": "invalid-type"}]})

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("variant type" in error for error in errors)

    def test_advisor_references_validation(self):
        """Test advisor GlobalID reference validation."""
        # Invalid advisor GlobalID
        entry = _base_entry(Advisors=["INVALID_GLOBALID"])

        file_data = {"Smith, John": entry}
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("advisor" in error and "GlobalID" in error for error in errors)

    def test_canonical_name_consistency(self):
        """Test consistency between key and CanonicalLatin."""
        # Mismatched canonical name
        entry = _base_entry(CanonicalLatin="Johnson, Mary", CanonicalNative="Johnson, Mary")

        file_data = {"Smith, John": entry}  # Key doesn't match
        is_valid, errors = self.validator.validate_file_structure(file_data)

        assert not is_valid
        assert any("mismatch" in error for error in errors)

    def test_single_entry_validation(self):
        """Test validation of single entry (not full file)."""
        entry = _base_entry()

        is_valid = self.validator.validate_entry(entry)
        assert is_valid

    def test_convenience_function(self):
        """Test module-level convenience function."""
        entry = _base_entry()

        is_valid = validate_entry(entry)
        assert is_valid


# ── Stage 8 Schema Strict Mode Tests ─────────────────────────────────────


def _stage8_entry(**overrides):
    """Build a valid entry for stage8 testing (all required fields present)."""
    entry = {
        "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
        "UpdatedAt": "2025-01-01T00:00:00Z",
        "CanonicalLatin": "Smith, John",
        "CanonicalNative": "Smith, John",
        "LanguageOfPublication": ["en"],
        "FamilyNameType": "surname",
        "Gender": "unspecified",
        "CountryCodes": ["US"],
        "Confidence": 90,
        "Historic": False,
        "GDPR_DATA": False,
    }
    entry.update(overrides)
    return entry


class TestStage8StrictMode:
    """Test GMNAP_SCHEMA_STRICT modes in stage8_global_validate."""

    # ── Mode 0: Advisory (default) ──────────────────────────────────────

    def test_strict_0_valid_entries_pass(self):
        """Mode 0: Valid entries pass through unchanged."""
        batch = [_stage8_entry()]
        result, metrics = stage8_global_validate(batch, schema_strict=0)
        assert len(result) == 1
        assert metrics["schema_errors"] == 0
        assert metrics["quarantined_count"] == 0
        assert metrics["rejected_count"] == 0

    def test_strict_0_missing_required_quarantines(self):
        """Mode 0: Missing required fields quarantines entry to Z0."""
        entry = _stage8_entry()
        del entry["Gender"]
        batch = [entry]
        result, metrics = stage8_global_validate(batch, schema_strict=0)
        assert len(result) == 1  # entry still in output
        assert result[0]["DetectedRegion"] == "Z0"
        assert result[0]["RegionalExtras"]["quarantined"] is True
        assert metrics["quarantined_count"] == 1
        assert metrics["rejected_count"] == 0

    def test_strict_0_non_required_error_passes_through(self):
        """Mode 0: Non-required schema errors (e.g. invalid enum) are logged but entry passes."""
        entry = _stage8_entry(FamilyNameType="invalid_type")
        batch = [entry]
        result, metrics = stage8_global_validate(batch, schema_strict=0)
        assert len(result) == 1
        assert metrics["schema_errors"] > 0
        # NOT quarantined because it's not a missing-required-field error
        assert metrics["quarantined_count"] == 0
        assert metrics["rejected_count"] == 0
        assert result[0].get("DetectedRegion") != "Z0"

    # ── Mode 1: Strict quarantine ───────────────────────────────────────

    def test_strict_1_valid_entries_pass(self):
        """Mode 1: Valid entries pass through unchanged."""
        batch = [_stage8_entry()]
        result, metrics = stage8_global_validate(batch, schema_strict=1)
        assert len(result) == 1
        assert metrics["quarantined_count"] == 0
        assert metrics["rejected_count"] == 0

    def test_strict_1_missing_required_quarantines(self):
        """Mode 1: Missing required fields quarantines entry to Z0."""
        entry = _stage8_entry()
        del entry["Gender"]
        batch = [entry]
        result, metrics = stage8_global_validate(batch, schema_strict=1)
        assert len(result) == 1
        assert result[0]["DetectedRegion"] == "Z0"
        assert result[0]["RegionalExtras"]["quarantined"] is True
        assert metrics["quarantined_count"] == 1

    def test_strict_1_non_required_error_also_quarantines(self):
        """Mode 1: ALL schema errors cause quarantine, not just missing-required."""
        entry = _stage8_entry(FamilyNameType="invalid_type")
        batch = [entry]
        result, metrics = stage8_global_validate(batch, schema_strict=1)
        assert len(result) == 1  # still in output
        assert result[0]["DetectedRegion"] == "Z0"
        assert result[0]["RegionalExtras"]["quarantined"] is True
        assert metrics["quarantined_count"] == 1
        assert metrics["rejected_count"] == 0

    def test_strict_1_invalid_gender_quarantines(self):
        """Mode 1: Invalid gender enum quarantines."""
        entry = _stage8_entry(Gender="unknown")
        batch = [entry]
        result, metrics = stage8_global_validate(batch, schema_strict=1)
        assert len(result) == 1
        assert result[0]["DetectedRegion"] == "Z0"
        assert metrics["quarantined_count"] == 1

    def test_strict_1_invalid_confidence_quarantines(self):
        """Mode 1: Out-of-range Confidence quarantines."""
        entry = _stage8_entry(Confidence=150)
        batch = [entry]
        result, metrics = stage8_global_validate(batch, schema_strict=1)
        assert len(result) == 1
        assert result[0]["DetectedRegion"] == "Z0"
        assert metrics["quarantined_count"] == 1

    # ── Mode 2: Strict reject ──────────────────────────────────────────

    def test_strict_2_valid_entries_pass(self):
        """Mode 2: Valid entries pass through."""
        batch = [_stage8_entry()]
        result, metrics = stage8_global_validate(batch, schema_strict=2)
        assert len(result) == 1
        assert metrics["rejected_count"] == 0

    def test_strict_2_missing_required_rejects(self):
        """Mode 2: Missing required fields rejects entry from output entirely."""
        entry = _stage8_entry()
        del entry["Gender"]
        batch = [entry]
        result, metrics = stage8_global_validate(batch, schema_strict=2)
        assert len(result) == 0  # entry excluded from output
        assert metrics["rejected_count"] == 1
        assert metrics["quarantined_count"] == 0

    def test_strict_2_non_required_error_rejects(self):
        """Mode 2: ALL schema errors cause rejection."""
        entry = _stage8_entry(FamilyNameType="invalid_type")
        batch = [entry]
        result, metrics = stage8_global_validate(batch, schema_strict=2)
        assert len(result) == 0
        assert metrics["rejected_count"] == 1

    def test_strict_2_mixed_batch(self):
        """Mode 2: Mixed batch — valid entries pass, invalid rejected."""
        batch = [
            _stage8_entry(CanonicalLatin="Good, Entry"),
            _stage8_entry(FamilyNameType="bad_enum"),
            _stage8_entry(CanonicalLatin="Also Good, Entry"),
        ]
        result, metrics = stage8_global_validate(batch, schema_strict=2)
        assert len(result) == 2
        assert metrics["rejected_count"] == 1
        names = [e["CanonicalLatin"] for e in result]
        assert "Good, Entry" in names
        assert "Also Good, Entry" in names

    def test_strict_2_invalid_country_code_rejects(self):
        """Mode 2: Invalid country code rejects entry."""
        entry = _stage8_entry(CountryCodes=["USA"])  # Should be 2-letter
        batch = [entry]
        result, metrics = stage8_global_validate(batch, schema_strict=2)
        assert len(result) == 0
        assert metrics["rejected_count"] == 1

    # ── Roundtrip not affected by strict mode ───────────────────────────

    def test_roundtrip_failures_not_affected_by_strict_mode(self):
        """Roundtrip failures are flagged but never quarantined or rejected."""
        entry = _stage8_entry(
            CanonicalLatin="Tanaka, Hiroshi",
            CanonicalNative="田中博",
            CanonicalLatin_Folded="totally_different_name",
        )
        for strict_level in [0, 1, 2]:
            batch = [entry.copy()]
            result, metrics = stage8_global_validate(batch, schema_strict=strict_level)
            # Entry should always be in output (roundtrip doesn't cause rejection)
            assert len(result) == 1, f"strict={strict_level}: entry should be in output"
            assert metrics["roundtrip_failures"] == 1
            assert metrics["rejected_count"] == 0
            assert metrics["quarantined_count"] == 0

    # ── Metrics correctness ─────────────────────────────────────────────

    def test_metrics_schema_errors_counted_in_all_modes(self):
        """Schema errors are counted regardless of strict mode."""
        entry = _stage8_entry(Gender="invalid")
        for strict_level in [0, 1, 2]:
            batch = [entry.copy()]
            _, metrics = stage8_global_validate(batch, schema_strict=strict_level)
            assert metrics["schema_errors"] > 0, f"strict={strict_level}: should count errors"

    def test_empty_batch_all_modes(self):
        """Empty batch works in all modes."""
        for strict_level in [0, 1, 2]:
            result, metrics = stage8_global_validate([], schema_strict=strict_level)
            assert result == []
            assert metrics["schema_errors"] == 0
            assert metrics["quarantined_count"] == 0
            assert metrics["rejected_count"] == 0

    # ── ENV var wiring ──────────────────────────────────────────────────

    def test_env_var_default_is_0(self):
        """GMNAP_SCHEMA_STRICT defaults to 0 if not set."""
        import os

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GMNAP_SCHEMA_STRICT", None)
            val = int(os.getenv("GMNAP_SCHEMA_STRICT", "0"))
            assert val == 0

    def test_env_var_parses_correctly(self):
        """GMNAP_SCHEMA_STRICT env var parses to int."""
        import os

        for expected in [0, 1, 2]:
            with patch.dict(os.environ, {"GMNAP_SCHEMA_STRICT": str(expected)}):
                val = int(os.getenv("GMNAP_SCHEMA_STRICT", "0"))
                assert val == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
