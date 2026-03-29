#!/usr/bin/env python3
import json, os
from src.pipeline.stage10_report import generate_report

if __name__ == "__main__":
    os.makedirs("snapshots", exist_ok=True)
    # Minimal synthetic batch
    batch = [
        {
            "GlobalID": "X",
            "CanonicalLatin": "Noether, Emmy",
            "DetectedRegion": "A2",
            "Source": "Manual",
            "_sources": ["OpenAlex", "Crossref"],
        },
        {
            "GlobalID": "Y",
            "CanonicalLatin": "Hilbert, David",
            "DetectedRegion": "A2",
            "Source": "Manual",
            "_sources": ["OpenAlex"],
        },
    ]
    metrics = {
        "coherence": 0.91,
        "roundtrip_script_rate": 0.99,
        "idempotent_diff_bytes": 0,
        "changed_entries": 1,
    }
    snapshot_dir = "snapshots/run-demo1234"
    os.makedirs(snapshot_dir, exist_ok=True)
    # ensure entries.json exists to make archive_manifest useful
    with open(os.path.join(snapshot_dir, "entries.json"), "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)

    rep_dir, payload = generate_report(
        batch,
        metrics=metrics,
        snapshot_dir=snapshot_dir,
        shortform_clusters={"E. Noether": 2},
    )
    print(rep_dir)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
