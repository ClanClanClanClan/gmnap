from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Set, Tuple, Iterable
import time


@dataclass
class GateConfig:
    stage6_min: float = 0.85
    projected_1m_minutes_max: float = 35.0
    duplicate_external_id_pct_max: float = 0.0
    sample_every_n: int = 4  # sample by default for small batches
    overhead_budget_ms: float = 5.0  # keep checks ultra-cheap
    remember_cross_batch: bool = True


@dataclass
class GateState:
    seen_gids: Set[str] = field(default_factory=set)
    seen_extids: Set[Tuple[str, str]] = field(default_factory=set)
    i: int = 0


class FastSmallBatchGates:
    def __init__(self, cfg: GateConfig | None = None):
        self.cfg = cfg or GateConfig()
        self.s = GateState()

    def _dups(self, entries: Iterable[Dict[str, Any]]) -> tuple[int, int]:
        seen = set()
        d = 0
        t = 0
        for e in entries:
            gid = e.get("GlobalID") or e.get("id")
            if gid is None:
                continue
            t += 1
            if gid in seen or (self.cfg.remember_cross_batch and gid in self.s.seen_gids):
                d += 1
            seen.add(gid)
        if self.cfg.remember_cross_batch:
            self.s.seen_gids.update(seen)
        return d, t

    def _dup_ext(self, entries: Iterable[Dict[str, Any]]) -> float:
        seen = set()
        d = 0
        t = 0
        for e in entries:
            for pair in e.get("ExternalIDs") or []:
                k = (pair.get("source"), pair.get("id"))
                if not all(k):
                    continue
                t += 1
                if k in seen or (self.cfg.remember_cross_batch and k in self.s.seen_extids):
                    d += 1
                seen.add(k)
        if t == 0:
            return 0.0
        if self.cfg.remember_cross_batch:
            self.s.seen_extids.update(seen)
        return d / t

    def check_batch(
        self,
        entries: List[Dict[str, Any]],
        perf_minutes_1m: float | None = None,
        stage6_score: float | None = None,
    ) -> Dict[str, Any]:
        self.s.i += 1
        if (self.s.i - 1) % max(1, self.cfg.sample_every_n) != 0:
            return {"ok": True, "sampled": True, "skipped": True}
        t0 = time.perf_counter()
        d, t = self._dups(entries)
        ext = self._dup_ext(entries)
        perf_ok = (
            True
            if perf_minutes_1m is None
            else (perf_minutes_1m <= self.cfg.projected_1m_minutes_max)
        )
        s6_ok = True if stage6_score is None else (stage6_score >= self.cfg.stage6_min)
        ok = (d == 0) and (ext <= self.cfg.duplicate_external_id_pct_max) and perf_ok and s6_ok
        ms = (time.perf_counter() - t0) * 1000.0
        # If still too slow, relax sampling further
        if ms > self.cfg.overhead_budget_ms and self.cfg.sample_every_n < 16:
            self.cfg.sample_every_n *= 2
        return {
            "ok": ok,
            "ms": ms,
            "every": self.cfg.sample_every_n,
            "dup": d,
            "checked": t,
            "ext_pct": ext,
        }
