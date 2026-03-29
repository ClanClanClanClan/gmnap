import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage8_global_validate import global_validate


@pytest.mark.timeout(15)
def test_roundtrip_proxy():
    batch = [
        {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUVWX"[:22],
            "CanonicalLatin": "Chen Jingrun",
            "CanonicalNative": "陈景润",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        }
    ]
    out, m = global_validate(batch, mode="Quick")
    assert "schema_errors" in m
