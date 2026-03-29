import os, json, pathlib
from src.pipeline.stage9_write_and_diff import (
    write_snapshot,
    diff_snapshots,
    generate_sql_changelog,
)


def test_write_and_diff(tmp_path):
    prev_batch = [
        {
            "GlobalID": "AAAAAAAAAAAAAAAAAAAAAA"[:22],
            "CanonicalLatin": "Euler, Leonhard",
            "Field": "Mathematics",
            "Source": "M",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
        {
            "GlobalID": "BBBBBBBBBBBBBBBBBBBBBB"[:22],
            "CanonicalLatin": "Noether, Emmy",
            "Field": "Mathematics",
            "Source": "M",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
    ]
    curr_batch = [
        {
            "GlobalID": "AAAAAAAAAAAAAAAAAAAAAA"[:22],
            "CanonicalLatin": "Euler, Leonhard",
            "Field": "Mathematics",
            "Source": "M",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
        {
            "GlobalID": "BBBBBBBBBBBBBBBBBBBBBB"[:22],
            "CanonicalLatin": "Noether, Emmy N.",
            "Field": "Mathematics",
            "Source": "M",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
        {
            "GlobalID": "CCCCCCCCCCCCCCCCCCCCCC"[:22],
            "CanonicalLatin": "Poincaré, Henri",
            "Field": "Mathematics",
            "Source": "M",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        },
    ]
    out_root = tmp_path / "out"
    prev_dir = write_snapshot(prev_batch, out_root=str(out_root), run_hash="prev")
    curr_dir = write_snapshot(curr_batch, out_root=str(out_root), run_hash="curr")
    summary = diff_snapshots(prev_dir, curr_dir)
    assert (
        summary["added"] == 1 and summary["modified"] == 1 and summary["removed"] == 0
    )
    sql = generate_sql_changelog(prev_dir, curr_dir)
    assert os.path.exists(sql)
    with open(sql, "r", encoding="utf-8") as f:
        content = f.read()
        assert "INSERT INTO gmnap_changelog" in content
