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


def Counter(name: str, desc: str = ""):
    if _PCounter is None:
        return _NoOp()
    return _PCounter(name, desc)


def Gauge(name: str, desc: str = ""):
    if _PGauge is None:
        return _NoOp()
    return _PGauge(name, desc)


# Common metrics (shared with Push 9)
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

# Push 10 metrics
REPORTS_EMITTED = Counter("gmnap_reports_emitted_total", "Stage 10 reports generated")
DOI_DRAFTS_CREATED = Counter(
    "gmnap_doi_drafts_created_total", "DataCite DOI drafts generated"
)
ARCHIVE_UPLOADS_SUCCEEDED = Counter(
    "gmnap_archive_uploads_succeeded_total", "Snapshot archives uploaded successfully"
)
ARCHIVE_UPLOADS_FAILED = Counter(
    "gmnap_archive_uploads_failed_total", "Snapshot archive uploads failed"
)
