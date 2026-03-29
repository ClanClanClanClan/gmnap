from __future__ import annotations
from typing import List, Dict, Any

try:
    import networkx as nx
except Exception:
    nx = None


class GraphCoherence:
    """Offline graph coherence using NetworkX betweenness with small‑cycle penalty."""

    def __init__(self):
        pass

    def _edges_from_entries(self, entries):
        for e in entries:
            sid = e.get("GlobalID")
            for adv in e.get("Advisors", []) or []:
                if adv and sid:
                    yield (adv, sid)

    def score(self, entries: List[Dict[str, Any]]) -> float:
        if nx is None:
            return 0.0
        G = nx.DiGraph()
        for e in entries:
            gid = e.get("GlobalID")
            if gid:
                G.add_node(gid)
        for u, v in self._edges_from_entries(entries):
            G.add_edge(u, v)
        if G.number_of_nodes() == 0:
            return 0.0
        bc = nx.betweenness_centrality(G, normalized=True)
        base = sum(bc.values()) / max(1, len(bc))  # 0..1-ish
        # Penalise short cycles (<3)
        penalty = 0.0
        try:
            for cyc in nx.simple_cycles(G):
                if len(cyc) < 3:
                    penalty += 0.05
        except Exception:
            pass
        return max(0.0, min(1.0, base - penalty))
