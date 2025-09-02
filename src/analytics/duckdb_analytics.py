from __future__ import annotations
import duckdb, os, pathlib, json
from typing import List, Dict, Tuple

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS entries (
  GlobalID TEXT,
  CanonicalLatin TEXT,
  order_key TEXT,
  BirthYear INTEGER,
  Field TEXT,
  Source TEXT,
  LastUpdated TEXT,
  ValidationStatus TEXT
);
CREATE INDEX IF NOT EXISTS idx_entries_key ON entries(order_key);
CREATE INDEX IF NOT EXISTS idx_entries_gid ON entries(GlobalID);
"""

class DuckDBAnalytics:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self.con = duckdb.connect(db_path)
        self.con.execute(SCHEMA_DDL)

    def load_entries(self, batch: List[Dict]) -> None:
        # Create a temp view and insert deterministically (sorted by GlobalID)
        rows = [(e.get("GlobalID",""), e.get("CanonicalLatin",""), e.get("order_key",""),
                 int(e.get("BirthYear") or 0) if e.get("BirthYear") is not None else None,
                 e.get("Field",""), e.get("Source",""), e.get("LastUpdated",""), e.get("ValidationStatus",""))
                for e in sorted(batch, key=lambda x: x.get("GlobalID",""))]
        self.con.execute("DELETE FROM entries")
        self.con.executemany("INSERT INTO entries VALUES (?,?,?,?,?,?,?,?)", rows)

    def detect_collisions(self) -> List[Dict]:
        q = """
        SELECT order_key, BirthYear, COUNT(*) AS n, LIST(GlobalID) AS gids
        FROM entries
        GROUP BY order_key, BirthYear
        HAVING n > 1
        ORDER BY n DESC, order_key
        """
        return [dict(zip([c[0] for c in self.con.description], row)) for row in self.con.execute(q).fetchall()]

    def suffix_duplicates(self, batch: List[Dict]) -> Tuple[List[Dict], int]:
        collisions = self.detect_collisions()
        suffixed = 0
        coll_map = {}
        for c in collisions:
            ok, by, gids = c["order_key"], c["BirthYear"], list(c["gids"])
            for i, gid in enumerate(sorted(gids)):
                if i == 0:
                    continue
                coll_map[gid] = f"{gid}--{i}"
        out = []
        for e in batch:
            gid = e.get("GlobalID","")
            if gid in coll_map:
                e = dict(e)
                e["GlobalID"] = coll_map[gid]
                suffixed += 1
            out.append(e)
        return out, suffixed

def stage5_collision_analytics_duckdb(batch: List[Dict], db_path: str = ":memory:"):
    d = DuckDBAnalytics(db_path=db_path)
    d.load_entries(batch)
    out, suffixed = d.suffix_duplicates(batch)
    metrics = {"collision_duplicates": suffixed}
    return out, metrics
