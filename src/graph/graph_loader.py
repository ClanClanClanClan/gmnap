from __future__ import annotations

from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

from ..utils.matching import map_wikidata_to_global_id


class GraphLoader:
    def __init__(
        self, uri: str, user: Optional[str] = None, password: Optional[str] = None
    ):
        auth = (user, password) if user or password else None
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def upsert_nodes(
        self, entries: List[Dict[str, Any]], batch_size: int = 1000
    ) -> None:
        q = (
            "UNWIND $batch AS e "
            "MERGE (m:Mathematician {global_id: e.global_id}) "
            "SET m.canonical_latin = e.canonical_latin, "
            "    m.canonical_native = e.canonical_native, "
            "    m.name_given = e.name_given, "
            "    m.name_family = e.name_family, "
            "    m.region_code = e.region_code, "
            "    m.country_code = e.country_code, "
            "    m.birth_year = e.birth_year, "
            "    m.death_year = e.death_year, "
            "    m.detection_confidence = coalesce(e.detection_confidence, 0.0), "
            "    m.bayesian_coherence = coalesce(e.bayesian_coherence, 0.0), "
            "    m.betweenness_score = coalesce(e.betweenness_score, 0.0), "
            "    m.data_sources = coalesce(e.data_sources, [])"
        )
        with self.driver.session() as s:
            for i in range(0, len(entries), batch_size):
                s.run(q, batch=entries[i : i + batch_size])

    def upsert_advisor_edges(
        self, edges: List[Dict[str, Any]], batch_size: int = 1000
    ) -> None:
        # Fetch a snapshot of all current nodes for name->id resolution
        with self.driver.session() as s:
            res = s.run(
                "MATCH (m:Mathematician) RETURN m.global_id AS id, m.canonical_latin AS name, m.birth_year AS by"
            )
            rows = res.data()
        snapshot = [
            {"GlobalID": r["id"], "CanonicalLatin": r["name"], "BirthYear": r["by"]}
            for r in rows
        ]

        # Resolve target ids where missing
        resolved: List[Dict[str, Any]] = []
        for e in edges:
            tid = e.get("target_id")
            if not tid:
                tname = e.get("target_name")
                tby = e.get("target_birth_year")
                tid, _ = map_wikidata_to_global_id(tname or "", tby, snapshot)
            if not tid:
                # create shadow node id
                tid = f"SHADOW::{(tname or 'unknown')}"
                # insert shadow node
                with self.driver.session() as s:
                    s.run(
                        "MERGE (m:Mathematician:Shadow {global_id:$id}) "
                        "SET m.canonical_latin=$name, m.is_shadow=true",
                        id=tid,
                        name=e.get("target_name"),
                    )
            e2 = dict(e)
            e2["target_id"] = tid
            resolved.append(e2)

        q = (
            "UNWIND $batch AS r "
            "MATCH (s:Mathematician {global_id: r.source_id}) "
            "MATCH (a:Mathematician {global_id: r.target_id}) "
            "MERGE (s)-[rel:DOCTORAL_ADVISOR]->(a) "
            "SET rel.degree_date = r.degree_date, "
            "    rel.institution = r.institution, "
            "    rel.confidence = coalesce(r.confidence, 0.9), "
            "    rel.sources = coalesce(r.sources, [])"
        )
        with self.driver.session() as s:
            for i in range(0, len(resolved), batch_size):
                s.run(q, batch=resolved[i : i + batch_size])

    def compute_basic_metrics(self) -> None:
        # Keep it simple and cheap. PageRank is illustrative.
        with self.driver.session() as s:
            # Create an in-memory projection via Memgraph/Neo4j procedure if available;
            # here we just count degree as a cheap proxy.
            s.run(
                "MATCH (a:Mathematician)<-[r:DOCTORAL_ADVISOR]-() "
                "WITH a, count(r) AS deg "
                "SET a.betweenness_score = deg * 1.0"
            )
