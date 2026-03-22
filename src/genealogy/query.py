"""
GMNAP V7 — Academic genealogy lineage queries.

Queries the Memgraph graph database for advisor/student relationships,
returning lineage trees up to a configurable depth.  Falls back to a
``{}``, not a crash, when the graph is empty or the driver is missing.

Used by ``GET /api/v1/lineage/{global_id}?depth=3&format=json``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Neo4j / Memgraph driver (optional — degrade gracefully)
# ---------------------------------------------------------------------------
try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Cypher queries
# ---------------------------------------------------------------------------
_ANCESTORS_QUERY = """
MATCH path = (start:Mathematician {global_id: $gid})-[:DOCTORAL_ADVISOR*1..$depth]->(ancestor:Mathematician)
WITH ancestor, path, size(nodes(path)) - 1 AS dist
RETURN ancestor.global_id   AS global_id,
       ancestor.canonical_latin AS name,
       ancestor.birth_year   AS birth_year,
       ancestor.death_year   AS death_year,
       ancestor.region       AS region,
       ancestor.msc_primary  AS msc_primary,
       dist                  AS distance
ORDER BY dist, ancestor.canonical_latin
"""

_DESCENDANTS_QUERY = """
MATCH path = (start:Mathematician {global_id: $gid})<-[:DOCTORAL_ADVISOR*1..$depth]-(student:Mathematician)
WITH student, path, size(nodes(path)) - 1 AS dist
RETURN student.global_id   AS global_id,
       student.canonical_latin AS name,
       student.birth_year   AS birth_year,
       student.death_year   AS death_year,
       student.region       AS region,
       student.msc_primary  AS msc_primary,
       dist                 AS distance
ORDER BY dist, student.canonical_latin
"""

_NODE_QUERY = """
MATCH (m:Mathematician {global_id: $gid})
RETURN m.global_id        AS global_id,
       m.canonical_latin  AS name,
       m.canonical_native AS native_name,
       m.birth_year       AS birth_year,
       m.death_year       AS death_year,
       m.region           AS region,
       m.msc_primary      AS msc_primary,
       m.confidence       AS confidence,
       m.betweenness_score AS betweenness
"""

_EDGES_QUERY = """
MATCH (s:Mathematician {global_id: $gid})-[r:DOCTORAL_ADVISOR]->(a:Mathematician)
RETURN s.global_id AS student_id,
       a.global_id AS advisor_id,
       r.confidence AS confidence,
       r.source     AS source,
       r.year       AS year
UNION
MATCH (s:Mathematician)-[r:DOCTORAL_ADVISOR]->(a:Mathematician {global_id: $gid})
RETURN s.global_id AS student_id,
       a.global_id AS advisor_id,
       r.confidence AS confidence,
       r.source     AS source,
       r.year       AS year
"""


def _record_to_dict(record) -> Dict[str, Any]:
    """Convert a neo4j Record to a plain dict, dropping None values."""
    return {k: v for k, v in dict(record).items() if v is not None}


# ---------------------------------------------------------------------------
# Core query function
# ---------------------------------------------------------------------------
def query_lineage(
    global_id: str,
    *,
    depth: int = 3,
    bolt_uri: str = "bolt://localhost:7687",
    auth: Optional[tuple] = None,
) -> Optional[Dict[str, Any]]:
    """
    Query the academic lineage graph for a mathematician.

    Parameters
    ----------
    global_id : str
        The GMNAP GlobalID to look up.
    depth : int
        Maximum number of hops for ancestor/descendant traversal (1–10).
    bolt_uri : str
        Bolt protocol URI for Memgraph / Neo4j.
    auth : tuple, optional
        ``(user, password)`` for the graph database.  Falls back to
        ``MEMGRAPH_USER`` / ``MEMGRAPH_PASSWORD`` env vars.

    Returns
    -------
    dict or None
        Lineage result with ``root``, ``ancestors``, ``descendants``,
        ``edges``, and ``meta`` keys.  Returns ``None`` if the GlobalID
        is not found in the graph.
    """
    if GraphDatabase is None:
        logger.warning("neo4j driver not installed — lineage queries unavailable")
        return None

    if auth is None:
        user = os.getenv("MEMGRAPH_USER", "")
        pwd = os.getenv("MEMGRAPH_PASSWORD", "")
        auth = (user, pwd) if user else None

    # Cypher variable-length patterns (*1..N) don't support parameters,
    # so we must interpolate depth. Strictly validate it's a small int.
    depth = int(max(1, min(depth, 10)))

    driver = None
    try:
        driver = GraphDatabase.driver(bolt_uri, auth=auth)
        driver.verify_connectivity()

        with driver.session() as session:
            # 1. Fetch the root node
            root_result = session.run(_NODE_QUERY, gid=global_id)
            root_record = root_result.single()
            if root_record is None:
                return None
            root = _record_to_dict(root_record)

            # 2. Fetch ancestors (advisors going up)
            anc_result = session.run(
                _ANCESTORS_QUERY.replace("$depth", str(depth)),
                gid=global_id,
            )
            ancestors = [_record_to_dict(r) for r in anc_result]

            # 3. Fetch descendants (students going down)
            desc_result = session.run(
                _DESCENDANTS_QUERY.replace("$depth", str(depth)),
                gid=global_id,
            )
            descendants = [_record_to_dict(r) for r in desc_result]

            # 4. Fetch direct edges involving this node
            edge_result = session.run(_EDGES_QUERY, gid=global_id)
            edges = [_record_to_dict(r) for r in edge_result]

        return {
            "root": root,
            "ancestors": ancestors,
            "descendants": descendants,
            "edges": edges,
            "meta": {
                "depth": depth,
                "ancestor_count": len(ancestors),
                "descendant_count": len(descendants),
                "edge_count": len(edges),
            },
        }

    except Exception as e:
        logger.error("Lineage query failed for %s: %s", global_id, e)
        raise

    finally:
        if driver is not None:
            try:
                driver.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# DOT (Graphviz) export
# ---------------------------------------------------------------------------
def lineage_to_dot(lineage: Dict[str, Any]) -> str:
    """Convert lineage result to DOT format for Graphviz rendering."""
    lines = ['digraph lineage {', '  rankdir=BT;', '  node [shape=box, style=rounded];']

    root = lineage["root"]
    root_gid = root["global_id"]
    root_label = root.get("name", root_gid)
    lines.append(f'  "{root_gid}" [label="{root_label}", style="rounded,bold"];')

    seen = {root_gid}
    for node in lineage.get("ancestors", []) + lineage.get("descendants", []):
        gid = node["global_id"]
        if gid not in seen:
            label = node.get("name", gid)
            years = ""
            if node.get("birth_year"):
                years = f"\\n{node['birth_year']}"
                if node.get("death_year"):
                    years += f"–{node['death_year']}"
            lines.append(f'  "{gid}" [label="{label}{years}"];')
            seen.add(gid)

    for edge in lineage.get("edges", []):
        src = edge["student_id"]
        dst = edge["advisor_id"]
        conf = edge.get("confidence", "")
        label = f' [label="{conf}"]' if conf else ""
        lines.append(f'  "{src}" -> "{dst}"{label};')

    lines.append("}")
    return "\n".join(lines)
