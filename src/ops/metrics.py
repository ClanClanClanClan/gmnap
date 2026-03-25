from __future__ import annotations

try:
    from prometheus_client import Counter as _PCounter, Gauge as _PGauge
except Exception:  # pragma: no cover
    _PCounter = _PGauge = None


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


def Counter(name: str, desc: str = "", labelnames: list = None):
    if _PCounter is None:
        return _NoOp()
    if labelnames:
        return _PCounter(name, desc, labelnames=labelnames)
    return _PCounter(name, desc)


def Gauge(name: str, desc: str = "", labelnames: list = None):
    if _PGauge is None:
        return _NoOp()
    if labelnames:
        return _PGauge(name, desc, labelnames=labelnames)
    return _PGauge(name, desc)


# Common metrics used across stages
WRITE_DIFF_CHANGED_ENTRIES = Gauge(
    "gmnap_write_diff_changed_entries", "Changed entries reported by Stage 9"
)
POOL_IN_USE = Gauge("gmnap_db_pool_in_use", "DB pool connections in use")
POOL_AVAIL = Gauge("gmnap_db_pool_available", "DB pool connections available")
TX_SUCCESS = Counter("gmnap_db_tx_success_total", "Successful DB transactions")
TX_ROLLBACK = Counter("gmnap_db_tx_rollback_total", "Rolled back DB transactions")
AUTH_FAILS = Counter("gmnap_auth_fail_total", "Authentication failures")
AUTH_OK = Counter("gmnap_auth_ok_total", "Authentication successes")
DB_APPLY_QUERIES = Counter("gmnap_db_apply_queries_total", "Queries applied from changelog")

# Stage 8 metrics
SCHEMA_VALIDATION_ERRORS = Counter(
    "gmnap_schema_validation_errors_total", "Schema validation errors", labelnames=["field"]
)
ROUNDTRIP_FAILURES = Counter(
    "gmnap_roundtrip_failures_total", "Roundtrip validation failures", labelnames=["region"]
)
PROCESSED_TOTAL = Counter("gmnap_processed_total", "Total entries processed", labelnames=["stage"])

# Stage 10 metrics
REPORTS_EMITTED = Counter("gmnap_reports_emitted_total", "Reports generated")
DOI_DRAFTS_CREATED = Counter("gmnap_doi_drafts_created_total", "DOI drafts created")

# Stage 11 idempotency metrics
IDEMP_DIFF_BYTES = Gauge("gmnap_idempotency_diff_bytes", "Idempotency check difference in bytes")
IDEMP_OK_TOTAL = Counter("gmnap_idempotency_ok_total", "Idempotency checks passed")
IDEMP_FAIL_TOTAL = Counter("gmnap_idempotency_fail_total", "Idempotency checks failed")

# Archive metrics
ARCHIVE_UPLOADS_SUCCEEDED = Counter(
    "gmnap_archive_uploads_succeeded_total", "Archive uploads succeeded"
)
ARCHIVE_UPLOADS_FAILED = Counter("gmnap_archive_uploads_failed_total", "Archive uploads failed")


def start_metrics_server(port: int = 8000):
    """Start Prometheus metrics HTTP server on *port*.

    Returns the server thread (daemon) so callers can check `is_alive()`.
    If prometheus_client is not installed, logs a warning and returns None.
    """
    try:
        from prometheus_client import start_http_server

        start_http_server(port)
        import logging

        logging.getLogger(__name__).info(f"Prometheus metrics server on :{port}/metrics")
    except ImportError:
        import logging

        logging.getLogger(__name__).warning(
            "prometheus_client not installed; metrics server disabled"
        )
    except OSError as e:
        import logging

        logging.getLogger(__name__).warning(f"Metrics server failed to start: {e}")
