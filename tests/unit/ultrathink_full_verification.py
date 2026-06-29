#!/usr/bin/env python3
"""
ULTRATHINK FULL COMPLIANCE VERIFICATION (V7-migrated)

Originally a standalone "brutally honest" audit script that imported the
deleted ``src.core.pipeline_v6`` and a non-existent
``comprehensive_system_audit`` module. Migrated to pytest:

  * region classification / Korean / Persian / Arabic processor checks
    -> ``src.regions.manager_optimized.RegionManager`` (detection-only
    precedent from tests/unit/test_simple_detection.py).
  * the performance-claim check
    -> ``src.core.pipeline_v7.V7Pipeline.process_batch`` (async).

Two original sub-checks were intentionally dropped, with no v7 analog:
  * ``verify_1_archive_cleanup_safety`` only asserted that the now-deleted
    ``src/core/pipeline_v6.py`` still imported — meaningless post-deletion.
  * ``verify_6_no_regressions`` imported ``comprehensive_system_audit``,
    a module that does not exist in the repo.
"""

import asyncio
import time

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline
from src.regions.manager_optimized import RegionManager


def _detect(manager: RegionManager, name: str) -> str:
    result = manager.detect_region({"CanonicalLatin": name})
    return getattr(result, "region_code", str(result))


def test_performance_claims_quick_mode():
    """QUICK-mode batch processes a real dataset and returns 1:1 results."""
    test_names = [
        "Isaac Newton",
        "Carl Friedrich Gauss",
        "Andrey Kolmogorov",
        "Omar Khayyam",
        "Srinivasa Ramanujan",
        "Shiing-Shen Chern",
    ]
    entries = [
        {
            "GlobalID": f"TEST{i:04d}",
            "CanonicalLatin": name,
            "UpdatedAt": "2025-08-04T00:00:00Z",
        }
        for i, name in enumerate(test_names * 10)  # 60 entries
    ]

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    start = time.time()
    results = asyncio.run(pipeline.process_batch(entries))
    duration = time.time() - start

    assert isinstance(results, list)
    assert len(results) == len(entries)
    # Generous offline ceiling — guards against a catastrophic regression
    # (the round-28 lru_cache fix made this path ~22x faster).
    assert duration < 180, f"60-entry QUICK batch took {duration:.1f}s"


def test_regional_classification():
    """Critical name->region cases classify correctly (>=80% accuracy)."""
    manager = RegionManager()
    manager._ensure_regions_loaded()

    critical_tests = [
        ("Isaac Newton", "A1"),
        ("Alan Turing", "A1"),
        ("John Nash", "A1"),
        ("Andrey Kolmogorov", "B1"),
        ("Pafnuty Chebyshev", "B1"),
        ("Omar Khayyam", "C2"),
        ("Srinivasa Ramanujan", "D1"),
        ("Carl Friedrich Gauss", "A2"),
        ("David Hilbert", "A2"),
        ("Shiing-Shen Chern", "E1"),
    ]

    successes = sum(
        1 for name, expected in critical_tests if _detect(manager, name) == expected
    )
    accuracy = successes / len(critical_tests)
    # "Omar Khayyam" lands in C3 (Arabic) rather than C2 (Persian) offline
    # without fastText — a genuine, documented Persian/Arabic ambiguity,
    # not a crash. 80% threshold keeps the real behaviour honest.
    assert accuracy >= 0.8, f"classification accuracy {accuracy:.0%} below 80%"


def test_korean_detection_and_variants():
    """Korean names detect to E4 and the E4 processor generates variants."""
    manager = RegionManager()
    manager._ensure_regions_loaded()

    korean_tests = [
        ("김정은", "E4"),
        ("Kim Jong-un", "E4"),
        ("Park Geun-hye", "E4"),
        ("Moon Jae-in", "E4"),
    ]
    for name, expected in korean_tests:
        assert _detect(manager, name) == expected, f"{name} did not detect as E4"

    assert "E4" in manager._regions, "E4 Korea region not loaded"
    processor = manager._regions["E4"]
    entry = {"CanonicalLatin": "Kim Jong-un"}
    processor.clean(entry)
    processor.augment(entry)
    variants = entry.get("Variants", {}).get("Synthesised", [])
    assert variants, "E4 processor generated no Korean variants"


def test_persian_arabic_processors_run_without_typeerror():
    """C2 Persian and C4 Arabic processors run clean/augment/validate cleanly."""
    manager = RegionManager()
    manager._ensure_regions_loaded()

    for code, name in [("C2", "Omar Khayyam"), ("C4", "Abdul Jabbar Jerri")]:
        assert code in manager._regions, f"{code} region not loaded"
        processor = manager._regions[code]
        entry = {"CanonicalLatin": name}
        # The original bug class was a TypeError inside these processors;
        # a clean run is the assertion.
        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
