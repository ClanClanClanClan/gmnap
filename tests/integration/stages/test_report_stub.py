import pytest

import os, json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage10_report import generate_report


@pytest.mark.timeout(15)
def test_report(tmp_path):
    batch = [{"GlobalID": "X", "Source": "Manual", "CanonicalLatin": "Euler, Leonhard"}]
    out_dir = tmp_path / "reports"
    rep_dir, payload = generate_report(
        batch,
        metrics={"coherence": 0.9},
        shortform_clusters={"L. Euler": 3},
        snapshot_dir="snapshots/run-deadbeef",
        out_dir=str(out_dir),
        templates_dir="templates",
    )
    assert os.path.isdir(rep_dir)
    with open(os.path.join(rep_dir, "report.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["entries"] == 1
