"""Stage 9: Write&Diff - Deterministic YAML snapshot, HTML diff, SQL changelog."""

from __future__ import annotations
import json
import pathlib
import hashlib
import datetime
import difflib
import shutil
import unicodedata
from typing import Dict, List
from src.ops.metrics_ext import (
    WRITE_DIFF_ADDED,
    WRITE_DIFF_REMOVED,
    WRITE_DIFF_MODIFIED,
    WRITE_DIFF_LATEST,
)

_VOLATILE_KEYS = {"ProcessedAt", "ProcessingLatencyMs", "_debug", "_trace_id", "_meta"}


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _scrub(entry: Dict) -> Dict:
    """Remove volatile keys and NFC-normalise strings (shallow)."""
    out = {}
    for k, v in entry.items():
        if k in _VOLATILE_KEYS:
            continue
        if isinstance(v, str):
            out[k] = _nfc(v)
        else:
            out[k] = v
    return out


def _order_entry(e: Dict) -> Dict:
    """Sort nested structures deterministically."""

    def sort_list(xs):
        try:
            return sorted(xs, key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=True))
        except Exception:
            return xs

    out = {}
    for k in sorted(e.keys()):
        v = e[k]
        if isinstance(v, list):
            out[k] = sort_list(v)
        elif isinstance(v, dict):
            out[k] = {kk: v[kk] for kk in sorted(v.keys())}
        else:
            out[k] = v
    return out


def _batch_hash(batch: List[Dict], pre_canonical: bool = False) -> str:
    """Deterministic hash for a batch (streaming — no giant JSON string)."""
    h = hashlib.sha256()
    for e in sorted(batch, key=lambda x: x.get("GlobalID", "")):
        entry = e if pre_canonical else _order_entry(_scrub(dict(e)))
        h.update(
            json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        )
    return h.hexdigest()[:16]


def _safe_filename(global_id: str) -> str:
    return f"{global_id}.yaml"


def _write_yaml_file(data: Dict, path: pathlib.Path):
    """Write a single YAML entry file."""
    try:
        from ruamel.yaml import YAML

        y = YAML()
        y.default_flow_style = False
        y.indent(sequence=2, offset=2)
        y.allow_unicode = True
        y.preserve_quotes = True
        y.width = 4096
        with open(path, "w", encoding="utf-8") as f:
            y.dump(data, f)
    except ImportError:
        import yaml

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=True)


_YAML_FILE_THRESHOLD = 10_000  # Skip per-entry YAML files above this count


