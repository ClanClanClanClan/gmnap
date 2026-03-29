from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

try:
    import duckdb  # type: ignore
except Exception:
    duckdb = None


def canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def write_yaml(entries: List[Dict[str, Any]], path: str):
    Path(path).write_text(canonical(entries), encoding="utf-8")


def write_duckdb_changelog(old: List[Dict[str, Any]], new: List[Dict[str, Any]], db_path: str):
    if duckdb is None:
        Path(db_path + ".SKIPPED").write_text("duckdb not available", encoding="utf-8")
        return
    con = duckdb.connect(db_path)
    con.execute("CREATE TABLE IF NOT EXISTS entries (GlobalID TEXT PRIMARY KEY, payload JSON)")
    con.execute(
        "CREATE TABLE IF NOT EXISTS changes (ts TIMESTAMP DEFAULT current_timestamp, action TEXT, GlobalID TEXT)"
    )
    o = {e.get("GlobalID"): e for e in old if e.get("GlobalID")}
    n = {e.get("GlobalID"): e for e in new if e.get("GlobalID")}
    for gid in sorted(set(n) - set(o)):
        con.execute("INSERT OR REPLACE INTO entries VALUES (?, ?)", [gid, canonical(n[gid])])
        con.execute("INSERT INTO changes(action, GlobalID) VALUES ('INSERT', ?)", [gid])
    for gid in sorted(set(o) - set(n)):
        con.execute("DELETE FROM entries WHERE GlobalID=?", [gid])
        con.execute("INSERT INTO changes(action, GlobalID) VALUES ('DELETE', ?)", [gid])
    for gid in sorted(set(o) & set(n)):
        if canonical(o[gid]) != canonical(n[gid]):
            con.execute("UPDATE entries SET payload=? WHERE GlobalID=?", [canonical(n[gid]), gid])
            con.execute("INSERT INTO changes(action, GlobalID) VALUES ('UPDATE', ?)", [gid])
    con.close()


def write_html_index(old: List[Dict[str, Any]], new: List[Dict[str, Any]], out_path: str):
    from html import escape

    o = {e.get("GlobalID"): e for e in old if e.get("GlobalID")}
    n = {e.get("GlobalID"): e for e in new if e.get("GlobalID")}
    keys = sorted(set(o) | set(n))
    rows = []
    for k in keys:
        left = escape(canonical(o.get(k, {})))
        right = escape(canonical(n.get(k, {})))
        klass = "same" if left == right else "diff"
        rows.append(
            f"<tr class='{klass}'><td>{k}</td><td><pre>{left}</pre></td><td><pre>{right}</pre></td></tr>"
        )
    html = (
        "<html><head><style>td{vertical-align:top}.diff{background:#fff5f5}.same{background:#f8fff8}table{width:100%}pre{white-space:pre-wrap;word-wrap:break-word}</style></head><body><table><thead><tr><th>GlobalID</th><th>Old</th><th>New</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></body></html>"
    )
    Path(out_path).write_text(html, encoding="utf-8")


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
        self, old_entries: List[Dict[str, Any]], new_entries: List[Dict[str, Any]], output_path: str
    ) -> None:
        """Generate HTML diff report."""
        write_html_index(old_entries, new_entries, output_path)

    def is_available(self) -> bool:
        """Check if DuckDB is available."""
        return self.available
