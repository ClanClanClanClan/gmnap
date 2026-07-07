from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    import networkx as nx  # type: ignore
except Exception:
    nx = None

logger = logging.getLogger(__name__)


def betweenness_score(entries: List[Dict[str, Any]]) -> float:
    """Legacy function for backward compatibility - returns average score."""
    coherence = GraphCoherence()
    scores = coherence.compute_coherence(entries)
    if scores:
        return sum(scores.values()) / len(scores)
    return 0.5


class GraphCoherence:
    """Graph coherence analyzer for V7 pipeline."""

    def score(self, entries: List[Dict[str, Any]]) -> float:
        """Aggregate single-score wrapper around ``compute_coherence``.

        Returns the mean of per-entry coherence values (matches the
        contract of the legacy ``betweenness_score`` module-level
        function and the API the round-34 nested-mistake
        ``src/graph_coherence/src/graph/coherence.py`` shipped).
        Both consumers now flow through this canonical method.
        """
        return betweenness_score(entries)

    def compute_coherence(self, entries: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Compute graph coherence scores for each entry.
        Returns dict mapping GlobalID to coherence score.
        """
        if not entries:
            return {}

        if nx is None:
            # NetworkX not available, return default scores
            return {
                e.get("GlobalID", f"unknown_{i}"): 0.5 for i, e in enumerate(entries)
            }

        # Build graph
        G = nx.DiGraph()

        # Add nodes
        for e in entries:
            gid = e.get("GlobalID")
            if gid:
                G.add_node(gid, field=e.get("Field", "Unknown"))

        # Build a name -> GlobalID index so advisor/student references can
        # be matched to the GlobalID-keyed nodes. Advisors/Students hold
        # NAME strings (or {name|qid|GlobalID} dicts), NOT GlobalIDs, so
        # the previous ``adv in G`` test was always False (a name is never
        # a GlobalID node) -> edges_added stayed 0 -> the betweenness
        # branch never ran and the score silently fell back to a
        # field-frequency proxy. Resolving references to in-batch GIDs lets
        # real advisor links form edges.
        name_to_gid: Dict[str, str] = {}
        for e in entries:
            gid = e.get("GlobalID")
            if not gid:
                continue
            for key in ("CanonicalLatin", "CanonicalNative", "CanonicalName", "Name"):
                v = e.get(key)
                if isinstance(v, str) and v:
                    name_to_gid.setdefault(v, gid)
                    name_to_gid.setdefault(v.lower(), gid)

        def _resolve(ref: Any) -> Optional[str]:
            # ref may be a GlobalID, a name string, or a {name|qid|GlobalID}
            # dict (the Wikidata-derived advisor shape).
            if isinstance(ref, dict):
                ref = ref.get("GlobalID") or ref.get("name") or ref.get("qid")
            if not isinstance(ref, str) or not ref:
                return None
            if ref in G:  # already a GlobalID node
                return ref
            return name_to_gid.get(ref) or name_to_gid.get(ref.lower())

        # Add edges from relationships
        edges_added = 0
        for e in entries:
            sid = e.get("GlobalID")

            # Advisor relationships (advisor -> student)
            for adv in e.get("Advisors") or []:
                a = _resolve(adv)
                if a and sid and a in G and a != sid:
                    G.add_edge(a, sid)
                    edges_added += 1

            # Student relationships (me -> student)
            for student in e.get("Students") or []:
                s = _resolve(student)
                if s and sid and s in G and s != sid:
                    G.add_edge(sid, s)
                    edges_added += 1

        # Calculate scores
        scores = {}

        if edges_added > 0 and G.number_of_nodes() > 1:
            # Use betweenness centrality
            try:
                # R56: exact betweenness is O(V*E) — fine for the usual
                # few-thousand-node genealogy graphs, intractable at 1M
                # nodes. Above the cutoff, use NetworkX's documented
                # k-source sampling (an unbiased estimator; k pivots
                # instead of all V), which keeps large batches feasible
                # while small graphs stay exact.
                n_nodes = G.number_of_nodes()
                if n_nodes > 10_000:
                    bc = nx.betweenness_centrality(
                        G, normalized=True, k=min(256, n_nodes), seed=42
                    )
                else:
                    bc = nx.betweenness_centrality(G, normalized=True)

                # Also calculate degree centrality for combination
                dc = nx.degree_centrality(G)

                # Combine betweenness and degree centrality
                # Nodes with high betweenness OR high degree should score well
                for gid in G.nodes():
                    b_score = bc.get(gid, 0.0)
                    d_score = dc.get(gid, 0.0)

                    # Weighted combination: 60% betweenness, 40% degree
                    combined = (b_score * 0.6) + (d_score * 0.4)

                    # Scale to 0.3-0.9 range
                    # Nodes with connections get at least 0.4
                    if G.degree(gid) > 0:
                        scores[gid] = max(0.4, min(0.9, 0.4 + combined * 0.5))
                    else:
                        scores[gid] = 0.3  # Isolated nodes

            except Exception as e:
                logger.warning(f"Centrality calculation failed: {e}")
                # Fallback to degree centrality only
                dc = nx.degree_centrality(G)
                for gid, score in dc.items():
                    scores[gid] = 0.4 + (score * 0.4)
        else:
            # Use field-based coherence as fallback
            field_counts = {}
            for e in entries:
                field = e.get("Field", "Unknown")
                field_counts[field] = field_counts.get(field, 0) + 1

            # Assign scores based on field frequency.
            # R56: the previous line was
            #   gid = e.get("GlobalID", f"unknown_{entries.index(e)}")
            # — dict.get evaluates its default EAGERLY, so entries.index(e)
            # (an O(n) scan doing full dict comparisons) ran for EVERY entry
            # even when GlobalID existed: O(n²) overall. Invisible at 4k
            # (~0.1 s); at a 1M batch it projected to DAYS and pinned a core
            # at 100% in PyObject_RichCompare. enumerate() is the O(n) form.
            for i, e in enumerate(entries):
                gid = e.get("GlobalID") or f"unknown_{i}"
                field = e.get("Field", "Unknown")

                if len(entries) > 0:
                    field_freq = field_counts.get(field, 1) / len(entries)
                    scores[gid] = 0.4 + (field_freq * 0.4)
                else:
                    scores[gid] = 0.5

        # Ensure all entries have scores
        for e in entries:
            gid = e.get("GlobalID")
            if gid and gid not in scores:
                scores[gid] = 0.5

        return scores
