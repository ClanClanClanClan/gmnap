import pytest

from src.validation.schema_validator import V7SchemaValidator


@pytest.mark.timeout(15)
def test_valid_entry_passes():
    v = V7SchemaValidator()
    ok, errs = v.validate(
        {
            "GlobalID": "X",
            "CanonicalLatin": "Test",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        }
    )
    assert ok and not errs


@pytest.mark.timeout(15)
def test_missing_required_fails():
    v = V7SchemaValidator()
    ok, errs = v.validate({"foo": "bar"})
    assert not ok and any("Missing required field: GlobalID" in e for e in errs)
