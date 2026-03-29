from __future__ import annotations

import logging
from typing import Any, Dict, List

try:
    import networkx as nx  # type: ignore
except Exception:
    nx = None

logger = logging.getLogger(__name__)


def compute_betweenness_scores(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Compute betweenness centrality scores for each entry.
    Returns dict mapping GlobalID to coherence score.
    """
    if nx is None or not entries:
        return {e.get("GlobalID", f"unknown_{i}"): 0.5 for i, e in enumerate(entries)}

    # Build directed graph from advisor relationships
    G = nx.DiGraph()

    # Add all nodes
    for e in entries:
        gid = e.get("GlobalID")
        if gid:
            G.add_node(
                gid,
                **{
                    "Field": e.get("Field", "Unknown"),
                    "Name": e.get("CanonicalLatin", "Unknown"),
                },
            )

    # Add edges from advisor relationships
    edges_added = 0
    for e in entries:
        sid = e.get("GlobalID")

        # Check Advisors field
        for adv in e.get("Advisors") or []:
            if adv and sid and adv in G:
                G.add_edge(adv, sid, relation="advisor")
                edges_added += 1

        # Check Students field
        for student in e.get("Students") or []:
            if student and sid and student in G:
                G.add_edge(sid, student, relation="advisor")
                edges_added += 1

    logger.info(
        f"Graph built with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges"
    )

    # Calculate betweenness centrality if we have edges
    if edges_added > 0 and G.number_of_nodes() > 1:
        try:
            # Calculate betweenness centrality
            bc = nx.betweenness_centrality(G, normalized=True)

            # Scale scores to reasonable range (0.3 to 0.9)
            max_bc = max(bc.values()) if bc.values() else 1.0
            if max_bc > 0:
                scores = {
                    gid: 0.3 + (score / max_bc * 0.6) for gid, score in bc.items()
                }
            else:
                scores = {gid: 0.5 for gid in bc.keys()}

            # Add default scores for nodes not in centrality calculation
            for e in entries:
                gid = e.get("GlobalID")
                if gid and gid not in scores:
                    scores[gid] = 0.5

            return scores

        except Exception as e:
            logger.warning(f"Betweenness centrality calculation failed: {e}")

    # Fallback: Use field-based coherence
    return compute_field_coherence(entries, G)


def compute_field_coherence(
    entries: List[Dict[str, Any]], G: nx.DiGraph = None
) -> Dict[str, float]:
    """
    Compute coherence based on field similarity.
    Higher scores for entries in common fields.
    """
    # Count field frequencies
    field_counts = {}
    total_entries = len(entries)

    for e in entries:
        field = e.get("Field", "Unknown")
        field_counts[field] = field_counts.get(field, 0) + 1

    # Assign scores based on field commonality
    scores = {}
    for e in entries:
        gid = e.get("GlobalID", f"unknown_{entries.index(e)}")
        field = e.get("Field", "Unknown")

        if total_entries > 0:
            # Higher score for more common fields (network effect)
            field_frequency = field_counts.get(field, 1) / total_entries

            # Score between 0.4 and 0.8 based on field frequency
            score = 0.4 + (field_frequency * 0.4)

            # Boost score if entry has relationships
            if G and gid in G:
                degree = G.degree(gid)
                if degree > 0:
                    score = min(0.9, score + 0.1)
        else:
            score = 0.5

        scores[gid] = score

    return scores


class GraphCoherence:
    """
    Graph coherence analyzer for V7 pipeline.
    Computes individual coherence scores for each entry.
    """

    def compute_coherence(self, entries: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Compute graph coherence scores for entries.

        Args:
            entries: List of entry dictionaries

        Returns:
            Dictionary mapping GlobalID to coherence score
        """
        if not entries:
            return {}

        # Compute individual scores
        scores = compute_betweenness_scores(entries)

        # Log statistics
        if scores:
            avg_score = sum(scores.values()) / len(scores)
            min_score = min(scores.values())
            max_score = max(scores.values())
            logger.info(
                f"Coherence scores - Avg: {avg_score:.3f}, Min: {min_score:.3f}, Max: {max_score:.3f}"
            )

        return scores

    def apply_scores_to_entries(
        self, entries: List[Dict[str, Any]], scores: Dict[str, float]
    ) -> None:
        """
        Apply coherence scores to entries in-place.

        Args:
            entries: List of entries to update
            scores: Dictionary of GlobalID to score mappings
        """
        for entry in entries:
            gid = entry.get("GlobalID")
            if gid and gid in scores:
                entry["GraphCoherence"] = scores[gid]
            else:
                # Default score for entries without GlobalID
                entry["GraphCoherence"] = 0.5
