from __future__ import annotations

import json
import os
import time
import tracemalloc
from dataclasses import asdict, dataclass
from typing import List, Optional

import psutil


@dataclass
class StageEvent:
    stage: str
    started_ns: int
    ended_ns: int
    ok: bool
    error: Optional[str]
    rss_mb_before: float
    rss_mb_after: float
    top_alloc: List[str]


class FlightRecorder:
    def __init__(self, out_path: str = "/tmp/gmnap_flight.jsonl", top_k: int = 5):
        self.out_path = out_path
        self.top_k = top_k
        tracemalloc.start()

    def _rss_mb(self) -> float:
        p = psutil.Process(os.getpid())
        return p.memory_info().rss / (1024 * 1024)

    def stage(self, name: str):
        class _Ctx:
            def __init__(self, outer: "FlightRecorder", nm: str):
                self.o = outer
                self.nm = nm

            async def __aenter__(self):
                self.t0 = time.perf_counter_ns()
                self.r0 = self.o._rss_mb()
                return self

            async def __aexit__(self, exc_type, exc, tb):
                t1 = time.perf_counter_ns()
                r1 = self.o._rss_mb()
                stats = tracemalloc.take_snapshot().statistics("lineno")[: self.o.top_k]
                top = [str(s.traceback[0]) for s in stats]
                ev = StageEvent(
                    self.nm,
                    self.t0,
                    t1,
                    exc is None,
                    None if exc is None else f"{exc_type.__name__}: {exc}",
                    self.r0,
                    r1,
                    top,
                )
                with open(self.o.out_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(ev), ensure_ascii=False) + "\n")
                # do not suppress exception
                return False

        return _Ctx(self, name)
