from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from src.graph_coherence.src.graph.coherence import GraphCoherence

DEFAULT_WEIGHTS = {"betweenness_weight": 0.6, "authority_weight": 0.4, "authority_reliability": {}}


class BayesCoherence:
    """Stage 6 Bayesian coherence/confidence layer.
    Combines betweenness (0..1) with an authority‑evidence posterior.
    Rejects short cycles implicitly via GraphCoherence.
    Deterministic for same inputs & weights.
    """

    def __init__(self, weights_path: str = "extras/config/weights.yaml"):
        self.weights = self._load_weights(weights_path)

    def _load_weights(self, p: str) -> Dict[str, Any]:
        if yaml is None:
            return DEFAULT_WEIGHTS
        try:
            d = yaml.safe_load(Path(p).read_text("utf-8"))
            return {**DEFAULT_WEIGHTS, **(d or {})}
        except Exception:
            return DEFAULT_WEIGHTS

    def _authority_confidence(self, entry_sources: List[str]) -> float:
        # Bayesian update with Beta prior (alpha0=1, beta0=1 → uniform)
        alpha, beta = 1.0, 1.0
        rel = self.weights.get("authority_reliability", {})
        for s in sorted(set(entry_sources or [])):
            p = float(rel.get(s, 0.5))
            # Treat each source as one Bernoulli observation with success prob = p
            alpha += p
            beta += 1.0 - p
        return alpha / (alpha + beta)  # 0..1

    def _entries_authority_conf(self, entries: List[Dict[str, Any]]) -> float:
        if not entries:
            return 0.0
        acc = 0.0
        n = 0
        for e in entries:
            srcs = e.get("Sources") or []
            acc += self._authority_confidence(srcs)
            n += 1
        return acc / max(1, n)

    def score(self, entries: List[Dict[str, Any]]) -> Dict[str, float]:
        """Return dict with components and final Stage‑6 score in [0,1]."""
        b_w = float(self.weights.get("betweenness_weight", 0.6))
        a_w = float(self.weights.get("authority_weight", 0.4))
        total_w = max(1e-6, b_w + a_w)
        b_w, a_w = b_w / total_w, a_w / total_w

        betw = GraphCoherence().score(entries)
        auth = self._entries_authority_conf(entries)
        final = max(0.0, min(1.0, b_w * betw + a_w * auth))
        return {"betweenness": betw, "authority_conf": auth, "stage6_score": final}
