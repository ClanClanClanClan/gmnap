from __future__ import annotations

import contextlib
import time

from .metrics import PIPELINE_LAT_P95, PIPELINE_THROUGHPUT, STAGE_DURATION


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
