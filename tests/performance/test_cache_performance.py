#!/usr/bin/env python3
"""Re-run consistency check for the V7 pipeline.

Migrated 2026-06-29 from V6. The V6 test ran `GMNAPPipeline.run` twice
against a persistent on-disk authority cache and compared
`pipeline._authority_cache.get_stats()` hit/miss counts (cold vs warm)
plus per-stage timing deltas.

V7 has no `_authority_cache` attribute on the pipeline object, and the
default OFFLINE mode short-circuits authority enrichment before the
cache is consulted, so the original warm/cold-cache assertion has no
V7 analog. What still has real value — and what a "cache works"
property ultimately guarantees — is that processing the same batch
twice gives the same enriched result. This version asserts that
determinism through `V7Pipeline.process_batch` (async).
"""

import asyncio

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


@pytest.mark.timeout(30)
def test_cache_performance():
    """Two runs over the same input must agree on ids and regions."""
    names = [
        "Smith, John Michael",
        "Johnson, Robert",
        "Williams, David",
        "Brown, Michael",
        "Jones, William",
    ]
    entries = [
        {
            "CanonicalLatin": name,
            "CanonicalNative": name,
            "BirthYear": 1980 + i,
            "CountryCodes": ["US"],
            "Confidence": 85,
        }
        for i, name in enumerate(names)
    ]

    def run_once():
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        return asyncio.run(pipeline.process_batch([dict(e) for e in entries]))

    result1 = run_once()
    result2 = run_once()

    assert len(result1) == len(entries)
    assert len(result2) == len(entries)

    ids1 = [r["GlobalID"] for r in result1]
    ids2 = [r["GlobalID"] for r in result2]
    regions1 = [r["DetectedRegion"] for r in result1]
    regions2 = [r["DetectedRegion"] for r in result2]

    assert all(ids1), "every processed entry must carry a GlobalID"
    assert ids1 == ids2, "GlobalIDs differ between identical runs"
    assert regions1 == regions2, "region detection differs between identical runs"


if __name__ == "__main__":
    test_cache_performance()
