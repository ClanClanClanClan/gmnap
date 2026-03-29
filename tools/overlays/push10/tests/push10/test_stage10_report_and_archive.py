import os, json, pathlib
from src.pipeline.stage10_report import generate_report


def test_stage10_writes_report_and_doi(tmp_path):
    snap = tmp_path / "snapshots" / "run-abc123"
    snap.mkdir(parents=True, exist_ok=True)
    batch = [
        {
            "GlobalID": "G1",
            "CanonicalLatin": "Euler, Leonhard",
            "DetectedRegion": "A2",
            "Source": "Manual",
            "_sources": ["OpenAlex"],
        }
    ]
    (snap / "entries.json").write_text(json.dumps(batch), encoding="utf-8")
    rep_dir, payload = generate_report(
        batch,
        metrics={"coherence": 0.9, "roundtrip_script_rate": 0.98, "idempotent_diff_bytes": 0},
        snapshot_dir=str(snap),
        shortform_clusters={"L. Euler": 3},
    )
    assert os.path.exists(os.path.join(rep_dir, "report.md"))
    assert os.path.exists(os.path.join(rep_dir, "report.json"))
    assert os.path.exists(os.path.join(rep_dir, "doi_draft.json"))
    assert os.path.exists(os.path.join(rep_dir, "archive_manifest.json"))
    # Archive exists (local zip by default)
    assert os.path.exists(payload["archived_artifact"])
    # DOI draft basic shape
    doi = json.loads((snap / "doi_draft.json").read_text(encoding="utf-8"))
    assert "doi" in doi and "creators" in doi and "titles" in doi
