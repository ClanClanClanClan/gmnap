#!/usr/bin/env python3
import os, json, shutil
from src.pipeline.stage9_write_and_diff import (
    write_snapshot,
    diff_snapshots,
    generate_sql_changelog,
)

if __name__ == "__main__":
    # Prepare two small batches
    prev_batch = [
        {
            "GlobalID": "A12345678901234567890",
            "CanonicalLatin": "Euler, Leonhard",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
        {
            "GlobalID": "B12345678901234567890",
            "CanonicalLatin": "Noether, Emmy",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
    ]
    curr_batch = [
        {
            "GlobalID": "A12345678901234567890",
            "CanonicalLatin": "Euler, Leonhard",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
        {
            "GlobalID": "B12345678901234567890",
            "CanonicalLatin": "Noether, Emmy N.",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
        {
            "GlobalID": "C12345678901234567890",
            "CanonicalLatin": "Poincaré, Henri",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
    ]

    prev_dir = write_snapshot(prev_batch, out_root="out/yaml", run_hash="prevdemo")
    curr_dir = write_snapshot(curr_batch, out_root="out/yaml", run_hash="currdemo")

    # Diff
    summary = diff_snapshots(prev_dir, curr_dir)
    sql = generate_sql_changelog(prev_dir, curr_dir)
    print("Prev:", prev_dir)
    print("Curr:", curr_dir)
    print("Summary:", json.dumps(summary))
    print("Changelog:", sql)
