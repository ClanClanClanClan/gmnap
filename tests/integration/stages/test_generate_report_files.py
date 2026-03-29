import pytest

import os, json, shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage9_write_and_diff import write_and_diff
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage10_report import generate_report


@pytest.mark.timeout(15)
def test_generate_report_produces_files(tmp_path, monkeypatch):
    base = tmp_path / "snapshots"
    base.mkdir(parents=True, exist_ok=True)
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
    # Stage 9 first
    _, m9, sdir = write_and_diff(batch, out_base=str(base), templates_dir="templates")
    # Stage 10 hardened
    report_dir, payload = generate_report(
        batch,
        metrics=m9,
        snapshot_dir=sdir,
        shortform_clusters={"E. Noether": 2},
        specs={
            "doi_minting": {"shoulder": "10.3929/ethz-lineage"},
            "authority_sources": [{"tier": 0, "service": "OpenAlex", "licence": "CC0"}],
        },
    )
    assert os.path.isfile(os.path.join(report_dir, "REPORT.md"))
    assert os.path.isfile(os.path.join(report_dir, "datacite_draft.json"))
    assert os.path.isfile(os.path.join(report_dir, "ATTRIBUTION.txt"))
    assert os.path.isfile(os.path.join(report_dir, "CHECKSUMS.sha256"))
    # DOI string present
    doi = (
        open(os.path.join(report_dir, "DOI.txt"), "r", encoding="utf-8").read().strip()
    )
    assert doi.startswith("10.3929/ethz-lineage/")
    # datacite payload parsable
    with open(
        os.path.join(report_dir, "datacite_draft.json"), "r", encoding="utf-8"
    ) as f:
        data = json.load(f)
    assert data["data"]["attributes"]["event"] == "draft"
