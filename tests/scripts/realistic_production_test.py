#!/usr/bin/env python3
"""
Realistic Production Test Suite for GMNAP (V7-migrated)

Originally a standalone script that drove the deleted
``src.core.pipeline_v6.GMNAPPipeline`` via its file-based ``run(input_dir)``
API and reached into ``pipeline.region_manager``. Both are gone in v7.

Migrated to pytest against the live v7 surface:

  * scale / performance -> ``V7Pipeline.process_batch`` (async; returns a
    flat list of len(entries), see tests/v7/test_v7_batch_shape.py).
  * regional coverage reality -> ``RegionManager.detect_region`` with
    CountryCodes (the geo branch is 100% accurate when CC is supplied).

Dropped sub-tests with no v7 analog:
  * ``test_authority_quota_reality`` — instrumented the v6 QuotaManager
    internals through ``pipeline.run()``; v7 enrichment is OFFLINE-gated
    and has no equivalent quota hook to assert against.
  * ``test_concurrent_operations`` — spun N threads each calling the
    file-based ``pipeline.run()``; ``process_batch`` is the v7 concurrency
    primitive (it parallelises chunks internally), so per-thread
    ``run()`` has no meaning. The 1:1 batch-shape guarantee is covered by
    ``test_scale_performance`` instead.
"""

import asyncio
import os
import random
import time
from contextlib import contextmanager

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline
from src.regions.manager_optimized import RegionManager


@contextmanager
def _isolated_cwd(tmp_path):
    """Run inside a fresh cwd so stage-9 writes go to a per-test
    ``output/stage9.duckdb`` and don't collide on the DuckDB file lock when
    multiple full-pipeline batches run in the same process."""
    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield
    finally:
        os.chdir(prev)


def _generate_realistic_entries(size: int, seed: int = 1234) -> list[dict]:
    """Generate `size` realistic mathematician entries across regions."""
    rng = random.Random(seed)

    patterns = [
        # (CanonicalLatin samples, CountryCode)
        (
            ["John Michael Smith", "Sarah Elizabeth Johnson", "Robert James Williams"],
            "US",
        ),
        (["Ram Prakash Sharma", "Sunil Kumar Gupta", "Vijay Singh"], "IN"),
        (["Ivan Petrovich Ivanov", "Maria Aleksandrovna Petrova"], "RU"),
        (["Wang Xiaoming", "Li Dahua", "Zhang Meili"], "CN"),
        (["Muhammad Abdullah Al-Ahmad", "Ahmad Ali Al-Hasan"], "EG"),
    ]

    entries = []
    for i in range(size):
        names, cc = rng.choice(patterns)
        name = rng.choice(names)
        entries.append(
            {
                "GlobalID": f"REAL{i:015d}",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": name,
                "CountryCodes": [cc],
                "BirthYear": rng.randint(1920, 2000),
            }
        )
    return entries


@pytest.mark.parametrize("size", [100, 500])
def test_scale_performance(size, tmp_path):
    """process_batch handles realistic batches and returns 1:1 results."""
    entries = _generate_realistic_entries(size)
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    start = time.time()
    with _isolated_cwd(tmp_path):
        results = asyncio.run(pipeline.process_batch(entries))
    duration = time.time() - start

    assert isinstance(results, list)
    assert len(results) == size, f"process_batch({size}) returned {len(results)}"
    # Offline ceiling guarding against catastrophic perf regression.
    assert duration < 300, f"{size}-entry batch took {duration:.1f}s (>300s)"


def test_regional_coverage_implemented_regions():
    """Implemented regions detect correctly when CountryCodes are supplied."""
    manager = RegionManager()
    manager._ensure_regions_loaded()

    implemented = [
        ("Smith, John", "US", "A1"),
        ("Иванов Иван", "RU", "B1"),
        ("राम प्रकाश शर्मा", "IN", "D1"),
        ("王小明", "CN", "E1"),
        ("محمد عبد الله", "EG", "C3"),
        ("田中太郎", "JP", "E3"),
        ("García López, José", "MX", "G1"),
    ]

    successes = 0
    for name, cc, expected in implemented:
        result = manager.detect_region(
            {"CanonicalLatin": name, "CanonicalNative": name, "CountryCodes": [cc]}
        )
        if result.region_code == expected:
            successes += 1

    accuracy = successes / len(implemented)
    # Geo branch is 100% accurate with CC provided; allow a small margin.
    assert accuracy >= 0.85, (
        f"implemented-region coverage {accuracy:.0%} "
        f"({successes}/{len(implemented)}) below 85%"
    )


def test_regional_coverage_handles_unmapped_gracefully():
    """Names with no implemented region never crash detection."""
    manager = RegionManager()
    manager._ensure_regions_loaded()

    # These cover non-implemented-region territories / boundary cases;
    # the contract is "no crash and a well-formed result", not a specific
    # leaf — the v6 script tracked these as coverage-gap diagnostics.
    edge_cases = [
        ("Okonkwo, Chinua", "NG"),
        ("Andersson, Lars", "SE"),
        ("Öztürk, Ahmet", "TR"),
        ("রহমান আহমদ", "BD"),
    ]
    for name, cc in edge_cases:
        result = manager.detect_region({"CanonicalLatin": name, "CountryCodes": [cc]})
        assert result is not None
        assert isinstance(result.region_code, str) and result.region_code


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
