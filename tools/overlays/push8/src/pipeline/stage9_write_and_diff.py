from __future__ import annotations

import datetime
import difflib
import hashlib
import json
import os
import pathlib
import shutil
import unicodedata
from typing import Dict, List, Tuple

from ruamel.yaml import YAML

from ..ops.metrics_ext import (
    WRITE_DIFF_ADDED,
    WRITE_DIFF_LATEST,
    WRITE_DIFF_MODIFIED,
    WRITE_DIFF_REMOVED,
)
from .stage10_report import _batch_hash  # reuse deterministic hasher

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


def _yaml() -> YAML:
    y = YAML()
    y.default_flow_style = False
    y.indent(sequence=2, offset=2)
    y.allow_unicode = True
    y.preserve_quotes = True
    y.width = 4096
    return y


def _safe_filename(global_id: str) -> str:
    # GlobalID per spec is Base32 (A-Z2-7) + optional '--N'. Keep as is.
    return f"{global_id}.yaml"


def _order_entry(e: Dict) -> Dict:
    # Sort nested structures deterministically
    def sort_list(xs):
        try:
            return sorted(
                xs, key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=True)
            )
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


def write_snapshot(
    batch: List[Dict], out_root: str = "out/yaml", run_hash: str | None = None
) -> str:
    """
    Writes a deterministic YAML snapshot: one file per entry `<GlobalID>.yaml` under `out/yaml/run-<hash>/`.
    Returns the snapshot directory path.
    """
    run_hash = run_hash or _batch_hash(batch)
    snap_dir = pathlib.Path(out_root) / f"run-{run_hash}"
    snap_dir.mkdir(parents=True, exist_ok=True)
    y = _yaml()

    # Write manifest
    manifest = {
        "run_hash": run_hash,
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "count": len(batch),
        "schema_version": "7.0",
    }
    with open(snap_dir / "MANIFEST.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    for e in batch:
        gid = e.get("GlobalID")
        if not gid:
            raise ValueError("Entry missing GlobalID during snapshot write")
        clean = _order_entry(_scrub(dict(e)))
        fp = snap_dir / _safe_filename(gid)
        with open(fp, "w", encoding="utf-8") as f:
            y.dump(clean, f)
    return str(snap_dir)


def _read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _diff_texts(a: str, b: str, fromdesc: str, todesc: str) -> str:
    d = difflib.HtmlDiff(tabsize=2, wrapcolumn=120)
    return d.make_file(a.splitlines(), b.splitlines(), fromdesc=fromdesc, todesc=todesc)


def diff_snapshots(
    prev_dir: str, curr_dir: str, out_dir: str | None = None
) -> Dict[str, int]:
    """
    Diffs two snapshot directories and writes an HTML report with per-file diffs.
    Returns counts dict: {"added": X, "removed": Y, "modified": Z}.
    """
    prev = pathlib.Path(prev_dir)
    curr = pathlib.Path(curr_dir)
    out_dir = pathlib.Path(out_dir or (curr / "diff"))
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    prev_files = {p.name for p in prev.glob("*.yaml")}
    curr_files = {p.name for p in curr.glob("*.yaml")}

    added = sorted(list(curr_files - prev_files))
    removed = sorted(list(prev_files - curr_files))
    common = sorted(list(prev_files & curr_files))

    modified = []
    for name in common:
        a = _read_text(prev / name)
        b = _read_text(curr / name)
        if a != b:
            modified.append(name)
            html = _diff_texts(a, b, fromdesc=f"prev/{name}", todesc=f"curr/{name}")
            (out_dir / f"{name}.html").write_text(html, encoding="utf-8")

    # Index report
    index = [
        "<html><head><meta charset='utf-8'><title>Write&Diff Report</title></head><body>"
    ]
    index.append("<h1>Write&amp;Diff Report</h1>")
    index.append(f"<p><b>Prev:</b> {prev}</p><p><b>Curr:</b> {curr}</p>")
    index.append("<h2>Summary</h2>")
    index.append(
        f"<ul><li>Added: {len(added)}</li><li>Removed: {len(removed)}</li><li>Modified: {len(modified)}</li></ul>"
    )
    if modified:
        index.append("<h2>Modified</h2><ul>")
        for n in modified:
            index.append(f"<li><a href='{n}.html'>{n}</a></li>")
        index.append("</ul>")
    if added:
        index.append(
            "<h2>Added</h2><ul>" + "".join(f"<li>{n}</li>" for n in added) + "</ul>"
        )
    if removed:
        index.append(
            "<h2>Removed</h2><ul>" + "".join(f"<li>{n}</li>" for n in removed) + "</ul>"
        )
    index.append("</body></html>")
    (out_dir / "index.html").write_text("\n".join(index), encoding="utf-8")

    # Metrics
    WRITE_DIFF_ADDED.inc(len(added))
    WRITE_DIFF_REMOVED.inc(len(removed))
    WRITE_DIFF_MODIFIED.inc(len(modified))
    WRITE_DIFF_LATEST.set(len(added) + len(removed) + len(modified))

    summary = {"added": len(added), "removed": len(removed), "modified": len(modified)}
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary


def generate_sql_changelog(
    prev_snapshot: str, curr_snapshot: str, out_path: str | None = None
) -> str:
    """
    Emits a deterministic SQL changelog for a simple audit table 'gmnap_changelog'.
    Operations: INSERT (new), UPDATE (modified), DELETE (removed) based on file-level changes.
    """
    prev = pathlib.Path(prev_snapshot)
    curr = pathlib.Path(curr_snapshot)
    out_path = out_path or str(curr / "diff" / "changelog.sql")
    sql_lines = [
        "-- GMNAP Stage 9 SQL changelog",
        "CREATE TABLE IF NOT EXISTS gmnap_changelog (ts TEXT, op TEXT, global_id TEXT, details TEXT);",
    ]

    def _load_yaml(p: pathlib.Path) -> Dict:
        if not p.exists():
            return {}
        from ruamel.yaml import YAML

        y = YAML(typ="safe")
        with open(p, "r", encoding="utf-8") as f:
            return y.load(f) or {}

    prev_files = {p.name for p in prev.glob("*.yaml")}
    curr_files = {p.name for p in curr.glob("*.yaml")}

    added = sorted(list(curr_files - prev_files))
    removed = sorted(list(prev_files - curr_files))
    common = sorted(list(prev_files & curr_files))

    utc = datetime.datetime.utcnow().isoformat() + "Z"

    for name in added:
        gid = name[:-5]
        data = _load_yaml(curr / name)
        details = json.dumps({"new": data}, ensure_ascii=False).replace("'", "''")
        sql_lines.append(
            f"INSERT INTO gmnap_changelog(ts,op,global_id,details) VALUES('{utc}','INSERT','{gid}','{details}');"
        )

    for name in removed:
        gid = name[:-5]
        details = json.dumps({"removed": True}, ensure_ascii=False).replace("'", "''")
        sql_lines.append(
            f"INSERT INTO gmnap_changelog(ts,op,global_id,details) VALUES('{utc}','DELETE','{gid}','{details}');"
        )

    for name in common:
        a = _load_yaml(prev / name)
        b = _load_yaml(curr / name)
        if a != b:
            gid = name[:-5]
            details = json.dumps({"from": a, "to": b}, ensure_ascii=False).replace(
                "'", "''"
            )
            sql_lines.append(
                f"INSERT INTO gmnap_changelog(ts,op,global_id,details) VALUES('{utc}','UPDATE','{gid}','{details}');"
            )

    out_file = pathlib.Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(sql_lines) + "\n", encoding="utf-8")
    return str(out_file)
