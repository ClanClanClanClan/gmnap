from __future__ import annotations

import datetime
import hashlib
import json
import os
import pathlib
from typing import Any, Dict, List, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..ops.diff_utils import compute_entry_diffs
from ..ops.metrics import WRITE_DIFF_CHANGED_ENTRIES
from ..ops.yaml_deterministic import canonicalise_entry, dump_yaml_deterministic


def _batch_hash(batch: List[Dict]) -> str:
    ordered = sorted(
        [canonicalise_entry(e) for e in batch],
        key=lambda e: (e.get("GlobalID", ""), e.get("Source", "")),
    )
    payload = json.dumps(ordered, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _load_prev_snapshot_dir(out_base: str) -> str | None:
    idx = pathlib.Path(out_base) / "SNAPSHOT_INDEX.json"
    if idx.exists():
        try:
            data = json.loads(idx.read_text(encoding="utf-8"))
            return data.get("latest")
        except Exception:
            return None
    return None


def _update_snapshot_index(out_base: str, new_dir: str) -> None:
    idx = pathlib.Path(out_base) / "SNAPSHOT_INDEX.json"
    payload = {"latest": new_dir}
    idx.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_dir(p: str) -> pathlib.Path:
    path = pathlib.Path(p)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_yaml_and_json(dir_path: pathlib.Path, batch: List[Dict]) -> Tuple[str, str]:
    entries = [canonicalise_entry(e) for e in batch]
    yaml_text = dump_yaml_deterministic(entries)
    yaml_path = dir_path / "entries.yaml"
    yaml_path.write_text(yaml_text, encoding="utf-8")
    json_path = dir_path / "entries.json"
    json_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Return file paths
    return str(yaml_path), str(json_path)


def _load_entries_if_exists(path: str) -> List[Dict]:
    p = pathlib.Path(path)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _render_html_diff(
    template_dir: str,
    out_dir: pathlib.Path,
    diff_payload: Dict[str, Any],
    run_hash: str,
) -> str:
    env = Environment(
        loader=FileSystemLoader(template_dir), autoescape=select_autoescape()
    )
    html = env.get_template("diff.html.j2").render(
        diff=diff_payload,
        run_hash=run_hash,
        generated_utc=datetime.datetime.utcnow().isoformat() + "Z",
    )
    path = out_dir / "diff.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def _generate_sql_changelog(
    out_dir: pathlib.Path, diff: Dict[str, Any], new_entries: List[Dict]
) -> str:
    """Produce a Cypher changelog with MERGE/SET and optional deletes (disabled by default)."""
    lines: List[str] = []
    lines.append("// GMNAP Stage 9 SQL changelog (Cypher)")
    lines.append("BEGIN;")

    # Added
    idx_new = {e.get("GlobalID"): e for e in new_entries}
    for gid in diff["added_ids"]:
        e = idx_new.get(gid) or {}
        name = e.get("CanonicalLatin", "").replace('"', '\\"')
        lines.append(f'MERGE (m:Mathematician {{global_id: "{gid}"}})')
        lines.append(
            f'  ON CREATE SET m.name = "{name}", m.source = "{e.get("Source","")}", m.last_updated = "{e.get("LastUpdated","")}"'
        )
        lines.append(";")

    # Changed: set properties (basic scalar props only to avoid exploding SETs)
    scalar_props = [
        "CanonicalLatin",
        "CanonicalNative",
        "BirthYear",
        "DeathYear",
        "Field",
        "Source",
        "LastUpdated",
        "ValidationStatus",
    ]
    for gid, d in (diff.get("changed") or {}).items():
        sets = []
        idx_new.get(gid, {})
        for k, v in (d.get("changed") or {}).items():
            if k in scalar_props:
                val = v["to"]
                if isinstance(val, str):
                    sval = val.replace('"', '\\"')
                    sets.append(f'm.{k} = "{sval}"')
                else:
                    sets.append(f"m.{k} = {json.dumps(val)}")
        if sets:
            lines.append(f'MATCH (m:Mathematician {{global_id: "{gid}"}})')
            lines.append("SET " + ", ".join(sets))
            lines.append(";")

    # Removed (left commented out by default)
    for gid in diff["removed_ids"]:
        lines.append(
            f'// MATCH (m:Mathematician {{global_id: "{gid}"}}) DETACH DELETE m;'
        )

    lines.append("COMMIT;")
    sql_path = out_dir / "changelog.cypher"
    sql_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(sql_path)


def write_and_diff(
    batch: List[Dict],
    out_base: str = "snapshots",
    templates_dir: str = "templates",
    previous_snapshot_dir: str | None = None,
) -> Tuple[List[Dict], Dict[str, float], str]:
    """
    Stage 9: Deterministic YAML snapshot; diff with previous snapshot; HTML diff; SQL changelog.
    Returns (batch, metrics, snapshot_dir).
    """
    run_hash = _batch_hash(batch)
    snapshot_dir = os.path.join(out_base, f"run-{run_hash}")
    out_dir = _ensure_dir(snapshot_dir)

    # 1) Write deterministic YAML/JSON for this run
    yaml_path, json_path = _write_yaml_and_json(out_dir, batch)

    # 2) Locate previous snapshot
    prev_dir = previous_snapshot_dir or _load_prev_snapshot_dir(out_base)
    prev_json = os.path.join(prev_dir, "entries.json") if prev_dir else None
    prev_entries = _load_entries_if_exists(prev_json) if prev_json else []

    # 3) Compute diff
    new_entries = [canonicalise_entry(e) for e in batch]
    diff_payload = compute_entry_diffs(prev_entries, new_entries)

    # 4) Render diff HTML and SQL changelog
    _render_html_diff(templates_dir, out_dir, diff_payload, run_hash)
    _generate_sql_changelog(out_dir, diff_payload, new_entries)

    # 5) Update metrics and index pointer
    WRITE_DIFF_CHANGED_ENTRIES.set(diff_payload["changed_entries_count"])
    _update_snapshot_index(out_base, snapshot_dir)

    metrics = {
        "changed_entries": float(diff_payload["changed_entries_count"]),
        "added": float(len(diff_payload["added_ids"])),
        "removed": float(len(diff_payload["removed_ids"])),
    }
    return batch, metrics, snapshot_dir
