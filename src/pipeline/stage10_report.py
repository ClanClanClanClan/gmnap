from __future__ import annotations
import os, json, pathlib, datetime, hashlib, yaml
from typing import Dict, List, Tuple
from jinja2 import Environment, FileSystemLoader, select_autoescape


def _batch_hash(batch: List[Dict]) -> str:
    # Deterministic hash of sorted entries
    def key(e):
        return (e.get("GlobalID", ""), e.get("Source", ""))

    ordered = sorted(batch, key=key)
    payload = json.dumps(ordered, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _load_specs(spec_paths=("specs_v7.yaml", "v7.0.yaml")) -> Dict:
    for p in spec_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def _doi_stub(specs: Dict, title: str, snapshot_rel_path: str) -> Dict:
    meta = (specs or {}).get("doi_minting", {})
    return {
        "provider": meta.get("provider", "ETH‑Bibliothek (DataCite)"),
        "registration_mode": meta.get("registration_mode", "draft"),
        "metadata": {
            "titles": [{"title": title}],
            "publisher": "ETH Zürich",
            "publicationYear": datetime.datetime.utcnow().year,
            "types": {"resourceTypeGeneral": "Dataset"},
            "identifiers": [{"identifierType": "URL", "identifier": snapshot_rel_path}],
            "creators": [{"name": "GMNAP V7 Pipeline"}],
            "container": {"shoulder": meta.get("shoulder", "10.3929/ethz-lineage")},
        },
    }


def generate_report(
    batch: List[Dict],
    metrics: Dict[str, float] | None = None,
    shortform_clusters: Dict[str, int] | None = None,
    snapshot_dir: str | None = None,
    out_dir: str = "reports",
    templates_dir: str = "templates",
) -> Tuple[str, Dict]:
    h = _batch_hash(batch)
    rdir = pathlib.Path(out_dir) / f"run-{h}"
    rdir.mkdir(parents=True, exist_ok=True)
    specs = _load_specs()

    payload = {
        "run_hash": h,
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "entries": len(batch),
        "metrics": metrics or {},
        "shortform_clusters_top10": sorted(
            (shortform_clusters or {}).items(), key=lambda kv: kv[1], reverse=True
        )[:10],
        "snapshot_dir": snapshot_dir,
        "quality_gates": specs.get("quality_gates", {}),
    }
    with open(rdir / "report.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=select_autoescape())
    md = env.get_template("report.md.j2").render(payload=payload)
    with open(rdir / "report.md", "w", encoding="utf-8") as f:
        f.write(md)

    doi_draft = _doi_stub(
        specs, f"GMNAP lineage snapshot {h}", snapshot_dir or f"snapshots/run-{h}"
    )
    with open(rdir / "doi_draft.json", "w", encoding="utf-8") as f:
        json.dump(doi_draft, f, ensure_ascii=False, indent=2)

    # Optional SFTP push left to Stage10 helper in ops (not invoked here).
    return str(rdir), payload
