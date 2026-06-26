import json
import os

from src.pipeline.stage9_write_and_diff import write_and_diff
from src.pipeline.stage11_idempotency_check import idempotency_check


def test_idempotency_previous_detects_change(tmp_path):
    base = tmp_path / "snapshots"
    base.mkdir(parents=True, exist_ok=True)
    # Run 1
    batch1 = [
        {
            "GlobalID": "A",
            "CanonicalLatin": "Noether, Emmy",
            "Field": "Mathematics",
            "Source": "Manual",
            "DetectedRegion": "A2",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        }
    ]
    _, m9a, sdir1 = write_and_diff(
        batch1, out_base=str(base), templates_dir="templates"
    )
    # Run 2 (mutated)
    batch2 = [dict(batch1[0], CanonicalLatin="Noether, E.")]
    _, m11 = idempotency_check(
        batch2, snapshot_dir=sdir1, out_base=str(base), mode="previous", strict=False
    )
    assert m11["idempotency_diff_bytes"] > 0.0
