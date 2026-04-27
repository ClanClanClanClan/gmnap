from __future__ import annotations

import datetime
import hashlib
import json
import os
import pathlib
from typing import Any, Dict, List, Tuple

# jinja2 is only needed by `_render_html_diff` (the optional HTML
# changelog renderer). The new public APIs (`write_snapshot`,
# `generate_sql_changelog`, `generate_cypher_changelog`) and the
# legacy monolithic `write_and_diff` function don't touch it. Defer
# the import so importing this module on a runtime that doesn't ship
# jinja2 (e.g. CI that only installs the slim runtime requirements)
# stays viable.
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
    # Lazy import — see module-level note. Only this codepath needs jinja2.
    from jinja2 import Environment, FileSystemLoader, select_autoescape

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


# ---------------------------------------------------------------------------
# Public API used by the V7 pipeline + downstream tooling
# ---------------------------------------------------------------------------


def write_snapshot(entries: List[Dict], *, out_root: str) -> str:
    """Write a deterministic snapshot of ``entries`` under
    ``out_root``.

    Layout::

        <out_root>/run-<run_hash>/
            <GlobalID>.yaml         # one per entry, canonicalised
            entries.yaml            # combined deterministic YAML
            entries.json            # combined deterministic JSON
            MANIFEST.json           # {run_hash, count, generated_utc}

    Determinism: ``run_hash`` is derived from
    ``sha256(canonical(entries))[:16]`` so identical inputs always
    produce identical snapshot directory names — round-tripping the
    same batch is a no-op on disk and a no-op for the cross-snapshot
    diff that follows.

    Returns the absolute snapshot directory path.
    """
    run_hash = _batch_hash(entries)
    snap_dir = pathlib.Path(out_root) / f"run-{run_hash}"
    snap_dir.mkdir(parents=True, exist_ok=True)

    canonical = [canonicalise_entry(e) for e in entries]

    # Per-entry YAML — one file per GlobalID (filename-safe).
    for entry in canonical:
        gid = entry.get("GlobalID") or entry.get("global_id") or "unknown"
        # Sanitize: forbid path separators in the filename
        safe = str(gid).replace("/", "_").replace("\\", "_")
        per_entry = snap_dir / f"{safe}.yaml"
        per_entry.write_text(dump_yaml_deterministic([entry]), encoding="utf-8")

    # Combined deterministic JSON for cross-snapshot diffing. We
    # don't write a combined entries.yaml here — the per-entry YAMLs
    # already cover the YAML use case, and a combined version
    # would inflate `*.yaml` glob counts that consumers (and tests)
    # rely on.
    (snap_dir / "entries.json").write_text(
        json.dumps(canonical, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # Manifest. ``generated_utc`` would normally bust determinism
    # for cross-machine reproducibility tests; we use a fixed sentinel
    # when the env var ``SOURCE_DATE_EPOCH`` is set (Reproducible
    # Builds convention) and otherwise the current ISO timestamp. The
    # run_hash itself is invariant either way because it depends only
    # on the entries.
    sde = os.environ.get("SOURCE_DATE_EPOCH")
    if sde:
        try:
            ts = (
                datetime.datetime.fromtimestamp(int(sde), tz=datetime.timezone.utc)
                .replace(tzinfo=None)
                .isoformat()
                + "Z"
            )
        except (ValueError, OSError):
            ts = "1970-01-01T00:00:00Z"
    else:
        ts = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(tzinfo=None)
            .isoformat()
            + "Z"
        )
    manifest = {
        "run_hash": run_hash,
        "count": len(canonical),
        "generated_utc": ts,
    }
    (snap_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return str(snap_dir)


def _diff_snapshots(
    prev_dir: str, curr_dir: str
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Return ``(added, changed, removed)`` lists by comparing the
    ``entries.json`` of two snapshot directories.

    - ``added``: entries whose GlobalID is in curr but not prev
    - ``changed``: entries whose GlobalID is in both but content differs
    - ``removed``: entries whose GlobalID is in prev but not curr
    """
    prev_entries = _load_entries_if_exists(str(pathlib.Path(prev_dir) / "entries.json"))
    curr_entries = _load_entries_if_exists(str(pathlib.Path(curr_dir) / "entries.json"))
    prev_idx = {e.get("GlobalID"): e for e in prev_entries if e.get("GlobalID")}
    curr_idx = {e.get("GlobalID"): e for e in curr_entries if e.get("GlobalID")}
    added = [curr_idx[g] for g in curr_idx if g not in prev_idx]
    removed = [prev_idx[g] for g in prev_idx if g not in curr_idx]
    changed = [
        curr_idx[g] for g in curr_idx if g in prev_idx and curr_idx[g] != prev_idx[g]
    ]
    return added, changed, removed


def _sql_quote(s: Any) -> str:
    """Single-quote-escape a value for SQL embedding."""
    if s is None:
        return "NULL"
    if isinstance(s, (int, float)):
        return repr(s)
    return "'" + str(s).replace("'", "''") + "'"


def generate_sql_changelog(prev_dir: str, curr_dir: str, *, out_path: str) -> str:
    """Emit a SQL changelog (INSERT for added, UPDATE for changed,
    DELETE for removed) at ``out_path``. Returns the path.
    """
    added, changed, removed = _diff_snapshots(prev_dir, curr_dir)
    lines: List[str] = ["-- GMNAP Stage 9 SQL changelog", "BEGIN;"]

    columns = ("GlobalID", "CanonicalLatin", "BirthYear", "Source", "LastUpdated")
    for e in added:
        vals = ", ".join(_sql_quote(e.get(c)) for c in columns)
        cols = ", ".join(columns)
        lines.append(f"INSERT INTO mathematicians ({cols}) VALUES ({vals});")

    for e in changed:
        gid = _sql_quote(e.get("GlobalID"))
        sets = ", ".join(
            f"{c}={_sql_quote(e.get(c))}" for c in columns if c != "GlobalID"
        )
        lines.append(f"UPDATE mathematicians SET {sets} WHERE GlobalID={gid};")

    for e in removed:
        gid = _sql_quote(e.get("GlobalID"))
        lines.append(f"DELETE FROM mathematicians WHERE GlobalID={gid};")

    lines.append("COMMIT;")
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(out)


def generate_cypher_changelog(prev_dir: str, curr_dir: str, *, out_path: str) -> str:
    """Emit a Cypher changelog (MERGE for added/changed, DETACH
    DELETE for removed) at ``out_path``. Returns the path.
    """
    added, changed, removed = _diff_snapshots(prev_dir, curr_dir)
    lines: List[str] = ["// GMNAP Stage 9 Cypher changelog"]

    def _cy_str(s: Any) -> str:
        if s is None:
            return "null"
        return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'

    for e in added + changed:
        gid = _cy_str(e.get("GlobalID"))
        name = _cy_str(e.get("CanonicalLatin", ""))
        by = e.get("BirthYear")
        by_clause = f", birth_year: {by}" if isinstance(by, int) else ""
        lines.append(
            f"MERGE (m:Mathematician {{global_id: {gid}}}) "
            f"SET m.name = {name}{by_clause};"
        )

    for e in removed:
        gid = _cy_str(e.get("GlobalID"))
        lines.append(f"MATCH (m:Mathematician {{global_id: {gid}}}) DETACH DELETE m;")

    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(out)


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
