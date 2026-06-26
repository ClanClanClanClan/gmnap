from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Set


@dataclass
class RollingGateLimits:
    minutes_1m_max: float = 35.0
    min_success_rate: float = 0.95


@dataclass
class RollingGateState:
    seen: int = 0
    ok: int = 0
    err: int = 0
    seen_ids: Set[str] = field(default_factory=set)


class RollingGates:
    def __init__(self, limits: RollingGateLimits | None = None):
        self.l = limits or GateLimits()
        self.s = RollingGateState()

    def ingest(self, batch_out):
        for r in batch_out:
            gid = r.get("GlobalID") or r.get("id")
            if gid:
                self.s.seen_ids.add(gid)
            self.s.seen += 1
            if r.get("status") == "processing_error":
                self.s.err += 1
            else:
                self.s.ok += 1

    def decision(self, eps: float) -> Dict[str, Any]:
        if eps <= 0:
            return {"ok": False, "reason": "throughput_zero"}
        minutes_1m = (1_000_000 / eps) / 60.0
        sr = self.s.ok / max(1, self.s.seen)
        ok = (minutes_1m <= self.l.minutes_1m_max) and (sr >= self.l.min_success_rate)
        return {
            "ok": ok,
            "minutes_1m": minutes_1m,
            "success_rate": sr,
            "seen": self.s.seen,
            "unique": len(self.s.seen_ids),
        }
