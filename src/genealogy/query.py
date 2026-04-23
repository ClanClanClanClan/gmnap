"""Lineage queries against Memgraph (or any Bolt-compatible graph DB).

This module is the "live graph store" path for the
``/api/v1/lineage/{id}`` endpoint.  If the graph is unreachable (no
network, wrong URI, driver not installed), every public function
returns ``None`` and the caller falls through to the local YAML-based
path and then the curated ``GenealogyLookup`` JSON.

Data model (written by ``tools/load_memgraph_from_enrichment.py``)::

    (p:Person {
        key: "euler, leonhard",           // normalized, PK
        name: "Euler, Leonhard",          // display form
        global_id: "NYBSDL…",             // optional
        birth_year: 1707,                 // optional
        death_year: 1783,                 // optional
        institution: "University of Basel",
        country: "Switzerland"
    })
    -[:DOCTORAL_ADVISOR]->(a:Person)

Lineage traversal is "advisor-of-me, then advisor-of-advisor, …". The
Cypher query uses variable-length pattern matching capped at
``depth`` hops; each matched path contributes one edge tuple per hop.

Public API
----------

``query_lineage(start, depth, bolt_uri, user, password)`` → ``dict | None``
    ``start`` may be a normalized key, a display name, or a GlobalID.
    Returns ``{"root": start, "depth": N, "edges": [...]}`` or ``None``
    if the driver can't connect.

``lineage_to_dot(result)`` → ``str``
    Render the edges as a Graphviz DOT document, rank-BT so the
    queried person sits at the top and ancestors stack downward —
    matches the web UI's tree layout.
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional

try:
    from neo4j import GraphDatabase  # type: ignore
    from neo4j.exceptions import Neo4jError, ServiceUnavailable  # type: ignore

    _DRIVER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _DRIVER_AVAILABLE = False

    # Bind placeholder attributes so test code can ``patch(...)`` them
    # without the module having to import neo4j for real. The guards
    # in `_driver` skip these entirely when _DRIVER_AVAILABLE is False.
    class GraphDatabase:  # type: ignore[no-redef]
        @staticmethod
        def driver(*args, **kwargs):
            raise RuntimeError("neo4j driver not installed")

    class Neo4jError(Exception):  # type: ignore[no-redef]
        pass

    class ServiceUnavailable(Exception):  # type: ignore[no-redef]
        pass


logger = logging.getLogger(__name__)


# --- Normalisation (matches GenealogyLookup + build_genealogy_enrichment) --

_PARTICLES = frozenset(
    {
        "von",
        "van",
        "de",
        "del",
        "della",
        "di",
        "du",
        "da",
        "den",
        "der",
        "le",
        "la",
        "ten",
        "ter",
        "af",
        "av",
        "zu",
        "zum",
        "zur",
    }
)


def _strip_diacritics(text: str) -> str:
    if not text:
        return text
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def _fold_particles(key: str) -> str:
    if "," not in key:
        return key
    surname, given = key.split(",", 1)
    tokens = surname.strip().split()
    parts: list[str] = []
    while tokens and tokens[0] in _PARTICLES:
        parts.append(tokens.pop(0))
    if not parts or not tokens:
        return key
    return f"{' '.join(tokens)}, {(given.strip() + ' ' + ' '.join(parts)).strip()}"


def _normalize_key(name: str) -> str:
    """Match the enrichment-file + GenealogyLookup key convention.

    Lowercase, diacritic-folded, "surname, given" ordering, particles
    moved to the given-name side.
    """
    if not name:
        return ""
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = _strip_diacritics(name)
    name = re.sub(r"\s+", " ", name.strip().lower())
    if "," not in name:
        parts = name.split()
        if len(parts) >= 2:
            name = f"{parts[-1]}, {' '.join(parts[:-1])}"
    name = re.sub(r"\s+,", ",", name).strip(" ,")
    return _fold_particles(name)


# --- Driver lifecycle ------------------------------------------------------


def _driver(bolt_uri: str, user: str = "", password: str = "", timeout: float = 2.0):
    if not _DRIVER_AVAILABLE:
        return None
    auth = (user, password) if user else None
    try:
        # connection_timeout prevents /api/v1/lineage from hanging for the
        # default 30 s bolt retry cycle when Memgraph isn't running.
        drv = GraphDatabase.driver(
            bolt_uri,
            auth=auth,
            connection_timeout=timeout,
            max_connection_lifetime=60,
        )
        # Verify connectivity eagerly so downstream failures are fast.
        drv.verify_connectivity()
        return drv
    except (ServiceUnavailable, Neo4jError, OSError) as exc:
        logger.debug("Memgraph driver unavailable at %s: %s", bolt_uri, exc)
        return None


# --- Public API ------------------------------------------------------------


def query_lineage(
    start: str,
    depth: int = 3,
    bolt_uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Query the graph store for up to `depth` advisor hops from `start`.

    Returns a serialisable dict or ``None`` if the store can't be
    reached / the driver isn't installed.
    """
    if depth <= 0:
        return {"root": start, "depth": depth, "edges": []}
    bolt_uri = bolt_uri or os.getenv("MEMGRAPH_BOLT", "bolt://localhost:7687")
    user = user if user is not None else os.getenv("MEMGRAPH_USER", "")
    password = password if password is not None else os.getenv("MEMGRAPH_PASSWORD", "")

    drv = _driver(bolt_uri, user, password)
    if drv is None:
        return None

    # Accept name: prefix + plain name + GID. We look up by normalized
    # key OR by global_id. If either matches, traverse.
    raw = start[5:] if start.startswith("name:") else start
    key = _normalize_key(raw)
    cypher = """
        MATCH (p:Person)
        WHERE p.key = $key OR p.global_id = $gid OR p.name = $raw
        WITH p LIMIT 1
        MATCH path = (p)-[:DOCTORAL_ADVISOR*1..%d]->(a:Person)
        UNWIND relationships(path) AS r
        WITH DISTINCT startNode(r) AS src, endNode(r) AS dst
        RETURN src.name AS from_name, dst.name AS to_name
    """ % int(max(1, min(depth, 10)))

    edges: List[Dict[str, str]] = []
    root_name = raw
    try:
        with drv.session() as session:
            # Resolve root's canonical display name first
            root_row = session.run(
                "MATCH (p:Person) "
                "WHERE p.key = $key OR p.global_id = $gid OR p.name = $raw "
                "RETURN p.name AS name LIMIT 1",
                key=key,
                gid=raw,
                raw=raw,
            ).single()
            if not root_row:
                drv.close()
                return {"root": start, "depth": depth, "edges": []}
            root_name = root_row["name"] or raw

            result = session.run(cypher, key=key, gid=raw, raw=raw)
            for row in result:
                frm = row["from_name"]
                to = row["to_name"]
                if frm and to:
                    edges.append({"from": frm, "to": to, "relation": "doctoralAdvisor"})
    except (Neo4jError, ServiceUnavailable, OSError) as exc:
        logger.debug("Memgraph lineage query failed: %s", exc)
        drv.close()
        return None
    finally:
        try:
            drv.close()
        except Exception:
            pass

    return {"root": start, "root_name": root_name, "depth": depth, "edges": edges}


def lineage_to_dot(result: Dict[str, Any]) -> str:
    """Render the lineage as a Graphviz DOT graph.

    Bottom-to-top layout (``rankdir=BT``) puts the queried person at
    the top and ancestors below, matching the web UI's tree view.
    """
    if not result:
        return "digraph Lineage {\n  rankdir=BT;\n}\n"
    lines = [
        "digraph Lineage {",
        "  rankdir=BT;",
        '  node [shape=box, style="rounded,filled", fillcolor="#1a1a25", fontcolor="#f0f0f5", color="#2a2a38"];',
        '  edge [color="#5b8def", arrowhead=vee];',
    ]
    nodes = set()
    for edge in result.get("edges", []) or []:
        frm = edge.get("from", "")
        to = edge.get("to", "")
        if not frm or not to:
            continue
        nodes.add(frm)
        nodes.add(to)
        lines.append(f'  "{frm}" -> "{to}";')
    if not result.get("edges"):
        # Still emit the root as a single node so DOT isn't empty
        root = result.get("root_name") or result.get("root") or ""
        if root:
            lines.append(f'  "{root}";')
    lines.append("}")
    return "\n".join(lines) + "\n"
