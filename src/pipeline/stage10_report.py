"""Stage 10: Report - Markdown metrics, DOI draft, push snapshot to archive."""

from __future__ import annotations
import os, json, pathlib, hashlib, datetime, logging
from collections import Counter
from typing import Dict, Any, List, Tuple
from src.ops.metrics import REPORTS_EMITTED, DOI_DRAFTS_CREATED
from src.ops.archive import archive_snapshot
from src.ops.attribution import generate_attribution_text

logger = logging.getLogger(__name__)


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
        srcs = e.get("_sources") or [e.get("Source", "Unknown")]
        for s in srcs:
            if s:
                c[s] += 1
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


def _build_doi_draft(
    run_hash: str,
    snapshot_dir: str,
    batch: List[Dict[str, Any]],
    shoulder: str = "10.3929/ethz-lineage",
) -> Dict[str, Any]:
    """Build DataCite DOI draft metadata."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "doi": f"{shoulder}/{run_hash}",
        "creators": [
            {
                "nameType": "Organizational",
                "name": "ETH Zurich - Global Name Authority Project (MathLineage)",
            }
        ],
        "titles": [{"title": f"MathLineage snapshot {now.date().isoformat()} (run {run_hash})"}],
        "publisher": "ETH Zurich",
        "publicationYear": now.year,
        "types": {"resourceTypeGeneral": "Dataset", "resourceType": "Authority snapshot"},
        "descriptions": [
            {
                "descriptionType": "Abstract",
                "description": "Snapshot of mathematician authority records and genealogy edges produced by the GMNAP V7 pipeline.",
            }
        ],
        "schemaVersion": "http://datacite.org/schema/kernel-4",
        "rightsList": [
            {
                "rights": "CC0 1.0 Universal",
                "rightsUri": "https://creativecommons.org/publicdomain/zero/1.0/",
            }
        ],
    }


def _render_markdown_report(context: Dict[str, Any]) -> str:
    """Render a markdown report from context dict."""
    lines = [
        f"# GMNAP V7 Pipeline Report",
        f"",
        f"**Run Hash**: {context['run_hash']}",
        f"**Date**: {context['date_utc']}",
        f"**Mode**: {context.get('mode', 'Quick')}",
        f"",
        f"## Entry Counts",
        f"- Total entries: {context['counts']['entries']}",
        f"- Regions covered: {context['counts']['regions']}",
        f"",
        f"## Performance Metrics",
    ]
    for k, v in context.get("metrics", {}).items():
        lines.append(f"- {k}: {v}")

    lines.append("")
    lines.append("## Region Distribution")
    for r, c in context.get("regions", {}).items():
        lines.append(f"- {r}: {c}")

    lines.append("")
    lines.append("## Authority Sources")
    for s, c in context.get("authorities", {}).items():
        lines.append(f"- {s}: {c}")

    if context.get("gates"):
        lines.append("")
        lines.append("## Quality Gates")
        for gate, result in context["gates"].items():
            status = "PASS" if result.get("pass") else "FAIL"
            lines.append(
                f"- {gate}: {status} (value={result.get('value')}, threshold={result.get('min', result.get('max'))})"
            )

    if context.get("shortform_top"):
        lines.append("")
        lines.append("## Top Short-Form Clusters")
        for sf, count in context["shortform_top"][:25]:
            lines.append(f"- {sf}: {count}")

    return "\n".join(lines) + "\n"


def generate_report(
    batch: List[Dict[str, Any]],
    metrics: Dict[str, Any] | None = None,
    snapshot_dir: str | None = None,
    shortform_clusters: Dict[str, int] | None = None,
    mode: str = "Quick",
) -> Tuple[str, Dict[str, Any]]:
    """
    Stage 10: Generate Markdown report, DOI draft, archive snapshot.
    Returns (report_dir, payload_json).
    """
    batch = batch or []
    metrics = metrics or {}
    shortform_clusters = shortform_clusters or {}

    snapshot_dir = snapshot_dir or "snapshots/latest"
    run_hash = _run_hash_from_snapshot(snapshot_dir)

    regions = _count_regions(batch)
    authorities = _list_authorities(batch)

    # Attribution file
    attribution_text = generate_attribution_text()
    snap_path = pathlib.Path(snapshot_dir)
    snap_path.mkdir(parents=True, exist_ok=True)
    (snap_path / "ATTRIBUTION.txt").write_text(attribution_text, encoding="utf-8")

    # DOI draft
    doi_draft = _build_doi_draft(run_hash, snapshot_dir, batch)
    doi_path = snap_path / "doi_draft.json"
    doi_path.write_text(json.dumps(doi_draft, ensure_ascii=False, indent=2), encoding="utf-8")
    DOI_DRAFTS_CREATED.inc()

    # Markdown report
    context = {
        "run_hash": run_hash,
        "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "counts": {"entries": len(batch), "regions": len(regions)},
        "metrics": metrics,
        "regions": regions,
        "authorities": authorities,
        "mode": mode,
        "shortform_top": sorted(shortform_clusters.items(), key=lambda kv: (-kv[1], kv[0]))[:25],
    }
    md = _render_markdown_report(context)
    report_path = snap_path / "report.md"
    report_path.write_text(md, encoding="utf-8")
    REPORTS_EMITTED.inc()

    # Archive snapshot (SFTP if configured, otherwise local zip)
    archive_method = "sftp" if os.getenv("SFTP_HOST") else "local_zip"
    try:
        archived = archive_snapshot(snapshot_dir, method=archive_method)
        if archive_method == "sftp":
            logger.info(f"Snapshot archived via SFTP: {archived}")
    except Exception as ex:
        logger.warning(f"Archive failed ({archive_method}): {ex}")
        archived = None

    payload = {
        "run_hash": run_hash,
        "snapshot_dir": snapshot_dir,
        "report_md": str(report_path),
        "doi_draft": str(doi_path),
        "archived_artifact": archived,
        "regions": regions,
        "authorities": authorities,
        "metrics": metrics,
    }
    json_path = snap_path / "report.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return snapshot_dir, payload
