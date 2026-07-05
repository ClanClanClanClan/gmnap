#!/usr/bin/env python3
"""Idempotency / determinism check for the V7 pipeline.

Migrated 2026-06-29 from V6 (`src.core.pipeline_v6.GMNAPPipeline.run`,
which read a directory of YAML files) to V7
(`src.core.pipeline_v7.V7Pipeline.process_batch`, an async call that
takes a list of entry dicts and returns a list of enriched dicts).

The V6 test only proved the pipeline "completed" on one entry. The V7
version asserts the stronger, real property the original was named for:
processing the *same* input twice yields byte-identical GlobalIDs
(stage 1 assigns canonical SHA-256 ids deterministically), i.e. the
pipeline is idempotent.
"""

import asyncio

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


@pytest.mark.timeout(30)
def test_idempotency():
    """Re-processing identical input must yield identical GlobalIDs."""
    entries = [
        {
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "Smith, John",
            "BirthYear": 1980,
            "CountryCodes": ["US"],
            "Confidence": 85,
        }
    ]

    def run_once():
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        return asyncio.run(pipeline.process_batch([dict(e) for e in entries]))

    result1 = run_once()
    result2 = run_once()

    assert isinstance(result1, list)
    assert len(result1) == len(entries)
    assert len(result2) == len(entries)

    # Stage 1 assigns canonical SHA-256 GlobalIDs; identical input must
    # produce identical ids across independent runs.
    ids1 = [r["GlobalID"] for r in result1]
    ids2 = [r["GlobalID"] for r in result2]
    assert all(ids1), "every processed entry must carry a GlobalID"
    assert ids1 == ids2, "pipeline is not idempotent: GlobalIDs differ between runs"

    # Region detection must also be stable.
    assert result1[0]["DetectedRegion"] == result2[0]["DetectedRegion"]


if __name__ == "__main__":
    test_idempotency()
    print("\nTest completed!")
