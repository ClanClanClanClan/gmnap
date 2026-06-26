import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.schema_validator import CoreV7SchemaValidator as V7SchemaValidator


@pytest.mark.timeout(15)
def test_schema_required_fields():
    v = V7SchemaValidator.load_default_schema()
    ok, errs = v.validate({"foo": "bar"})
    assert not ok and any("Missing required field" in e for e in errs)


@pytest.mark.timeout(15)
def test_schema_valid_minimal():
    v = V7SchemaValidator.load_default_schema()
    entry = {
        "GlobalID": "TEST-001",
        "CanonicalLatin": "Euler, Leonhard",
        "Field": "Mathematics",
        "Source": "Manual",
        "LastUpdated": "2024-01-01T00:00:00Z",
        "ValidationStatus": "pending",
    }
    ok, errs = v.validate(entry)
    assert ok, errs
