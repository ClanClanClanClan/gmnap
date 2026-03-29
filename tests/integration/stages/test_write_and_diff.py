import pytest

import os, json, shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage9_write_and_diff import write_and_diff


@pytest.mark.timeout(15)
def test_write_and_diff_generates_yaml_json_and_diff(tmp_path):
    base = tmp_path / "snapshots"
    (base).mkdir(parents=True, exist_ok=True)
    batch1 = [
        {
            "GlobalID": "X",
            "CanonicalLatin": "Euler, Leonhard",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01T00:00:00Z",
            "ValidationStatus": "verified",
        }
    ]
    out1, m1, dir1 = write_and_diff(
        batch1, out_base=str(base), templates_dir="templates"
    )
    assert os.path.isdir(dir1)
    assert os.path.exists(os.path.join(dir1, "entries.yaml"))
    assert os.path.exists(os.path.join(dir1, "entries.json"))
    assert os.path.exists(os.path.join(dir1, "diff.html"))
    assert os.path.exists(os.path.join(dir1, "changelog.cypher"))
    # run again with a change
    batch2 = [dict(batch1[0], CanonicalLatin="Euler, L.")]
    out2, m2, dir2 = write_and_diff(
        batch2, out_base=str(base), templates_dir="templates"
    )
    assert m2["changed_entries"] >= 1
    assert dir1 != dir2
