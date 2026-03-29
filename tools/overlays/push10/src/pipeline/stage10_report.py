from __future__ import annotations
import os, json, pathlib, hashlib, datetime
from collections import Counter
from typing import Dict, Any, List, Tuple
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jsonschema import Draft202012Validator

from ..ops.spec_loader import load_specs
from ..ops.metrics import REPORTS_EMITTED, DOI_DRAFTS_CREATED
from ..ops.archive import archive_snapshot
from ..ops.attribution import generate_attribution_text


def _sha256(p: pathlib.Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_name(s: str) -> str:
    return "".join(ch for ch in s if ch.isalnum() or ch in "-_., ").strip()


def _run_hash_from_snapshot(snapshot_dir: str) -> str:
    b = os.path.basename(snapshot_dir)
    if b.startswith("run-"):
        return b.split("run-")[-1]
    return hashlib.sha256(snapshot_dir.encode()).hexdigest()[:16]


def _count_regions(batch: List[Dict[str, Any]]) -> Dict[str, int]:
    c = Counter()
    for e in batch:
        r = e.get("DetectedRegion") or "R0"
        c[r] += 1
    return dict(sorted(c.items()))


def _list_authorities(batch: List[Dict[str, Any]]) -> Dict[str, int]:
    c = Counter()
    for e in batch:
        # collect explicit _sources (from enrichment) or Source
        srcs = e.get("_sources") or [e.get("Source", "Unknown")]
        for s in srcs:
            if s:
                c[s] += 1
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


def _quality_gate_eval(
    specs: Dict[str, Any], metrics: Dict[str, Any], mode: str
) -> Dict[str, Any]:
    gates = specs.get("quality_gates", {}) or {}
    mode = mode or "Quick"
    out = {}
    # Graph coherence
    min_coh = gates.get("graph_coherence_score_min", {}).get(
        (
            mode.lower()
            if isinstance(gates.get("graph_coherence_score_min"), dict)
            else None
        ),
        None,
    )
    if isinstance(gates.get("graph_coherence_score_min"), dict):
        min_coh = gates["graph_coherence_score_min"].get(mode.lower(), None) or gates[
            "graph_coherence_score_min"
        ].get(mode, None)
    if min_coh is None:
        min_coh = (
            gates.get("graph_coherence_score_min", 0.85)
            if isinstance(gates.get("graph_coherence_score_min"), (int, float))
            else 0.85
        )
    coh = float(metrics.get("graph_coherence", metrics.get("coherence", 0.0)))
    out["graph_coherence"] = {
        "value": coh,
        "min": float(min_coh),
        "pass": coh >= float(min_coh),
    }
    # Round-trip rate
    rrt_min = float(gates.get("roundtrip_script_rate_min", 0.97))
    rrt = float(
        metrics.get("roundtrip_script_rate", metrics.get("cjk_roundtrip_rate", 1.0))
    )
    out["roundtrip_script_rate"] = {
        "value": rrt,
        "min": rrt_min,
        "pass": rrt >= rrt_min,
    }
    # Idempotent diff bytes
    idem_max = int(gates.get("idempotent_diff_bytes_max", 0))
    diff_bytes = int(metrics.get("idempotent_diff_bytes", 0))
    out["idempotent_diff_bytes"] = {
        "value": diff_bytes,
        "max": idem_max,
        "pass": diff_bytes <= idem_max,
    }
    return out


def _load_datacite_schema(schema_dir: str) -> Dict[str, Any]:
    path = pathlib.Path(schema_dir) / "datacite_draft.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _render_markdown(template_dir: str, context: Dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(template_dir), autoescape=select_autoescape()
    )
    return env.get_template("report.md.j2").render(**context)


def _build_doi_draft(
    specs: Dict[str, Any], run_hash: str, snapshot_dir: str, batch: List[Dict[str, Any]]
) -> Dict[str, Any]:
    shoulder = (specs.get("doi_minting") or {}).get(
        "shoulder"
    ) or "10.3929/ethz-lineage"
    now = datetime.datetime.utcnow()
    creators = [
        {
            "nameType": "Organizational",
            "name": "ETH Zürich — Global Name Authority Project (MathLineage)",
        }
    ]
    titles = [
        {"title": f"MathLineage snapshot {now.date().isoformat()} (run {run_hash})"}
    ]
    related = [
        {
            "relationType": "IsIdenticalTo",
            "relationTypeGeneral": "Dataset",
            "relatedIdentifierType": "URL",
            "relatedIdentifier": f"file://{os.path.abspath(snapshot_dir)}/entries.json",
        }
    ]
    return {
        "doi": f"{shoulder}/{run_hash}",
        "creators": creators,
        "titles": titles,
        "publisher": "ETH Zürich",
        "publicationYear": now.year,
        "types": {
            "resourceTypeGeneral": "Dataset",
            "resourceType": "Authority snapshot",
        },
        "descriptions": [
            {
                "descriptionType": "Abstract",
                "description": "Snapshot of mathematician authority records and genealogy edges produced by the GMNAP V7 pipeline.",
            }
        ],
        "schemaVersion": "http://datacite.org/schema/kernel-4",
        "relatedIdentifiers": related,
        "rightsList": [
            {
                "rights": "CC0 1.0 Universal",
                "rightsUri": "https://creativecommons.org/publicdomain/zero/1.0/",
            }
        ],
    }


