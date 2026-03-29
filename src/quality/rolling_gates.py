from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Set, Iterable


@dataclass
class RollingState:
    seen_gids: Set[str] = field(default_factory=set)
    total: int = 0
    ok: int = 0
    err: int = 0


@dataclass
class RollingLimits:
    minutes_1m_max: float = 35.0
    min_success_rate: float = 0.95


class RollingGates:
    def __init__(self, limits: RollingLimits | None = None):
        self.l = limits or RollingLimits()
        self.s = RollingState()

    def ingest(self, entries: Iterable[Dict[str, Any]]):
        dups = 0
        c = 0
        for e in entries:
            gid = e.get("GlobalID") or e.get("id")
            if gid:
                dups += 1 if gid in self.s.seen_gids else 0
                self.s.seen_gids.add(gid)
            c += 1
            if e.get("status") == "processing_error":
                self.s.err += 1
            else:
                self.s.ok += 1
        self.s.total += c
        return {"dups": dups, "total": c}

    def decision(self, eps: float) -> Dict[str, Any]:
        if eps <= 0:
            return {"ok": False, "reason": "no_throughput"}
        minutes_1m = (1_000_000 / eps) / 60.0
        sr = self.s.ok / max(1, self.s.total)
        ok = (minutes_1m <= self.l.minutes_1m_max) and (sr >= self.l.min_success_rate)
        return {
            "ok": ok,
            "minutes_1m": minutes_1m,
            "success_rate": sr,
            "seen": self.s.total,
        }
