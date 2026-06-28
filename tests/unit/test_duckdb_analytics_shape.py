"""Regression tests for the ``suffix_duplicates`` return-shape contract.

``DuckDBAnalytics.suffix_duplicates(entries)`` is called by Stage 5 of
the pipeline as::

    entries, suffixed_count = analytics.suffix_duplicates(entries)

The tuple unpacking means the function MUST return a 2-tuple whenever
``entries`` was passed — even if the list is empty. Previously, the
fallback branch (when DuckDB is unavailable) returned a bare ``[]``
for empty-list inputs, which broke the unpacking with::

    ValueError: not enough values to unpack (expected 2, got 0)

That failure was triggered in the wild by any API call whose Stage 2
security filter rejected every entry (e.g. an XSS payload like
``<script>alert(1)</script>`` as the name) — Stage 5 then received an
empty list and crashed the whole request with a 500.

These tests pin the invariant so a future refactor can't reintroduce
the bug.
"""

from __future__ import annotations

from src.analytics.duckdb_analytics import DuckDBAnalytics


def test_empty_list_returns_2tuple_in_skipped_fallback():
    """Skipped fallback path — the path that was broken."""
    a = DuckDBAnalytics()
    # Force the skipped branch. This is what the Docker image and CI
    # see since DuckDB is not in requirements.txt.
    a.skipped = True
    result = a.suffix_duplicates([])
    assert isinstance(result, tuple), f"expected tuple, got {type(result).__name__}"
    assert len(result) == 2, f"expected 2-tuple, got len={len(result)}"
    entries, count = result
    assert entries == []
    assert count == 0


def test_none_returns_list_in_skipped_fallback():
    """When called with no entries (informational mode), the API is
    documented to return a list of (old, new) tuples. Preserve that."""
    a = DuckDBAnalytics()
    a.skipped = True
    result = a.suffix_duplicates(None)
    assert isinstance(result, list)
    assert result == []


def test_non_empty_returns_2tuple_in_skipped_fallback():
    a = DuckDBAnalytics()
    a.skipped = True
    entries = [{"GlobalID": "X", "order_key": "foo", "CanonicalLatin": "Foo"}]
    result = a.suffix_duplicates(entries)
    assert isinstance(result, tuple) and len(result) == 2
    assert result[0] is entries  # returned in place
    assert result[1] == 0  # nothing to suffix


def test_pipeline_unpack_pattern_survives_empty():
    """Reproduce the exact call site in pipeline_v7 Stage 5 and confirm
    the unpack no longer raises ValueError."""
    a = DuckDBAnalytics()
    a.skipped = True
    # This is the line that used to crash:
    entries, suffixed_count = a.suffix_duplicates([])
    assert entries == []
    assert suffixed_count == 0


# ── suffix_duplicates must not corrupt distinct people (R39) ──────────


def _two_distinct_same_name():
    return [
        {"GlobalID": "A" * 22, "CanonicalLatin": "Smith, John", "BirthYear": 1950},
        {"GlobalID": "B" * 22, "CanonicalLatin": "Smith, John", "BirthYear": 1950},
    ]


def test_suffix_duplicates_preserves_distinct_people():
    """Two DISTINCT people sharing name + birth year (different GlobalIDs)
    must KEEP their distinct ids. Regression (R39): suffix_duplicates
    appended --N to name+birth-year group members, corrupting a correct,
    unique id (B -> B--1) for genuinely different people."""
    from src.analytics.duckdb_analytics import DuckDBAnalytics

    a = DuckDBAnalytics()
    e = _two_distinct_same_name()
    a.load_entries(e)
    out, n = a.suffix_duplicates(e)
    assert n == 0
    assert [x["GlobalID"] for x in out] == ["A" * 22, "B" * 22]
    assert not any("--" in x["GlobalID"] for x in out)


def test_suffix_duplicates_report_mode_still_detects_name_collisions():
    """The report-only path (no entries arg) still surfaces name +
    birth-year collision groups for diagnostics, without mutating ids."""
    from src.analytics.duckdb_analytics import DuckDBAnalytics

    a = DuckDBAnalytics()
    e = _two_distinct_same_name()
    a.load_entries(e)
    assert len(a.suffix_duplicates()) > 0  # collision is reported