def write_snapshot(
    batch: List[Dict],
    out_root: str = "out/yaml",
    run_hash: str | None = None,
    pre_canonical: bool = False,
) -> str:
    """
    Write a deterministic YAML snapshot: one file per entry under out/yaml/run-<hash>/.
    For batches > 10K entries, skips individual YAML files (writes only entries.json).
    Returns the snapshot directory path.
    """
    run_hash = run_hash or _batch_hash(batch, pre_canonical=pre_canonical)
    snap_dir = pathlib.Path(out_root) / f"run-{run_hash}"
    snap_dir.mkdir(parents=True, exist_ok=True)

    # Write manifest
    manifest = {
        "run_hash": run_hash,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "count": len(batch),
        "schema_version": "7.0",
    }
    with open(snap_dir / "MANIFEST.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Prepare canonical entries (reuse if pre-canonicalised)
    if pre_canonical:
        all_entries = batch
    else:
        all_entries = [_order_entry(_scrub(dict(e))) for e in batch]

    # Write individual YAML files only for small batches
    if len(batch) <= _YAML_FILE_THRESHOLD:
        for e in all_entries:
            gid = e.get("GlobalID")
            if not gid:
                continue
            _write_yaml_file(e, snap_dir / _safe_filename(gid))

    # Write combined entries.json (streaming for large batches)
    with open(snap_dir / "entries.json", "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2, sort_keys=True)

    # Update snapshot index
    idx_path = pathlib.Path(out_root) / "SNAPSHOT_INDEX.json"
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx = {
        "latest": str(snap_dir),
        "run_hash": run_hash,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)

    return str(snap_dir)


def diff_snapshots(prev_dir: str, curr_dir: str, out_dir: str | None = None) -> Dict[str, int]:
    """Diff two snapshot directories and write HTML report with per-file diffs."""
    prev = pathlib.Path(prev_dir)
    curr = pathlib.Path(curr_dir)
    out_dir_p = pathlib.Path(out_dir or (str(curr) + "/diff"))
    if out_dir_p.exists():
        shutil.rmtree(out_dir_p)
    out_dir_p.mkdir(parents=True, exist_ok=True)

    prev_files = {p.name for p in prev.glob("*.yaml")}
    curr_files = {p.name for p in curr.glob("*.yaml")}

    added = sorted(list(curr_files - prev_files))
    removed = sorted(list(prev_files - curr_files))
    common = sorted(list(prev_files & curr_files))

    modified = []
    for name in common:
        a = (prev / name).read_text(encoding="utf-8") if (prev / name).exists() else ""
        b = (curr / name).read_text(encoding="utf-8") if (curr / name).exists() else ""
        if a != b:
            modified.append(name)
            d = difflib.HtmlDiff(tabsize=2, wrapcolumn=120)
            html = d.make_file(
                a.splitlines(), b.splitlines(), fromdesc=f"prev/{name}", todesc=f"curr/{name}"
            )
            (out_dir_p / f"{name}.html").write_text(html, encoding="utf-8")

    # Write index HTML
    index = ["<html><head><meta charset='utf-8'><title>Write&Diff Report</title></head><body>"]
    index.append("<h1>Write&amp;Diff Report</h1>")
    index.append(f"<p><b>Prev:</b> {prev}</p><p><b>Curr:</b> {curr}</p>")
    index.append("<h2>Summary</h2>")
    index.append(
        f"<ul><li>Added: {len(added)}</li><li>Removed: {len(removed)}</li>"
        f"<li>Modified: {len(modified)}</li></ul>"
    )
    if modified:
        index.append("<h2>Modified</h2><ul>")
        for n in modified:
            index.append(f"<li><a href='{n}.html'>{n}</a></li>")
        index.append("</ul>")
    if added:
        index.append("<h2>Added</h2><ul>" + "".join(f"<li>{n}</li>" for n in added) + "</ul>")
    if removed:
        index.append("<h2>Removed</h2><ul>" + "".join(f"<li>{n}</li>" for n in removed) + "</ul>")
    index.append("</body></html>")
    (out_dir_p / "index.html").write_text("\n".join(index), encoding="utf-8")

    WRITE_DIFF_ADDED.inc(len(added))
    WRITE_DIFF_REMOVED.inc(len(removed))
    WRITE_DIFF_MODIFIED.inc(len(modified))
    WRITE_DIFF_LATEST.set(len(added) + len(removed) + len(modified))

    summary = {"added": len(added), "removed": len(removed), "modified": len(modified)}
    with open(out_dir_p / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary


def generate_sql_changelog(
    prev_snapshot: str, curr_snapshot: str, out_path: str | None = None
) -> str:
    """Emit deterministic SQL changelog for audit table."""
    prev = pathlib.Path(prev_snapshot)
    curr = pathlib.Path(curr_snapshot)
    out_path = out_path or str(curr / "diff" / "changelog.sql")
    sql_lines = [
        "-- GMNAP Stage 9 SQL changelog",
        "CREATE TABLE IF NOT EXISTS gmnap_changelog (ts TEXT, op TEXT, global_id TEXT, details TEXT);",
    ]

    prev_files = {p.name for p in prev.glob("*.yaml")} if prev.exists() else set()
    curr_files = {p.name for p in curr.glob("*.yaml")}

    added = sorted(list(curr_files - prev_files))
    removed = sorted(list(prev_files - curr_files))
    common = sorted(list(prev_files & curr_files))
    utc = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    for name in added:
        gid = name[:-5]
        sql_lines.append(
            f"INSERT INTO gmnap_changelog(ts,op,global_id,details) "
            f"VALUES('{utc}','INSERT','{gid}','new entry');"
        )

    for name in removed:
        gid = name[:-5]
        sql_lines.append(
            f"INSERT INTO gmnap_changelog(ts,op,global_id,details) "
            f"VALUES('{utc}','DELETE','{gid}','removed');"
        )

    for name in common:
        a = (prev / name).read_text(encoding="utf-8") if (prev / name).exists() else ""
        b = (curr / name).read_text(encoding="utf-8") if (curr / name).exists() else ""
        if a != b:
            gid = name[:-5]
            sql_lines.append(
                f"INSERT INTO gmnap_changelog(ts,op,global_id,details) "
                f"VALUES('{utc}','UPDATE','{gid}','modified');"
            )

    out_file = pathlib.Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(sql_lines) + "\n", encoding="utf-8")
    return str(out_file)


def generate_cypher_changelog(
    prev_snapshot: str, curr_snapshot: str, out_path: str | None = None
) -> str:
    """Emit deterministic Cypher changelog for graph DB audit."""
    prev = pathlib.Path(prev_snapshot)
    curr = pathlib.Path(curr_snapshot)
    out_path = out_path or str(curr / "diff" / "changelog.cypher")

    prev_files = {p.name for p in prev.glob("*.yaml")} if prev.exists() else set()
    curr_files = {p.name for p in curr.glob("*.yaml")}

    added = sorted(list(curr_files - prev_files))
    removed = sorted(list(prev_files - curr_files))
    common = sorted(list(prev_files & curr_files))
    utc = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    cypher_lines = [
        "// GMNAP Stage 9 Cypher changelog",
        f"// Generated: {utc}",
    ]

    for name in added:
        gid = name[:-5]
        cypher_lines.append(
            f"MERGE (m:Mathematician {{globalId: '{gid}'}}) "
            f"SET m.updatedAt = '{utc}', m._changeType = 'INSERT';"
        )

    for name in removed:
        gid = name[:-5]
        cypher_lines.append(
            f"MATCH (m:Mathematician {{globalId: '{gid}'}}) "
            f"SET m._deletedAt = '{utc}', m._changeType = 'DELETE';"
        )

    for name in common:
        a = (prev / name).read_text(encoding="utf-8") if (prev / name).exists() else ""
        b = (curr / name).read_text(encoding="utf-8") if (curr / name).exists() else ""
        if a != b:
            gid = name[:-5]
            cypher_lines.append(
                f"MATCH (m:Mathematician {{globalId: '{gid}'}}) "
                f"SET m.updatedAt = '{utc}', m._changeType = 'UPDATE';"
            )

    out_file = pathlib.Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(cypher_lines) + "\n", encoding="utf-8")
    return str(out_file)
