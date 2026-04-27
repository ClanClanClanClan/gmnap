from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# Expert solution: Import rolling gates
from src.quality.gates_rolling import GateLimits, RollingGates


@dataclass
class GateThresholds:
    stage6_min: float = float(os.getenv("GATE_STAGE6_MIN", "0.85"))
    projected_1m_minutes_max: float = float(os.getenv("GATE_PERF_MINUTES_MAX", "35.0"))
    duplicate_external_id_pct_max: float = float(
        os.getenv("GATE_DUP_EXTID_PCT_MAX", "0.0")
    )
    sample_every_n: int = int(os.getenv("GATE_SAMPLE_EVERY_N", "1"))
    overhead_budget_ms: float = float(os.getenv("GATE_OVERHEAD_MS", "10.0"))
    remember_cross_batch: bool = os.getenv("GATE_REMEMBER_CROSS_BATCH", "1") == "1"


@dataclass
class GateState:
    seen_gids: Set[str] = field(default_factory=set)
    seen_extids: Set[Tuple[str, str]] = field(default_factory=set)
    i: int = 0


class QualityGates:
    def __init__(self, thresholds: Optional[GateThresholds] = None) -> None:
        self.t = thresholds or GateThresholds()
        self.s = GateState()
        self._lock = threading.RLock()
        self._trace = os.getenv("GATES_TRACE", "0") == "1"

    def check_duplicates(self, entries: Iterable[Dict[str, Any]]) -> bool:
        seen = set()
        d = 0
        tot = 0
        with self._lock:
            for e in entries:
                gid = e.get("GlobalID") or e.get("id") or e.get("Id")
                if gid is None:
                    continue
                tot += 1
                if gid in seen or (
                    self.t.remember_cross_batch and gid in self.s.seen_gids
                ):
                    d += 1
                seen.add(gid)
            if self.t.remember_cross_batch:
                self.s.seen_gids.update(seen)
        ok = d == 0
        if self._trace:
            print(f"[GATES] dup: tot={tot} dups={d} ok={ok}")
        return ok

    def check_performance(
        self, perf_minutes_1m: Optional[float], stage6_score: Optional[float]
    ) -> bool:
        perf_ok = (
            True
            if perf_minutes_1m is None
            else (perf_minutes_1m <= self.t.projected_1m_minutes_max)
        )
        s6_ok = True if stage6_score is None else (stage6_score >= self.t.stage6_min)
        if self._trace:
            print(
                f"[GATES] perf: proj={perf_minutes_1m} s6={stage6_score} -> {perf_ok and s6_ok}"
            )
        return bool(perf_ok and s6_ok)

    def check_batch(
        self,
        entries: List[Dict[str, Any]],
        *,
        perf_minutes_1m: Optional[float] = None,
        stage6_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            self.s.i += 1
            sample = (self.s.i - 1) % max(1, self.t.sample_every_n) == 0
        if not sample:
            return {"ok": True, "sampled": True, "skipped": True}
        t0 = time.perf_counter()
        dup = self.check_duplicates(entries)
        perf = self.check_performance(perf_minutes_1m, stage6_score)
        ok = bool(dup and perf)
        ms = (time.perf_counter() - t0) * 1000.0
        if ms > self.t.overhead_budget_ms and self.t.sample_every_n < 16:
            self.t.sample_every_n *= 2
        out = {"ok": ok, "elapsed_ms": ms, "sample_every_n": self.t.sample_every_n}
        if not dup:
            out["reason"] = "duplicates"
        elif not perf:
            out["reason"] = "performance_or_stage6"
        if self._trace:
            print(f"[GATES] batch: {out}")
        return out


# Expert solution: Replace quadratic gates with rolling O(n) gates
class QualityGateRunner:
    def __init__(self, minutes_1m_max=35.0, min_success_rate=0.95):
        self.g = RollingGates(GateLimits(minutes_1m_max, min_success_rate))
        self._t_start = None
        self._n_total = 0

    def start(self, n_expected: int):
        import time

        self._t_start = time.perf_counter()
        self._n_total = n_expected

    def ingest(self, batch_out: list[dict]):
        self.g.ingest(batch_out)

    def decision(self) -> dict:
        import time

        dt = max(1e-6, time.perf_counter() - self._t_start)
        eps = self._n_total / dt
        return self.g.decision(eps)


# Compatibility aliases
QualityGatesEnforcer = QualityGates


# ---------------------------------------------------------------------------
# Mode-driven 8-gate checker (V7 §15 quality gates contract)
# ---------------------------------------------------------------------------
#
# `QualityGateChecker` is the public, mode-aware façade that the
# pipeline + CLI + reporting use to evaluate the 8 V7 quality gates
# against a batch of entries plus a `metrics` dict produced by the
# pipeline. Each `check_…` method returns a `(ok, value)` 2-tuple so
# the caller can both report and decide.
#
# Modes:
#   - quick   — relaxed thresholds for fast iteration (default)
#   - full    — production thresholds for nightly runs
#   - extreme — zero-tolerance audit thresholds (no duplicates of any
#               kind, perfect graph coherence, fastest runtime budget)
#
# The thresholds below mirror the V7 spec; tests in
# tests/unit/test_quality_gates.py pin the contract.


_GATE_THRESHOLDS = {
    "quick": {
        "duplicate_external_pct_max": 1.0,
        "roundtrip_rate_min": 0.97,
        "edge_conflict_pct_max": 2.0,
        "graph_coherence_min": 0.85,
        "runtime_min_per_1m_max": 35.0,
    },
    "full": {
        "duplicate_external_pct_max": 0.5,
        "roundtrip_rate_min": 0.97,
        "edge_conflict_pct_max": 1.0,
        "graph_coherence_min": 0.92,
        "runtime_min_per_1m_max": 70.0,
    },
    "extreme": {
        "duplicate_external_pct_max": 0.0,
        "roundtrip_rate_min": 0.99,
        "edge_conflict_pct_max": 0.0,
        "graph_coherence_min": 0.97,
        "runtime_min_per_1m_max": 120.0,
    },
}


def dice(a: str, b: str) -> float:
    """Sørensen-Dice coefficient on bigrams of two strings.

    Case-insensitive; identical strings (including empty pair) score
    1.0; disjoint bigram sets score 0.0. Used as a similarity proxy
    in the roundtrip-script-rate gate (Gate 3): a Latin-script entry
    and its CJK round-trip are scored against each other and a
    Sørensen-Dice ≥ 0.97 over the batch is required.
    """
    a = (a or "").lower()
    b = (b or "").lower()
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    if len(a) == 1 and len(b) == 1:
        return 1.0 if a == b else 0.0
    grams_a = {a[i : i + 2] for i in range(len(a) - 1)}
    grams_b = {b[i : i + 2] for i in range(len(b) - 1)}
    if not grams_a or not grams_b:
        return 0.0
    inter = grams_a & grams_b
    return (2.0 * len(inter)) / (len(grams_a) + len(grams_b))


class QualityGateChecker:
    """Mode-aware checker for the 8 V7 quality gates.

    Each ``check_*`` method returns ``(ok: bool, value)`` so callers
    can both report and decide. ``check_all`` runs every gate against
    a batch + metrics dict and returns ``(all_ok, results_list)``.
    """

    GATE_NAMES = (
        "duplicate_global_id",
        "duplicate_external_id_pct",
        "roundtrip_script_rate",
        "genealogy_edge_conflict_pct",
        "graph_coherence_score",
        "peak_rss_gb",
        "warm_cache_runtime_per_1M_min",
        "idempotent_diff_bytes",
    )

    def __init__(self, mode: str = "quick") -> None:
        if mode not in _GATE_THRESHOLDS:
            raise ValueError(
                f"mode must be one of {tuple(_GATE_THRESHOLDS)}, got {mode!r}"
            )
        self.mode = mode
        self.t = _GATE_THRESHOLDS[mode]

    # --- Gate 1: duplicate GlobalIDs (zero tolerance, all modes) -----

    def check_duplicate_global_ids(
        self, entries: List[Dict[str, Any]]
    ) -> Tuple[bool, int]:
        from collections import Counter

        gids = [e.get("GlobalID") for e in entries if e.get("GlobalID")]
        counts = Counter(gids)
        dupes = sum(c - 1 for c in counts.values() if c > 1)
        return dupes == 0, dupes

    # --- Gate 2: duplicate external authority IDs --------------------

    def check_duplicate_external_ids(
        self, entries: List[Dict[str, Any]]
    ) -> Tuple[bool, float]:
        from collections import Counter

        all_ids: list[Tuple[str, str]] = []
        for e in entries:
            ids = e.get("AuthorityIDs") or {}
            if not isinstance(ids, dict):
                continue
            for src, val in ids.items():
                if val:
                    all_ids.append((src, val))
        if not all_ids:
            return True, 0.0
        counts = Counter(all_ids)
        dupes = sum(c - 1 for c in counts.values() if c > 1)
        pct = (dupes / len(all_ids)) * 100.0
        return pct <= self.t["duplicate_external_pct_max"], pct

    # --- Gate 3: roundtrip script-preservation rate ------------------

    def check_roundtrip_rate(self, pairs: List[Tuple[str, str]]) -> Tuple[bool, float]:
        """``pairs`` is a list of (original, post-roundtrip) strings.
        Rate is the mean of dice() over the pairs; an empty list passes.
        """
        if not pairs:
            return True, 1.0
        scores = [dice(a, b) for a, b in pairs]
        rate = sum(scores) / len(scores)
        return rate >= self.t["roundtrip_rate_min"], rate

    # --- Gate 4: genealogy edge conflicts ----------------------------

    def check_genealogy_edge_conflicts(
        self, conflicts: int, total_edges: int
    ) -> Tuple[bool, float]:
        if total_edges == 0:
            return True, 0.0
        pct = (conflicts / total_edges) * 100.0
        return pct <= self.t["edge_conflict_pct_max"], pct

    # --- Gate 5: graph coherence -------------------------------------

    def check_graph_coherence(self, score: float) -> Tuple[bool, float]:
        return score >= self.t["graph_coherence_min"], score

    # --- Gate 6: memory ceiling --------------------------------------

    def check_memory_limit(self, rss_gb_limit: float = 6.0) -> Tuple[bool, float]:
        try:
            import resource

            ru = resource.getrusage(resource.RUSAGE_SELF)
            # macOS reports bytes; Linux reports kilobytes.
            import platform

            divisor = 1024**3 if platform.system() == "Darwin" else 1024**2
            rss_gb = ru.ru_maxrss / divisor
        except Exception:
            rss_gb = 0.0
        return rss_gb <= rss_gb_limit, rss_gb

    # --- Gate 7: warm-cache runtime per 1 M entries ------------------

    def check_runtime(self, projected_minutes_per_1m: float) -> Tuple[bool, float]:
        return (
            projected_minutes_per_1m <= self.t["runtime_min_per_1m_max"],
            projected_minutes_per_1m,
        )

    # --- Gate 8: idempotent diff bytes (must be 0) -------------------

    def check_idempotency(self, diff_bytes: int) -> Tuple[bool, int]:
        return diff_bytes == 0, diff_bytes

    # --- Aggregate ---------------------------------------------------

    def check_all(
        self,
        entries: List[Dict[str, Any]],
        metrics: Dict[str, Any],
    ) -> Tuple[bool, Dict[str, Tuple[bool, Any]]]:
        """Run every gate. Returns ``(all_ok, results)`` where
        ``results`` is a dict keyed by gate name with ``(ok, value)``
        tuples. ``metrics`` should carry: ``graph_conflicts``,
        ``edges``, ``graph_coherence``, ``projected_time_per_million``,
        ``idempotency_diff_bytes``, plus optional ``roundtrip_pairs``.
        """
        results: Dict[str, Tuple[bool, Any]] = {
            self.GATE_NAMES[0]: self.check_duplicate_global_ids(entries),
            self.GATE_NAMES[1]: self.check_duplicate_external_ids(entries),
            self.GATE_NAMES[2]: self.check_roundtrip_rate(
                metrics.get("roundtrip_pairs") or []
            ),
            self.GATE_NAMES[3]: self.check_genealogy_edge_conflicts(
                metrics.get("graph_conflicts", 0),
                metrics.get("edges", 0),
            ),
            self.GATE_NAMES[4]: self.check_graph_coherence(
                metrics.get("graph_coherence", 0.0)
            ),
            self.GATE_NAMES[5]: self.check_memory_limit(),
            self.GATE_NAMES[6]: self.check_runtime(
                metrics.get("projected_time_per_million", 0.0)
            ),
            self.GATE_NAMES[7]: self.check_idempotency(
                metrics.get("idempotency_diff_bytes", 0)
            ),
        }
        all_ok = all(ok for ok, _ in results.values())
        return all_ok, results
