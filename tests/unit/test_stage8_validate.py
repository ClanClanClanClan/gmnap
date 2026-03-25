"""Unit tests for Stage 8: Global Schema Validation."""

from src.pipeline.stage8_global_validate import validate_entry_schema


def _minimal_entry(**overrides):
    """Build a minimal valid entry with all required fields."""
    base = {
        "GlobalID": "AAAAAAAAAAAAAAAAAAAAAA",
        "CanonicalLatin": "Euler, Leonhard",
        "CanonicalNative": "Euler, Leonhard",
        "UpdatedAt": "2024-01-01T00:00:00Z",
        "LanguageOfPublication": ["en"],
        "FamilyNameType": "surname",
        "Gender": "male",
        "CountryCodes": ["CH"],
        "Confidence": 95.0,
        "Historic": True,
        "GDPR_DATA": False,
    }
    base.update(overrides)
    return base


class TestValidateEntrySchema:
    def test_valid_minimal_entry(self):
        entry = _minimal_entry()
        errors = validate_entry_schema(entry)
        schema_errors = [e for e in errors if e.startswith("schema:")]
        assert len(schema_errors) == 0, f"Unexpected schema errors: {schema_errors}"

    def test_implausible_lifespan_flagged(self):
        entry = _minimal_entry(BirthYear=1800, DeathYear=2024)  # 224 years!
        errors = validate_entry_schema(entry)
        lifespan_errors = [e for e in errors if "lifespan" in e.lower()]
        assert len(lifespan_errors) > 0

    def test_non_schema_fields_stripped(self):
        entry = _minimal_entry(PublicationCount=42, HIndex=10)
        errors = validate_entry_schema(entry)
        schema_errors = [e for e in errors if e.startswith("schema:")]
        assert len(schema_errors) == 0  # Non-schema fields should be stripped

    def test_internal_fields_stripped(self):
        entry = _minimal_entry(_sources=["OpenAlex"], _InstitutionAll=["MIT"])
        errors = validate_entry_schema(entry)
        schema_errors = [e for e in errors if e.startswith("schema:")]
        assert len(schema_errors) == 0

    def test_empty_entry_has_errors(self):
        errors = validate_entry_schema({})
        assert len(errors) > 0
