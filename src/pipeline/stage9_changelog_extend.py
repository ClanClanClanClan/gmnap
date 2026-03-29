from __future__ import annotations
import json, pathlib
from typing import Dict, List, Any


def _append(path: pathlib.Path, lines: List[str]):
    with open(path, "a", encoding="utf-8") as f:
        for ln in lines:
            f.write(ln.rstrip() + "\n")


def _escape(s: str) -> str:
    return s.replace('"', '\\"')


def _to_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def append_edges_to_changelog(
    snapshot_dir: str, entries: List[Dict[str, Any]] | None = None
) -> str:
    """
    Append richer updates to changelog:
      - Array properties (AlternativeLatin, AlternativeNative, Institution, Publications, Subfield, Awards)
      - Genealogy relationships from Advisors/Students
    Uses MERGE for idempotency.
    """
    sdir = pathlib.Path(snapshot_dir)
    entries_json = sdir / "entries.json"
    if entries is None:
        entries = json.loads(entries_json.read_text(encoding="utf-8"))
    chg = sdir / "changelog.cypher"
    lines: List[str] = []
    lines.append("// --- Push 9: extended updates (arrays + relationships) ---")

    array_props = [
        "AlternativeLatin",
        "AlternativeNative",
        "Institution",
        "Publications",
        "Subfield",
        "Awards",
    ]
    for e in entries:
        gid = e.get("GlobalID")
        if not gid:
            continue
        # Arrays → set as arrays (idempotent)
        sets = []
        for k in array_props:
            if k in e and isinstance(e[k], list) and e[k]:
                sets.append(f"m.{k} = {json.dumps(e[k], ensure_ascii=False)}")
        if sets:
            lines.append(f'MATCH (m:Mathematician {{global_id: "{_escape(gid)}"}})')
            lines.append("SET " + ", ".join(sets))
            lines.append(";")
        # Advisors: student -[:ADVISED_BY]-> advisor
        for adv in _to_list(e.get("Advisors")):
            if not adv:
                continue
            lines.append(f'MERGE (s:Mathematician {{global_id: "{_escape(gid)}"}})')
            lines.append(f'MERGE (a:Mathematician {{global_id: "{_escape(adv)}"}})')
            lines.append("MERGE (s)-[:ADVISED_BY]->(a)")
            lines.append(";")
        # Students: inverse relation (student -> advisor)
        for stu in _to_list(e.get("Students")):
            if not stu:
                continue
            lines.append(f'MERGE (s:Mathematician {{global_id: "{_escape(stu)}"}})')
            lines.append(f'MERGE (a:Mathematician {{global_id: "{_escape(gid)}"}})')
            lines.append("MERGE (s)-[:ADVISED_BY]->(a)")
            lines.append(";")

    _append(chg, lines)
    return str(chg)
