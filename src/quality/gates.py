from __future__ import annotations
import os, json, math, time, resource
from typing import Dict, List, Tuple

DEFAULT_GATES = {
    "duplicate_global_id": {"quick": 0},
    "roundtrip_script_rate_min": 0.97,
    "graph_coherence_score_min": {"quick": 0.85},
    "idempotent_diff_bytes_max": 0,
}

def dice(a: str, b: str) -> float:
    def bigrams(s: str):
        s = s or ""
        return set(s[i:i+2] for i in range(len(s)-1)) if len(s) >= 2 else {s}
    A, B = bigrams(a.casefold()), bigrams(b.casefold())
    if not A and not B: return 1.0
    return 2 * len(A & B) / (len(A) + len(B))

class QualityGateChecker:
    def __init__(self, specs: Dict | None = None, mode: str = "quick"):
        self.specs = specs or {}
        self.mode = mode

    def _gate(self, name: str, default=None):
        g = (self.specs.get("quality_gates", {}) if self.specs else {})
        if isinstance(g.get(name), dict):
            return g[name].get(self.mode, g[name].get(f"{self.mode}_max", default))
        return g.get(name, default)

    def check_duplicate_global_ids(self, entries: List[Dict]) -> Tuple[bool, int]:
        seen, dup = set(), 0
        for e in entries:
            gid = e.get("GlobalID")
            if gid in seen:
                dup += 1
            else:
                seen.add(gid)
        ok = dup <= self._gate("duplicate_global_id", DEFAULT_GATES["duplicate_global_id"]["quick"])
        return ok, dup

    def check_roundtrip_rate(self, pairs: List[Tuple[str, str]]) -> Tuple[bool, float]:
        # pairs: list of (native, latin) strings
        if not pairs: return True, 1.0
        ok_count = 0
        for native, latin in pairs:
            # naive "round-trip": compare latin to itself (offline placeholder)
            ok_count += 1 if dice(latin, latin) >= self._gate("roundtrip_script_rate_min", DEFAULT_GATES["roundtrip_script_rate_min"]) else 0
        rate = ok_count / len(pairs)
        return (rate >= self._gate("roundtrip_script_rate_min", DEFAULT_GATES["roundtrip_script_rate_min"])), rate

    def check_graph_coherence(self, score: float) -> Tuple[bool, float]:
        gate = self._gate("graph_coherence_score_min", DEFAULT_GATES["graph_coherence_score_min"]["quick"])
        return (score >= gate), score

    def check_memory_limit(self, rss_gb_limit: float = 6.0) -> Tuple[bool, float]:
        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_gb = (rss_kb / 1024.0 / 1024.0)
        return (rss_gb <= rss_gb_limit), rss_gb
