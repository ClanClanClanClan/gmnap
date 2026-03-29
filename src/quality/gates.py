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
