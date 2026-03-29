import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage9_write_and_diff import write_and_diff
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage11_idempotency_check import idempotency_check


@pytest.mark.timeout(15)
def test_idempotency_shuffled_zero_diff(tmp_path):
    base = tmp_path / "snapshots"
    base.mkdir(parents=True, exist_ok=True)
    batch = [
        {
            "GlobalID": "A",
            "CanonicalLatin": "Euler, Leonhard",
            "Field": "Mathematics",
            "Source": "Manual",
            "DetectedRegion": "A2",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
            "Advisors": ["B"],
        },
        {
            "GlobalID": "B",
            "CanonicalLatin": "Bernoulli, Jakob",
            "Field": "Mathematics",
            "Source": "Manual",
            "DetectedRegion": "A2",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
    ]
    _, m9, sdir = write_and_diff(batch, out_base=str(base), templates_dir="templates")
    _, m11 = idempotency_check(
        batch, snapshot_dir=sdir, out_base=str(base), mode="shuffled", strict=False
    )
    assert m11["idempotency_diff_bytes"] == 0.0
