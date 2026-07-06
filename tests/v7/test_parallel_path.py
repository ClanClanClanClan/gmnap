"""R54 regression guards for the large-batch parallel path.

Two failures this pins, both of which shipped silently before R54:

1. THE NO-OP. The >100k "streaming" path fed 16-entry microbatches into a
   fast path that emitted entries with NO region detection — the documented
   "1M in 362s / 2763-per-s" was a dict-copy loop measuring skipped work.
   ``test_parallel_path_does_real_work`` asserts every entry on the parallel
   path is actually classified.

2. SERIAL != PARALLEL. The whole point of the process-pool path is that it is
   a faithful, faster twin of the serial path. ``test_serial_parallel_identical``
   asserts byte-identical output (GlobalIDs, region axes, everything) — it is
   what caught the GlobalID-per-chunk suffixing bug and the hash-ordered
   name-variant dedup (both fixed in R54).

The parallel path is forced on a small batch via GMNAP_PARALLEL_THRESHOLD so
the test is cheap; workers are capped at 2 to bound spawn cost.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


def _entries(n: int):
    # Diverse surnames -> exercises many region branches, not one hot path.
    seeds = [
        ("Kowalski", "Jan", "PL"),
        ("Tanaka", "Hiroshi", "JP"),
        ("Rossi", "Marco", "IT"),
        ("Nguyen", "Anh", "VN"),
        ("Okafor", "Chidi", "NG"),
        ("Andersson", "Lars", "SE"),
        ("Petrov", "Ivan", "RU"),
        ("Garcia", "Maria", "ES"),
    ]
    out = []
    for i in range(n):
        s, g, cc = seeds[i % len(seeds)]
        out.append({"CanonicalLatin": f"{s}{i}, {g}", "CountryCodes": [cc]})
    return out


def _run(entries, *, parallel: bool):
    env = dict(os.environ)
    if parallel:
        os.environ.pop("GMNAP_NO_PARALLEL", None)
        os.environ["GMNAP_PARALLEL_THRESHOLD"] = "10"
        os.environ["GMNAP_PARALLEL_WORKERS"] = "2"
    else:
        os.environ["GMNAP_NO_PARALLEL"] = "1"
    try:
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        return asyncio.run(pipeline.process_batch([dict(e) for e in entries]))
    finally:
        os.environ.clear()
        os.environ.update(env)


def _canon(rows):
    # LastUpdated is a wall-clock date; drop it before comparing.
    return [
        {k: v for k, v in sorted(r.items()) if k != "LastUpdated"}
        for r in sorted(rows, key=lambda x: x.get("GlobalID", ""))
    ]


@pytest.mark.timeout(180)
def test_parallel_path_does_real_work():
    """Every entry on the parallel path must be genuinely classified — the
    no-op shadow produced DetectedRegion=None/unknown for all of them."""
    rows = _run(_entries(60), parallel=True)
    assert len(rows) == 60
    classified = [
        r for r in rows if r.get("DetectedRegion") and r["DetectedRegion"] != "unknown"
    ]
    assert len(classified) == 60, (
        f"parallel path classified only {len(classified)}/60 — the large-batch "
        f"path is skipping region detection (the R54 no-op regression)"
    )
    # split axes + GDPR marking must be present too (full pipeline, not a shim)
    for r in rows:
        assert "GeoRegion" in r or "NameRegion" in r
        assert "GDPR_DATA" in r


@pytest.mark.timeout(180)
def test_serial_parallel_identical():
    """Parallel output must be byte-identical to serial output."""
    entries = _entries(60)
    serial = _run(entries, parallel=False)
    parallel = _run(entries, parallel=True)
    assert _canon(serial) == _canon(parallel), (
        "serial and parallel outputs diverged — the parallel path is not a "
        "faithful twin (GlobalID suffixing or nondeterministic ordering)"
    )
