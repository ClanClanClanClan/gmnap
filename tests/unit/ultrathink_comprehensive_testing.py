#!/usr/bin/env python3
"""
ULTRATHINK COMPREHENSIVE TESTING (V7-migrated)

Real-world mathematician testing for the GMNAP v7 system.

Originally a script that drove the deleted ``src.core.pipeline_v6`` and a
``mathematician_test_dataset.json`` fixture that no longer ships with the
repo. Migrated to pytest against the live v7 surface:

  * region classification / robustness / end-to-end region processing
    -> ``src.regions.manager_optimized.RegionManager.detect_region``
    (the precedent set by tests/unit/test_simple_detection.py)
  * the full-pipeline performance smoke
    -> ``src.core.pipeline_v7.V7Pipeline.process_batch`` (async).

The inline ``SAMPLE_MATHEMATICIANS`` set replaces the missing JSON fixture
so the file is self-contained and deterministic.
"""

import asyncio
import time

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline
from src.regions.manager_optimized import RegionManager

# (name, expected_region_code) — names chosen to exercise the handcrafted
# surname/suffix rules so detection is deterministic offline (no fastText
# subprocess gambling). These mirror the curated cases the v6 script used.
SAMPLE_MATHEMATICIANS = [
    ("Isaac Newton", "A1"),
    ("Alan Turing", "A1"),
    ("Andrey Kolmogorov", "B1"),
    ("Pafnuty Chebyshev", "B1"),
    ("Carl Friedrich Gauss", "A2"),
    ("David Hilbert", "A2"),
    ("Srinivasa Ramanujan", "D1"),
    ("Omar Khayyam", "C2"),
]


def _detect(manager: RegionManager, name: str) -> str:
    result = manager.detect_region({"CanonicalLatin": name})
    return getattr(result, "region_code", str(result))


def test_real_mathematician_classification():
    """Curated real names land in their expected region (>=75% accuracy)."""
    manager = RegionManager()
    manager._ensure_regions_loaded()

    correct = sum(
        1
        for name, expected in SAMPLE_MATHEMATICIANS
        if _detect(manager, name) == expected
    )
    accuracy = correct / len(SAMPLE_MATHEMATICIANS)
    assert accuracy >= 0.75, (
        f"classification accuracy {accuracy:.0%} "
        f"({correct}/{len(SAMPLE_MATHEMATICIANS)}) below 75% threshold"
    )


def test_regional_processing_generates_order_key():
    """Each detected region's processor runs clean/augment/validate/order_key."""
    manager = RegionManager()
    manager._ensure_regions_loaded()

    workflows_ok = 0
    for name, _expected in SAMPLE_MATHEMATICIANS:
        region = _detect(manager, name)
        processor = manager._regions.get(region)
        if processor is None:
            continue
        entry = {"CanonicalLatin": name}
        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)
        order_key = processor.order_key(entry)
        if order_key is not None and len(str(order_key).strip()) > 0:
            workflows_ok += 1

    rate = workflows_ok / len(SAMPLE_MATHEMATICIANS)
    assert rate >= 0.7, f"end-to-end processing succeeded for only {rate:.0%}"


def test_edge_cases_and_robustness():
    """Malformed / hostile inputs are handled gracefully (no crash)."""
    manager = RegionManager()
    manager._ensure_regions_loaded()

    edge_cases = [
        "",
        "   ",
        "A",
        "a" * 500,
        "John; DROP TABLE;",
        "<script>alert('xss')</script>",
        "../../../etc/passwd",
        "Джон Смит",
        "José Ádam Đorđević",
        "金正恩",
        "smith,john",
        "SMITH JOHN",
        "Smith,,John",
        "Smith\tJohn",
        "Smith\nJohn",
    ]

    for test_input in edge_cases:
        # Must never raise — the security layer returns an "XX"/blocked
        # result for hostile inputs rather than throwing.
        result = manager.detect_region({"CanonicalLatin": test_input})
        assert result is not None
        assert hasattr(result, "region_code")


def test_injection_inputs_are_blocked_not_classified():
    """SQL/XSS/path-traversal payloads are routed to the security-blocked path."""
    manager = RegionManager()
    manager._ensure_regions_loaded()

    malicious = [
        "John; DROP TABLE students; --",
        "<script>alert('xss')</script>",
        "../../../etc/passwd",
    ]
    for payload in malicious:
        result = manager.detect_region({"CanonicalLatin": payload})
        assert result.region_code == "XX", (
            f"malicious input {payload!r} was classified as "
            f"{result.region_code} instead of being blocked"
        )
        assert result.detection_method == "security_blocked"


def test_full_pipeline_performance_smoke():
    """V7Pipeline.process_batch runs a real batch and returns 1:1 results."""
    entries = []
    for i, (name, _expected) in enumerate(SAMPLE_MATHEMATICIANS * 4):  # 32 entries
        entries.append(
            {
                "GlobalID": f"MATH{i:06d}",
                "CanonicalLatin": name,
                "UpdatedAt": "2025-08-04T00:00:00Z",
            }
        )

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    start = time.time()
    results = asyncio.run(pipeline.process_batch(entries))
    duration = time.time() - start

    # process_batch returns a flat list of len(entries) (see
    # tests/v7/test_v7_batch_shape.py).
    assert isinstance(results, list)
    assert len(results) == len(
        entries
    ), f"process_batch returned {len(results)} for {len(entries)} inputs"
    # Sanity: a 32-entry QUICK batch must finish well within a generous
    # offline ceiling (guards against a catastrophic perf regression).
    assert duration < 120, f"32-entry batch took {duration:.1f}s (>120s)"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
