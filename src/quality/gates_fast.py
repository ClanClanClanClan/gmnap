from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Set, Tuple


@dataclass
class FastGateConfig:
    profile: str = "prod"  # "test" | "prod"
    stage6_min: float = 0.85
    projected_1m_minutes_max: float = 35.0
    duplicate_external_id_pct_max: float = 0.0
    sample_every_n: int = 1  # 1 = check every batch; higher => sampling
    overhead_budget_pct: float = 10.0  # gates should cost <10% of batch wall time
    remember_cross_batch: bool = True


@dataclass
class FastGateState:
    seen_gids: Set[str] = field(default_factory=set)
    seen_extids: Set[Tuple[str, str]] = field(default_factory=set)
    batch_index: int = 0


class FastQualityGates:
    def __init__(self, cfg: FastGateConfig | None = None):
        self.cfg = cfg or GateConfig()
        self.state = FastGateState()

    def reset(self):
        self.state = FastGateState()

    def _o_n_duplicates(self, entries: Iterable[Dict[str, Any]]) -> Tuple[int, int]:
        seen_local: Set[str] = set()
        dups = 0
        total = 0
        for e in entries:
            gid = e.get("GlobalID")
            if gid is None:
                continue
            total += 1
            if gid in seen_local or (
                self.cfg.remember_cross_batch and gid in self.state.seen_gids
            ):
                dups += 1
            seen_local.add(gid)
        # Update cross-batch memory
        if self.cfg.remember_cross_batch:
            self.state.seen_gids.update(seen_local)
        return dups, total

    def _dup_ext_ids_pct(self, entries: Iterable[Dict[str, Any]]) -> float:
        seen_local: Set[Tuple[str, str]] = set()
        dups = 0
        tot = 0
        for e in entries:
            ext = e.get("ExternalIDs") or []
            for pair in ext:
                src = pair.get("source")
                idv = pair.get("id")
                if not src or not idv:
                    continue
                key = (src, idv)
                tot += 1
                if key in seen_local or (
                    self.cfg.remember_cross_batch and key in self.state.seen_extids
                ):
                    dups += 1
                seen_local.add(key)
        if tot == 0:
            return 0.0
        if self.cfg.remember_cross_batch:
            self.state.seen_extids.update(seen_local)
        return dups / tot

    def check_batch(
        self,
        entries: list[dict],
        perf_minutes_1m: float | None = None,
        stage6_score: float | None = None,
    ) -> Dict[str, Any]:
        """Runs gates with adaptive sampling and a circuit breaker to keep overhead under budget."""
        self.state.batch_index += 1
        if (self.state.batch_index - 1) % max(1, self.cfg.sample_every_n) != 0:
            return {"ok": True, "sampled": True}

        t0 = time.perf_counter()

        # Duplicates
        dup_count, dup_total = self._o_n_duplicates(entries)
        dup_ext_pct = self._dup_ext_ids_pct(entries)

        # Perf gate
        perf_ok = (
            True
            if perf_minutes_1m is None
            else (perf_minutes_1m <= self.cfg.projected_1m_minutes_max)
        )

        # Stage 6 gate
        s6_ok = True if stage6_score is None else (stage6_score >= self.cfg.stage6_min)

        ok = (
            (dup_count == 0)
            and (dup_ext_pct <= self.cfg.duplicate_external_id_pct_max)
            and perf_ok
            and s6_ok
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000
        # If overhead exceeds budget, increase sampling
        # Assume batch wall time is provided by caller or approximate (not known here),
        # so we degrade sampling when single-run > 5ms (~ heuristic), or let caller pass wall time.
        if elapsed_ms > 5.0 and self.cfg.sample_every_n < 16:
            self.cfg.sample_every_n *= 2

        return {
            "ok": ok,
            "dup_in_batch": dup_count,
            "dup_checked": dup_total,
            "dup_ext_pct": dup_ext_pct,
            "perf_minutes_1m_ok": perf_ok,
            "stage6_ok": s6_ok,
            "sample_every_n": self.cfg.sample_every_n,
            "elapsed_ms": elapsed_ms,
        }
