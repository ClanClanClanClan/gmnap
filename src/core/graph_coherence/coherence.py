from __future__ import annotations

import logging
from typing import Any, Dict, List

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

        # Add edges from relationships
        edges_added = 0
        for e in entries:
            sid = e.get("GlobalID")

            # Advisor relationships
            for adv in e.get("Advisors") or []:
                if adv and sid and adv in G:
                    G.add_edge(adv, sid)
                    edges_added += 1

            # Student relationships
            for student in e.get("Students") or []:
                if student and sid and student in G:
                    G.add_edge(sid, student)
                    edges_added += 1

        # Calculate scores
        scores = {}

        if edges_added > 0 and G.number_of_nodes() > 1:
            # Use betweenness centrality
            try:
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

            # Assign scores based on field frequency
            for e in entries:
                gid = e.get("GlobalID", f"unknown_{entries.index(e)}")
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
