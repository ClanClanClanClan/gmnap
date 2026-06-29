#!/usr/bin/env python3
"""Region-detection throughput smoke test (optimized RegionManager).

Migrated 2026-06-29 from V6. The original drove a mix of region names
through `GMNAPPipeline.run` and compared "standard" vs "optimized"
RegionManager wall-clock — but the standard manager was deleted in
round 18 and the optimized one is now the only RegionManager, so the
A/B comparison is moot. Following the established precedent
(tests/unit/test_simple_detection.py), this exercises detection
directly via `RegionManager.detect_region`, which is what the test was
really measuring.

The original `test_with_manager(manager_type, n_entries)` took two
positional args pytest cannot supply as fixtures, so it never ran as a
test under pytest anyway; it was a helper for a `__main__` benchmark.
This rewrite is a genuine, self-contained pytest case.
"""

import time

import pytest

from src.regions.manager_optimized import RegionManager


def _generate_entries(n_entries: int) -> list[dict]:
    """Generate a region-diverse batch of entry dicts."""
    patterns = [
        "Smith, John",
        "Müller, Hans",
        "Ivanov, Ivan",
        "Kowalski, Piotr",
        "Hassan, Ahmad",
        "Sharma, Raj",
        "Wang, Xiaoming",
        "Tanaka, Satoshi",
        "García, María",
    ]
    entries = []
    for i in range(n_entries):
        base = patterns[i % len(patterns)]
        surname, given = base.split(",")
        name = f"{surname.strip()}{i}, {given.strip()}"
        entries.append({"CanonicalLatin": name})
    return entries


@pytest.mark.timeout(30)
def test_optimized_region_manager_detects_all():
    """Every generated entry resolves to a non-empty region code."""
    manager = RegionManager()
    entries = _generate_entries(500)

    start = time.time()
    results = [manager.detect_region(e) for e in entries]
    duration = time.time() - start

    assert len(results) == len(entries)
    for entry, result in zip(entries, results):
        assert result.region_code, f"empty region_code for {entry['CanonicalLatin']}"
        assert isinstance(result.confidence, float)
        assert isinstance(result.detection_method, str)

    # Sanity: detection should be comfortably sub-millisecond per entry
    # on the optimized manager (warm). This is a generous ceiling, not a
    # tight benchmark — it just guards against a catastrophic regression.
    per_entry_ms = (duration * 1000) / len(entries)
    assert per_entry_ms < 50, f"detection too slow: {per_entry_ms:.1f} ms/entry"


if __name__ == "__main__":
    test_optimized_region_manager_detects_all()
    print("Detection throughput test passed.")
