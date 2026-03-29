from __future__ import annotations
from typing import Dict, List, Tuple
import duckdb, json, os, pathlib

# from ..ops.metrics import WRITE_DIFF_CHANGED_ENTRIES  # placeholder import for consistency


def _as_table(batch: List[Dict]) -> List[Dict]:
    out = []
    for e in batch:
        out.append(
            {
                "GlobalID": e.get("GlobalID"),
                "CanonicalLatin": e.get("CanonicalLatin"),
                "BirthYear": e.get("BirthYear"),
                "DeathYear": e.get("DeathYear"),
                "Field": e.get("Field"),
                "Source": e.get("Source"),
                "Advisors": json.dumps(e.get("Advisors") or []),
            }
        )
    return out


def stage5_duckdb(
    batch: List[Dict], workdir: str = "work"
) -> Tuple[List[Dict], Dict[str, float], str]:
    """
    Stage 5 (enhanced): Use DuckDB to compute duplicates, suffix remaps, and synthesise genealogy edges.
    Returns (batch', metrics, path_to_report).
    """
    pathlib.Path(workdir).mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(database=":memory:")
    con.execute("PRAGMA memory_limit='1GB'")

    tbl = _as_table(batch)
    con.execute("CREATE TABLE entries AS SELECT * FROM tbl").df()  # ensure table exists
    con.register("tbl", tbl)
    con.execute(
        """
        CREATE TABLE entries AS
        SELECT * FROM tbl
    """
    )
    # Duplicate detection: same CanonicalLatin + BirthYear
    con.execute(
        """
        WITH d AS (
          SELECT CanonicalLatin, BirthYear, COUNT(*) AS c
          FROM entries
          GROUP BY 1,2 HAVING COUNT(*) > 1
        )
        SELECT e.GlobalID, e.CanonicalLatin, e.BirthYear
        FROM entries e
        JOIN d ON e.CanonicalLatin = d.CanonicalLatin AND coalesce(e.BirthYear, -1) = coalesce(d.BirthYear, -1)
        ORDER BY e.CanonicalLatin, e.BirthYear, e.GlobalID
    """
    )
    dup_rows = con.fetchall()
    collisions = 0
    seen = {}
    out = []
    for e in batch:
        key = (e.get("CanonicalLatin"), e.get("BirthYear"))
        if key not in seen:
            seen[key] = []
        seen[key].append(e)
    for key, group in seen.items():
        if len(group) == 1:
            out.extend(group)
        else:
            # suffix GlobalIDs deterministically
            group_sorted = sorted(group, key=lambda x: x.get("GlobalID", ""))
            first = True
            idx = 1
            for g in group_sorted:
                if first:
                    out.append(g)
                    first = False
                else:
                    collisions += 1
                    g2 = dict(g)
                    g2["GlobalID"] = f'{g2.get("GlobalID")}' + f"--{idx}"
                    idx += 1
                    out.append(g2)

    # Synthesise genealogy edges report (CSV)
    csv_path = os.path.join(workdir, "stage5_edges.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("source,target,relation_type\n")
        for e in out:
            sid = e.get("GlobalID")
            for a in e.get("Advisors") or []:
                if sid and a:
                    f.write(f"{sid},{a},doctoralAdvisor\n")

    metrics = {"collisions": float(collisions), "edges": 0.0}
    return out, metrics, csv_path
