#!/usr/bin/env python3
import os, json
from src.pipeline.stage9_write_and_diff import write_and_diff
from src.pipeline.stage11_idempotency_check import idempotency_check

if __name__ == "__main__":
    os.makedirs("snapshots", exist_ok=True)
    batch = [
        {
            "GlobalID": "X",
            "CanonicalLatin": "Noether, Emmy",
            "Field": "Mathematics",
            "Source": "Manual",
            "DetectedRegion": "A2",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
            "Advisors": ["Y"],
        },
        {
            "GlobalID": "Y",
            "CanonicalLatin": "Hilbert, David",
            "Field": "Mathematics",
            "Source": "Manual",
            "DetectedRegion": "A2",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
    ]
    _, m9, sdir = write_and_diff(batch, out_base="snapshots", templates_dir="templates")
    _, m11 = idempotency_check(
        batch, snapshot_dir=sdir, mode=os.getenv("GMNAP_IDEMPOTENCY_MODE", "shuffled")
    )
    print("Idempotency:", m11)
