import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage8_global_validate import global_validate


@pytest.mark.timeout(15)
def test_schema_validation_and_coherence_pass():
    good = [
        {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUVWX"[:22],
            "CanonicalLatin": "Euler, Leonhard",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        }
    ]
    out, metrics = global_validate(good, mode="Quick")
    assert isinstance(out, list) and "schema_errors" in metrics


@pytest.mark.timeout(15)
def test_schema_validation_fail():
    bad = [{"GlobalID": "NOTVALID"}]
    with pytest.raises(ValueError):
        global_validate(bad, mode="Quick")
