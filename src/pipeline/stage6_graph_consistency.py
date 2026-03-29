from __future__ import annotations
import os
from typing import List, Dict, Any
from ..graph.graph_loader import GraphLoader


async def populate_graph(
    entries: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    compute_metrics: bool = True,
    batch_size: int = 1000,
) -> None:
    """Stage 6: Populate Memgraph/Neo4j with nodes and advisor edges."""
    uri = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
    user = os.getenv("MEMGRAPH_USER", None)
    pwd = os.getenv("MEMGRAPH_PASSWORD", None)

    gl = GraphLoader(uri=uri, user=user, password=pwd)

    # Upsert nodes
    node_props = []
    for e in entries:
        node_props.append(
            {
                "global_id": e["GlobalID"],
                "canonical_latin": e.get("CanonicalLatin"),
                "canonical_native": e.get("CanonicalNative"),
                "name_given": e.get("NameGiven"),
                "name_family": e.get("NameFamily"),
                "region_code": e.get("DetectedRegion") or e.get("RegionCode"),
                "country_code": e.get("CountryCode"),
                "birth_year": e.get("BirthYear"),
                "death_year": e.get("DeathYear"),
                "detection_confidence": e.get("DetectionConfidence", 0.0),
                "bayesian_coherence": e.get("BayesianCoherence", 0.0),
                "betweenness_score": e.get("BetweennessScore", 0.0),
                "data_sources": e.get("Sources", []),
            }
        )
    gl.upsert_nodes(node_props, batch_size=batch_size)

    # Upsert edges (resolve target by id or name fuzzy match inside loader)
    gl.upsert_advisor_edges(edges, batch_size=batch_size)

    if compute_metrics:
        gl.compute_basic_metrics()
