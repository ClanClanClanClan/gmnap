from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import duckdb  # type: ignore
except Exception:
    duckdb = None


def canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def write_yaml(entries: List[Dict[str, Any]], path: str):
    Path(path).write_text(canonical(entries), encoding="utf-8")


def write_duckdb_changelog(
    old: List[Dict[str, Any]], new: List[Dict[str, Any]], db_path: str
):
    """Write an INSERT/UPDATE/DELETE changelog of ``new`` vs ``old`` to DuckDB.

    Performance history: R54 replaced two individual ``con.execute()``
    statements per entry (~7.5 ms/entry) with ``executemany`` in one
    transaction (~5×). R56 went further after the 1M benchmark showed
    ``executemany`` itself converts parameters row-by-row in Python
    (~1.5 ms/row for tiny rows, far worse for multi-KB payloads): the
    INSERT arm — the whole batch on a fresh run — now streams to a temp
    CSV and ingests via DuckDB's vectorized ``read_csv`` (~370× faster,
    measured). Output is identical — same tables, same rows, same
    canonical payloads.
    """
    if duckdb is None:
        Path(db_path + ".SKIPPED").write_text("duckdb not available", encoding="utf-8")
        return
    con = duckdb.connect(db_path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS entries (GlobalID TEXT PRIMARY KEY, payload JSON)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS changes (ts TIMESTAMP DEFAULT current_timestamp, action TEXT, GlobalID TEXT)"
    )
    o = {e.get("GlobalID"): e for e in old if e.get("GlobalID")}
    n = {e.get("GlobalID"): e for e in new if e.get("GlobalID")}

    added = sorted(set(n) - set(o))
    removed = sorted(set(o) - set(n))
    # Canonicalising both sides is proportional to the OVERLAP (usually
    # small); the fresh-run path (old=[]) skips it entirely.
    updated = [
        gid for gid in sorted(set(o) & set(n)) if canonical(o[gid]) != canonical(n[gid])
    ]

    con.execute("BEGIN TRANSACTION")
    try:
        # R56: the INSERT arm is the 1M-scale path (a fresh run inserts
        # every entry). executemany's per-row parameter conversion measures
        # ~1.5 ms/row (~26 min/1M) BEFORE the multi-KB payloads make it
        # worse, so stream (gid, payload) to a temp CSV and ingest through
        # DuckDB's vectorized read_csv (~seconds/1M). The 'changes' rows
        # derive from the same temp table. DELETE/UPDATE arms stay on
        # executemany: they are proportional to churn against a previous
        # run, which is small in every real workload.
        if added:
            import csv as _csv
            import os as _os
            import tempfile as _tempfile

            fd, path = _tempfile.mkstemp(suffix=".csv", prefix="gmnap_s9_")
            try:
                with _os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                    w = _csv.writer(f)
                    for gid in added:
                        w.writerow([gid, canonical(n[gid])])
                safe_path = path.replace("'", "''")
                src = (
                    f"read_csv('{safe_path}', header=false, "
                    "columns={'column0':'VARCHAR','column1':'VARCHAR'}, "
                    "max_line_size=33554432)"
                )
                con.execute(
                    f"INSERT OR REPLACE INTO entries SELECT column0, column1 FROM {src}"
                )
                con.execute(
                    f"INSERT INTO changes(action, GlobalID) "
                    f"SELECT 'INSERT', column0 FROM {src}"
                )
            finally:
                try:
                    _os.unlink(path)
                except OSError:
                    pass
        if removed:
            con.executemany(
                "DELETE FROM entries WHERE GlobalID=?", [(gid,) for gid in removed]
            )
            con.executemany(
                "INSERT INTO changes(action, GlobalID) VALUES ('DELETE', ?)",
                [(gid,) for gid in removed],
            )
        if updated:
            con.executemany(
                "UPDATE entries SET payload=? WHERE GlobalID=?",
                [(canonical(n[gid]), gid) for gid in updated],
            )
            con.executemany(
                "INSERT INTO changes(action, GlobalID) VALUES ('UPDATE', ?)",
                [(gid,) for gid in updated],
            )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        con.close()
        raise
    con.close()


def write_html_index(
    old: List[Dict[str, Any]], new: List[Dict[str, Any]], out_path: str
):
    """Write the human-readable old/new diff table.

    R56: capped at GMNAP_HTML_DIFF_MAX_ROWS rows (default 5000) and
    streamed to the file instead of concatenated into one string. The
    uncapped version emitted two canonical-JSON dumps of EVERY entry —
    a multi-GB HTML file at 1M entries, useless to a human and capable
    of exhausting RAM. Truncation is announced in the file itself, not
    silent. Output below the cap is byte-identical to the old writer.
    """
    import os as _os
    from html import escape

    try:
        max_rows = int(_os.getenv("GMNAP_HTML_DIFF_MAX_ROWS", "5000"))
    except ValueError:
        max_rows = 5000

    o = {e.get("GlobalID"): e for e in old if e.get("GlobalID")}
    n = {e.get("GlobalID"): e for e in new if e.get("GlobalID")}
    keys = sorted(set(o) | set(n))
    truncated = len(keys) - max_rows if len(keys) > max_rows else 0
    with Path(out_path).open("w", encoding="utf-8") as f:
        f.write(
            "<html><head><style>td{vertical-align:top}.diff{background:#fff5f5}.same{background:#f8fff8}table{width:100%}pre{white-space:pre-wrap;word-wrap:break-word}</style></head><body><table><thead><tr><th>GlobalID</th><th>Old</th><th>New</th></tr></thead><tbody>"
        )
        for k in keys[:max_rows]:
            left = escape(canonical(o.get(k, {})))
            right = escape(canonical(n.get(k, {})))
            klass = "same" if left == right else "diff"
            f.write(
                f"<tr class='{klass}'><td>{k}</td><td><pre>{left}</pre></td><td><pre>{right}</pre></td></tr>"
            )
        if truncated:
            f.write(
                f"<tr class='diff'><td colspan='3'><strong>… truncated: "
                f"{truncated} further row(s) omitted "
                f"(GMNAP_HTML_DIFF_MAX_ROWS={max_rows}; the complete data "
                f"is in stage9.yaml / stage9.duckdb)</strong></td></tr>"
            )
        f.write("</tbody></table></body></html>")


class DuckDBWriter:
    """DuckDB writer for Stage 9 - handles database persistence and analytics."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize DuckDB writer."""
        self.db_path = db_path or "output/entries.duckdb"
        self.available = duckdb is not None

    def write_entries(self, entries: List[Dict[str, Any]], output_path: str) -> None:
        """Write entries to file."""
        write_yaml(entries, output_path)

    def write_changelog(
        self, old_entries: List[Dict[str, Any]], new_entries: List[Dict[str, Any]]
    ) -> None:
        """Write changelog to DuckDB."""
        write_duckdb_changelog(old_entries, new_entries, self.db_path)

    def write_html_diff(
        self,
        old_entries: List[Dict[str, Any]],
        new_entries: List[Dict[str, Any]],
        output_path: str,
    ) -> None:
        """Generate HTML diff report."""
        write_html_index(old_entries, new_entries, output_path)

    def is_available(self) -> bool:
        """Check if DuckDB is available."""
        return self.available
