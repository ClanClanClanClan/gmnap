from __future__ import annotations

import json
import os

from neo4j import GraphDatabase


def get_driver(
    uri: str = "bolt://localhost:7687", user: str = None, password: str = None
):
    auth = (user, password) if user or password else None
    return GraphDatabase.driver(uri, auth=auth)


def run(db_type: str = "memgraph"):
    """
    Load graph data into Neo4j or Memgraph

    Args:
        db_type: "neo4j" or "memgraph" (default: "memgraph")
    """
    driver = get_driver("bolt://localhost:7687")
    with driver.session() as sess:
        # Use appropriate index file based on database type
        if db_type == "memgraph":
            idx_file = "graph/cypher_indexes_memgraph.cypher"
        else:
            idx_file = "graph/cypher_indexes.cypher"

        try:
            idx = open(idx_file, "r", encoding="utf-8").read()
            for stmt in [
                s
                for s in idx.split(";")
                if s.strip() and not s.strip().startswith("--")
            ]:
                try:
                    sess.run(stmt)
                except Exception as e:
                    print(f"[WARN] Index creation skipped (may already exist): {e}")
        except FileNotFoundError:
            print(f"[WARN] Index file not found: {idx_file}, skipping index creation")
        edges_path = "data/fixtures/edges.jsonl"
        if os.path.exists(edges_path):
            with open(edges_path, "r", encoding="utf-8") as f:
                for line in f:
                    e = json.loads(line)
                    sess.run(
                        """MERGE (s:Mathematician {global_id:$student})
  ON CREATE SET s.canonical_latin = $s_name
MERGE (a:Mathematician {global_id:$advisor})
  ON CREATE SET a.canonical_latin = $a_name
MERGE (s)-[r:DOCTORAL_ADVISOR]->(a)
SET r.degree_date=$date,
    r.institution=$inst,
    r.degree_type=$deg,
    r.confidence=$conf,
    r.sources=$sources,
    r.verified=$verified,
    r.provenance_hash=$prov
                        """,
                        student=e["student_global_id"],
                        s_name=e.get("student_name"),
                        advisor=e["advisor_global_id"],
                        a_name=e.get("advisor_name"),
                        date=e.get("degree_date"),
                        inst=e.get("institution"),
                        deg=e.get("degree_type"),
                        conf=e.get("confidence", 0.8),
                        sources=e.get("sources", []),
                        verified=e.get("verified", False),
                        prov=e.get("provenance_hash"),
                    )
            print("[LOAD] fixture edges loaded.")
        else:
            print("[SKIP] no fixture edges present.")
    driver.close()


if __name__ == "__main__":
    run()
