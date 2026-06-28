"""Unit tests for src/core/cost_tracker.py.

The interesting tests are the CROSS-PROCESS ones: the module's job is to
aggregate live-API spend across multiple uvicorn worker processes via an
fcntl-locked JSON file. The single-process threading.Lock makes
within-process correctness trivial; the file lock is what protects
across processes. These tests exercise that with multiprocessing so a
regression in the lock ordering (read-before-lock lost update, or
truncate-before-lock empty-file window) actually fails the suite.
"""

from __future__ import annotations

import json
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor

import pytest

from src.core import cost_tracker


@pytest.fixture()
def costs_path(monkeypatch):
    """Point the tracker at a throwaway costs file for each test."""
    d = tempfile.mkdtemp()
    path = os.path.join(d, "api_costs.json")
    monkeypatch.setenv("GMNAP_COSTS_PATH", path)
    cost_tracker.reset()
    yield path
    cost_tracker.reset()


# ── Basic semantics ───────────────────────────────────────────────────


def test_metered_source_accumulates(costs_path):
    cost_tracker.record("Scopus", calls=1000)  # 5.0/1k * 1000
    cost_tracker.record("Scopus", calls=1000)  # +5.0
    cost_tracker.record("ProQuest", calls=100)  # 10.0/1k * 100 = 1.0
    assert cost_tracker.total() == pytest.approx(11.0)


def test_free_source_is_noop(costs_path):
    cost_tracker.record("OpenAlex", calls=1_000_000)
    cost_tracker.record("Crossref", calls=1_000_000)
    assert cost_tracker.total() == 0.0
    # No file written for free sources (cost == 0 short-circuits I/O).
    assert not os.path.exists(costs_path)


def test_override_chf_is_absolute(costs_path):
    cost_tracker.record("MathSciNet", override_chf=42.5)
    assert cost_tracker.total() == pytest.approx(42.5)


def test_reset_wipes_file(costs_path):
    cost_tracker.record("Scopus", override_chf=3.0)
    assert os.path.exists(costs_path)
    cost_tracker.reset()
    assert not os.path.exists(costs_path)
    assert cost_tracker.total() == 0.0


def test_malformed_file_degrades_to_empty(costs_path):
    with open(costs_path, "w", encoding="utf-8") as fh:
        fh.write("{ not valid json ")
    # _load() must not raise; it logs and returns {}.
    assert cost_tracker.total() == 0.0
    # A subsequent record() overwrites the garbage with valid JSON.
    cost_tracker.record("Scopus", override_chf=2.0)
    assert cost_tracker.total() == pytest.approx(2.0)
    with open(costs_path, encoding="utf-8") as fh:
        assert json.load(fh) == {"Scopus": 2.0}


# ── Cross-process concurrency (the real regression guard) ─────────────


def _worker(args):
    """Top-level (picklable) worker: re-point the tracker at the shared
    file in this child process and record ``n`` charges of 1 CHF each."""
    path, n = args
    os.environ["GMNAP_COSTS_PATH"] = path
    # Re-import inside the child so the module picks up the env var.
    from src.core import cost_tracker as ct

    for _ in range(n):
        ct.record("Scopus", override_chf=1.0)
    return n


def test_cross_process_no_lost_updates(costs_path):
    """N processes each add M charges of 1 CHF. The total must be exactly
    N*M. The pre-fix code read the file BEFORE taking the exclusive lock,
    so two processes could both read the same old total and the second
    write would clobber the first — under-counting. The lock-first
    read-modify-write makes every increment durable.
    """
    n_procs, per_proc = 6, 40
    expected = float(n_procs * per_proc)  # 240.0

    with ProcessPoolExecutor(max_workers=n_procs) as ex:
        list(ex.map(_worker, [(costs_path, per_proc)] * n_procs))

    assert cost_tracker.total() == pytest.approx(expected), (
        f"lost update across processes: got {cost_tracker.total()}, "
        f"expected {expected}"
    )


def _reader(path):
    """Top-level reader: spin reading total() and assert it never goes
    backwards (which would indicate it observed a truncated/empty file
    mid-write). Returns the max total seen."""
    os.environ["GMNAP_COSTS_PATH"] = path
    from src.core import cost_tracker as ct

    last = 0.0
    saw_decrease = False
    for _ in range(200):
        cur = ct.total()
        if cur < last:
            saw_decrease = True
        last = max(last, cur)
    return saw_decrease


def test_reader_never_sees_truncated_file(costs_path):
    """A concurrent reader (shared lock) must never observe a transient
    empty/truncated file while a writer holds the exclusive lock. The
    pre-fix code opened the file in ``"w"`` mode (truncate) BEFORE the
    lock, exposing a 0-byte window that a reader would parse as {} → a
    spurious drop to 0. The reader returns True if it ever saw the total
    decrease.
    """
    # Seed a baseline so a truncate-to-empty would be a visible drop.
    cost_tracker.record("Scopus", override_chf=10.0)

    with ProcessPoolExecutor(max_workers=2) as ex:
        reader_fut = ex.submit(_reader, costs_path)
        writer_fut = ex.submit(_worker, (costs_path, 60))
        writer_fut.result()
        saw_decrease = reader_fut.result()

    assert saw_decrease is False, "reader observed a truncated/empty costs file"
