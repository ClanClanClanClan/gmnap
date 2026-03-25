"""Quality gate checks for V7 pipeline (specs_v7.yaml section 7).

All 8 gates with mode-specific thresholds per V7 spec.
"""

from __future__ import annotations

import platform
import resource
from typing import Dict, List, Tuple

DEFAULT_GATES = {
    "duplicate_global_id": {"quick": 0, "full": 0, "extreme": 0},
    "duplicate_external_id_pct": {"quick_max": 0.10, "full_max": 0.05, "extreme_max": 0},
    "roundtrip_script_rate_min": 0.97,
    "genealogy_edge_conflict_pct": {"quick_max": 2.0, "full_max": 1.0, "extreme_max": 0.0},
    "graph_coherence_score_min": {"quick": 0.85, "full": 0.92, "extreme": 0.97},
    "peak_rss_gb_on_2M": 6,
    "warm_cache_runtime_per_1M_min": {"quick": 35, "full": 70},
    "idempotent_diff_bytes_max": 0,
}


def dice(a: str, b: str) -> float:
    """Sørensen-Dice coefficient for two strings."""

    def bigrams(s: str):
        s = s or ""
        return set(s[i : i + 2] for i in range(len(s) - 1)) if len(s) >= 2 else {s}

    A, B = bigrams(a.casefold()), bigrams(b.casefold())
    if not A and not B:
        return 1.0
    return 2 * len(A & B) / (len(A) + len(B))


class QualityGateChecker:
    """Check all 8 V7 quality gates with mode-specific thresholds."""

    def __init__(self, specs: Dict | None = None, mode: str = "quick"):
        self.specs = specs or {}
        self.mode = mode

    def _gate(self, name: str, default=None):
        """Look up a gate value, resolving mode-specific dicts."""
        g = self.specs.get("quality_gates", {}) if self.specs else {}
        val = g.get(name, DEFAULT_GATES.get(name, default))
        if isinstance(val, dict):
            return val.get(self.mode, val.get(f"{self.mode}_max", default))
        return val

    def check_duplicate_global_ids(self, entries: List[Dict]) -> Tuple[bool, int]:
        """Gate 1: duplicate_global_id must be 0 in all modes."""
        seen, dup = set(), 0
        for e in entries:
            gid = e.get("GlobalID")
            if gid in seen:
                dup += 1
            else:
                seen.add(gid)
        limit = self._gate("duplicate_global_id", 0)
        return dup <= limit, dup

    def check_duplicate_external_ids(self, entries: List[Dict]) -> Tuple[bool, float]:
        """Gate 2: duplicate_external_id_pct (Quick ≤0.10%, Full ≤0.05%, Extreme 0%)."""
        if not entries:
            return True, 0.0
        ext_ids = []
        for e in entries:
            for source, val in (e.get("AuthorityIDs") or {}).items():
                eid = (
                    val
                    if isinstance(val, str)
                    else (val.get("id") if isinstance(val, dict) else str(val))
                )
                ext_ids.append(f"{source}:{eid}")
        seen, dup = set(), 0
        for eid in ext_ids:
            if eid in seen:
                dup += 1
            else:
                seen.add(eid)
        pct = (dup / max(len(entries), 1)) * 100
        limit = self._gate("duplicate_external_id_pct", 0.10)
        return pct <= limit, pct

    def check_roundtrip_rate(self, pairs: List[Tuple[str, str]]) -> Tuple[bool, float]:
        """Gate 3: roundtrip_script_rate_min ≥ 0.97.

        pairs: list of (native, latin) strings.
        Compares native script to Latin transliteration using Dice coefficient.
        """
        if not pairs:
            return True, 1.0
        threshold = self._gate("roundtrip_script_rate_min", 0.97)
        ok_count = 0
        for native, latin in pairs:
            score = dice(native, latin) if native != latin else 1.0
            ok_count += 1 if score >= threshold else 0
        rate = ok_count / len(pairs)
        return rate >= threshold, rate

    def check_genealogy_edge_conflicts(
        self, conflict_count: int, total_edges: int
    ) -> Tuple[bool, float]:
        """Gate 4: genealogy_edge_conflict_pct (Quick ≤2%, Full ≤1%, Extreme 0%)."""
        if total_edges == 0:
            return True, 0.0
        pct = (conflict_count / total_edges) * 100
        limit = self._gate("genealogy_edge_conflict_pct", 2.0)
        return pct <= limit, pct

    def check_graph_coherence(self, score: float) -> Tuple[bool, float]:
        """Gate 5: graph_coherence_score_min (Quick ≥0.85, Full ≥0.92, Extreme ≥0.97)."""
        gate = self._gate("graph_coherence_score_min", 0.85)
        return score >= gate, score

    def check_memory_limit(self, rss_gb_limit: float | None = None) -> Tuple[bool, float]:
        """Gate 6: peak_rss_gb_on_2M ≤ 6GB."""
        if rss_gb_limit is None:
            rss_gb_limit = self._gate("peak_rss_gb_on_2M", 6)
        ru = resource.getrusage(resource.RUSAGE_SELF)
        if platform.system() == "Darwin":
            rss_gb = ru.ru_maxrss / (1024 * 1024 * 1024)
        else:
            rss_gb = ru.ru_maxrss / (1024 * 1024)
        return rss_gb <= rss_gb_limit, rss_gb

    def check_runtime(self, projected_minutes: float) -> Tuple[bool, float]:
        """Gate 7: warm_cache_runtime_per_1M_min (Quick ≤35, Full ≤70)."""
        limit = self._gate("warm_cache_runtime_per_1M_min", 35)
        if limit is None:
            return True, projected_minutes
        return projected_minutes <= limit, projected_minutes

    def check_idempotency(self, diff_bytes: int) -> Tuple[bool, int]:
        """Gate 8: idempotent_diff_bytes_max must be 0."""
        limit = self._gate("idempotent_diff_bytes_max", 0)
        return diff_bytes <= limit, diff_bytes

    def check_all(
        self, entries: List[Dict], metrics: Dict
    ) -> Tuple[bool, Dict[str, Tuple[bool, float]]]:
        """Run all 8 quality gates and return (all_passed, {gate_name: (passed, value)})."""
        results = {}

        ok, val = self.check_duplicate_global_ids(entries)
        results["duplicate_global_id"] = (ok, val)

        ok, val = self.check_duplicate_external_ids(entries)
        results["duplicate_external_id_pct"] = (ok, val)

        pairs = [(e.get("CanonicalNative", ""), e.get("CanonicalLatin", "")) for e in entries]
        ok, val = self.check_roundtrip_rate(pairs)
        results["roundtrip_script_rate"] = (ok, val)

        ok, val = self.check_genealogy_edge_conflicts(
            metrics.get("graph_conflicts", 0), metrics.get("edges", 0)
        )
        results["genealogy_edge_conflict_pct"] = (ok, val)

        ok, val = self.check_graph_coherence(metrics.get("graph_coherence", 0.95))
        results["graph_coherence_score"] = (ok, val)

        ok, val = self.check_memory_limit()
        results["peak_rss_gb"] = (ok, val)

        ok, val = self.check_runtime(metrics.get("projected_time_per_million", 0))
        results["runtime_per_1M"] = (ok, val)

        ok, val = self.check_idempotency(metrics.get("idempotency_diff_bytes", 0))
        results["idempotent_diff_bytes"] = (ok, val)

        all_passed = all(v[0] for v in results.values())
        return all_passed, results
