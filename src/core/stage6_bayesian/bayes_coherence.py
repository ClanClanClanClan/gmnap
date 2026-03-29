from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from src.core.graph_coherence.coherence import betweenness_score

DEFAULT = {
    "betweenness_weight": 0.6,
    "authority_weight": 0.4,
    "authority_reliability": {},
}


class BayesCoherence:
    def __init__(self, weights_path: str = "extras/config/weights.yaml"):
        self.weights = self._load(weights_path)

    def _load(self, p: str) -> Dict[str, Any]:
        if yaml is None:
            return DEFAULT
        try:
            d = yaml.safe_load(Path(p).read_text("utf-8"))
            return {**DEFAULT, **(d or {})}
        except Exception:
            return DEFAULT

    def _auth_conf(self, sources: List[str]) -> float:
        alpha, beta = 1.0, 1.0  # uniform prior
        rel = self.weights.get("authority_reliability", {})
        for s in sorted(set(sources or [])):
            p = float(rel.get(s, 0.5))
            alpha += p
            beta += 1.0 - p
        return alpha / (alpha + beta)

    def _avg_auth_conf(self, entries: List[Dict[str, Any]]) -> float:
        if not entries:
            return 0.0
        tot = 0.0
        for e in entries:
            tot += self._auth_conf(e.get("Sources") or [])
        return tot / max(1, len(entries))

    def score(self, entries: List[Dict[str, Any]]) -> Dict[str, float]:
        b = betweenness_score(entries)
        a = self._avg_auth_conf(entries)
        bw = float(self.weights.get("betweenness_weight", 0.6))
        aw = float(self.weights.get("authority_weight", 0.4))
        s = max(1e-9, bw + aw)
        bw, aw = bw / s, aw / s
        final = max(0.0, min(1.0, bw * b + aw * a))
        return {"betweenness": b, "authority_conf": a, "stage6_score": final}
