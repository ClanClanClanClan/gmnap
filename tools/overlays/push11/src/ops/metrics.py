from __future__ import annotations

try:
    from prometheus_client import Counter as _PCounter
    from prometheus_client import Gauge as _PGauge
    from prometheus_client import Histogram as _PHist
except Exception:  # pragma: no cover
    _PCounter = _PGauge = _PHist = None


class _NoOp:
    def __init__(self, *_args, **_kwargs):
        pass

    def labels(self, *a, **k):
        return self

    def inc(self, v: float = 1.0):
        pass

    def dec(self, v: float = 1.0):
        pass

    def set(self, v: float):
        pass

    def observe(self, v: float):
        pass


def Counter(name: str, desc: str = ""):
    if _PCounter is None:
        return _NoOp()
    return _PCounter(name, desc)


def Gauge(name: str, desc: str = ""):
    if _PGauge is None:
        return _NoOp()
    return _PGauge(name, desc)


def Histogram(name: str, desc: str = "", buckets=None):
    if _PHist is None:
        return _NoOp()
    if buckets is None:
        return _PHist(name, desc)
    return _PHist(name, desc, buckets=buckets)


# Shared metrics
WRITE_DIFF_CHANGED_ENTRIES = Gauge(
    "gmnap_write_diff_changed_entries", "Changed entries reported by Stage 9"
)
POOL_IN_USE = Gauge("gmnap_db_pool_in_use", "DB pool connections in use")
POOL_AVAIL = Gauge("gmnap_db_pool_available", "DB pool connections available")
TX_SUCCESS = Counter("gmnap_db_tx_success_total", "Successful DB transactions")
TX_ROLLBACK = Counter("gmnap_db_tx_rollback_total", "Rolled back DB transactions")
AUTH_FAILS = Counter("gmnap_auth_fail_total", "Authentication failures")
AUTH_OK = Counter("gmnap_auth_ok_total", "Authentication successes")
DB_APPLY_QUERIES = Counter(
    "gmnap_db_apply_queries_total", "Queries applied from changelog"
)

# Stage 10 freshness
STAGE10_LAST_SUCCESS = Gauge(
    "gmnap_stage10_report_last_success", "Unix time of last successful Stage 10 report"
)

# Stage 11 idempotency
IDEMP_DIFF_BYTES = Gauge(
    "gmnap_idempotency_diff_bytes", "Byte-diff of canonical outputs between runs"
)
IDEMP_OK_TOTAL = Counter("gmnap_idempotency_ok_total", "Successful idempotency checks")
IDEMP_FAIL_TOTAL = Counter("gmnap_idempotency_fail_total", "Failed idempotency checks")

# Pipeline timing (used by Push 12)
STAGE_DURATION = Histogram(
    "gmnap_stage_duration_seconds",
    "Duration per stage",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60],
)
PIPELINE_THROUGHPUT = Gauge(
    "gmnap_pipeline_entries_per_sec", "Instantaneous throughput (entries/sec)"
)
PIPELINE_LAT_P95 = Gauge(
    "gmnap_pipeline_latency_p95_seconds", "p95 latency per batch (seconds)"
)
