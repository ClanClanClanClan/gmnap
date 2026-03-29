from __future__ import annotations
from typing import Dict, List, Any
import json, pathlib

ARRAY_PROPS = [
    "AlternativeLatin",
    "AlternativeNative",
    "Institution",
    "Subfield",
    "Awards",
    "Publications",
    "Collaborators",
]
EDGE_FIELDS = {
    "Advisors": ("ADVISED_BY", "advisor_id"),  # (edge_type, target_field_name)
    "Students": ("ADVISED_BY", "student_id:reverse"),  # reverse direction
}


def _esc(s: str) -> str:
    return s.replace('"', '\\"')


def generate_arrays_cypher(out_dir: pathlib.Path, entries: List[Dict[str, Any]]) -> str:
    lines = []
    lines.append("// GMNAP Stage 9 — Array property upserts")
    for e in entries:
        gid = e.get("GlobalID")
        if not gid:
            continue
        sets = []
        for k in ARRAY_PROPS:
            if k in e and isinstance(e[k], list):
                # set as array literal
                arr_json = json.dumps(e[k], ensure_ascii=False)
                sets.append(f"m.{k} = {arr_json}")
        if sets:
            lines.append(f'MATCH (m:Mathematician {{global_id: "{_esc(gid)}"}})')
            lines.append("SET " + ", ".join(sets))
            lines.append(";")
    path = out_dir / "changelog_arrays.cypher"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def generate_edges_cypher(out_dir: pathlib.Path, entries: List[Dict[str, Any]]) -> str:
    lines = []
    lines.append("// GMNAP Stage 9 — Relationship upserts")
    for e in entries:
        gid = e.get("GlobalID")
        if not gid:
            continue
        for field, (etype, mode) in EDGE_FIELDS.items():
            if field not in e:
                continue
            vals = [v for v in e[field] if v]
            if not vals:
                continue
            if mode.endswith(":reverse"):
                # (target)-[:ADVISED_BY]->(m)
                lines.append("UNWIND $pairs AS pair")
                lines.append("MATCH (m:Mathematician {global_id: pair.to})")
                lines.append("MERGE (n:Mathematician {global_id: pair.frm})")
                lines.append(f"MERGE (n)-[:{etype}]->(m);")
                # parameters would be [{'frm': student, 'to': gid}]
                # For static file we expand directly:
                for v in vals:
                    lines.append(f'MERGE (s:Mathematician {{global_id: "{_esc(v)}"}});')
                    lines.append(
                        f'MERGE (s)-[:{etype}]->(:Mathematician {{global_id: "{_esc(gid)}"}});'
                    )
            else:
                # (m)-[:ADVISED_BY]->(target)
                for v in vals:
                    lines.append(f'MERGE (m:Mathematician {{global_id: "{_esc(gid)}"}});')
                    lines.append(f'MERGE (n:Mathematician {{global_id: "{_esc(v)}"}});')
                    lines.append(f"MERGE (m)-[:{etype}]->(n);")
    path = out_dir / "changelog_edges.cypher"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def generate_changelogs_expanded(out_dir: str, entries: List[Dict[str, Any]]) -> List[str]:
    p = pathlib.Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    a = generate_arrays_cypher(p, entries)
    b = generate_edges_cypher(p, entries)
    return [a, b]
