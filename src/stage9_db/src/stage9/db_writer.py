from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path
import json

try:
    import duckdb
except Exception:
    duckdb = None


def canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def write_yaml(entries: List[Dict[str, Any]], path: str):
    Path(path).write_text(canonical(entries), encoding="utf-8")


def write_duckdb_changelog(
    old: List[Dict[str, Any]], new: List[Dict[str, Any]], db_path: str
):
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
    for gid in sorted(set(n) - set(o)):
        con.execute(
            "INSERT OR REPLACE INTO entries VALUES (?, ?)", [gid, canonical(n[gid])]
        )
        con.execute("INSERT INTO changes(action, GlobalID) VALUES ('INSERT', ?)", [gid])
    for gid in sorted(set(o) - set(n)):
        con.execute("DELETE FROM entries WHERE GlobalID=?", [gid])
        con.execute("INSERT INTO changes(action, GlobalID) VALUES ('DELETE', ?)", [gid])
    for gid in sorted(set(o) & set(n)):
        if canonical(o[gid]) != canonical(n[gid]):
            con.execute(
                "UPDATE entries SET payload=? WHERE GlobalID=?",
                [canonical(n[gid]), gid],
            )
            con.execute(
                "INSERT INTO changes(action, GlobalID) VALUES ('UPDATE', ?)", [gid]
            )
    con.close()


def write_html_index(
    old: List[Dict[str, Any]], new: List[Dict[str, Any]], out_path: str
):
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
