from __future__ import annotations
import time, contextlib
from .metrics import STAGE_DURATION, PIPELINE_THROUGHPUT, PIPELINE_LAT_P95


@contextlib.contextmanager
def stage_timer(stage_name: str, entries: int | None = None):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        STAGE_DURATION.labels(stage=stage_name).observe(dt)
        if entries:
            try:
                rate = entries / dt if dt > 0 else 0.0
                PIPELINE_THROUGHPUT.set(rate)
            except Exception:
                pass