def _write_archive_manifest(snapshot_dir: str) -> Dict[str, Any]:
    p = pathlib.Path(snapshot_dir)
    files = {}
    for name in ["entries.yaml", "entries.json", "diff.html", "changelog.cypher"]:
        f = p / name
        if f.exists():
            files[name] = {"sha256": _sha256(f), "bytes": f.stat().st_size}
    manifest = {
        "snapshot": os.path.basename(snapshot_dir),
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "files": files,
    }
    (p / "archive_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def generate_report(
    batch: List[Dict[str, Any]],
    metrics: Dict[str, Any] | None = None,
    snapshot_dir: str | None = None,
    shortform_clusters: Dict[str, int] | None = None,
    mode: str = "Quick",
    templates_dir: str = "templates",
    schema_dir: str = "schemas",
    archive_method: str | None = None,
    archive_target: str | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Stage 10: Generate Markdown report, DOI draft, archive snapshot, and attribution file.
    Returns (report_dir, payload_json)
    """
    specs = load_specs()
    batch = batch or []
    metrics = metrics or {}
    shortform_clusters = shortform_clusters or {}

    # Resolve snapshot and run hash
    snapshot_dir = snapshot_dir or "snapshots/latest"
    run_hash = _run_hash_from_snapshot(snapshot_dir)

    # Compute aggregates
    regions = _count_regions(batch)
    authorities = _list_authorities(batch)
    gates = _quality_gate_eval(specs, metrics, mode)

    # Archive manifest + attribution
    archive_manifest = _write_archive_manifest(snapshot_dir)
    attribution_text = generate_attribution_text()
    pathlib.Path(snapshot_dir, "ATTRIBUTION.txt").write_text(
        attribution_text, encoding="utf-8"
    )

    # DOI draft
    doi_draft = _build_doi_draft(specs, run_hash, snapshot_dir, batch)
    schema = _load_datacite_schema(schema_dir)
    Draft202012Validator(schema).validate(doi_draft)
    doi_path = pathlib.Path(snapshot_dir) / "doi_draft.json"
    doi_path.write_text(
        json.dumps(doi_draft, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    DOI_DRAFTS_CREATED.inc()

    # Markdown report
    context = {
        "run_hash": run_hash,
        "date_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "counts": {"entries": len(batch), "regions": len(regions)},
        "metrics": metrics,
        "regions": regions,
        "authorities": authorities,
        "gates": gates,
        "snapshot_dir": snapshot_dir,
        "shortform_top": sorted(
            shortform_clusters.items(), key=lambda kv: (-kv[1], kv[0])
        )[:25],
    }
    md = _render_markdown(templates_dir, context)
    report_path = pathlib.Path(snapshot_dir) / "report.md"
    report_path.write_text(md, encoding="utf-8")
    REPORTS_EMITTED.inc()

    # Optional: archive snapshot
    archive_cfg = specs.get("archive") or {}
    provider = (archive_cfg.get("provider") or "").lower()
    default_method = (
        "sftp"
        if (
            archive_cfg.get("protocol", "").lower() == "sftp"
            or provider.find("archive") >= 0
        )
        else "local_zip"
    )
    method = archive_method or default_method
    archived = archive_snapshot(
        snapshot_dir,
        target_dir=archive_target or archive_cfg.get("path"),
        method=method,
    )

    payload = {
        "run_hash": run_hash,
        "snapshot_dir": snapshot_dir,
        "report_md": str(report_path),
        "doi_draft": str(doi_path),
        "archived_artifact": archived,
        "archive_manifest": archive_manifest,
        "gates": gates,
        "metrics": metrics,
        "regions": regions,
        "authorities": authorities,
    }
    json_path = pathlib.Path(snapshot_dir) / "report.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Return directory (snapshot) and the payload
    return snapshot_dir, payload
