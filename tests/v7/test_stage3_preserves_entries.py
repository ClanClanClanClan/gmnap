"""Regression guard: stage 3 (region hooks) must return one row per
input row.

Root cause (fixed): _stage_3_region_hooks dropped two classes of entry
from its output — security-blocked (region "XX") and entries whose
region has no processor — via a `continue` that skipped the
`processed.append(entry)`. That:

  * silently lost those records from the pipeline output (len(out) <
    len(in)), and
  * in the >100k streaming path, made the per-microbatch worker return
    fewer rows than the AsyncBatchAggregator's futures. The aggregator
    maps results 1:1 by position and, on a count mismatch, fails the
    ENTIRE microbatch to None — so one blocked entry nulled ~512 good
    ones.

The fix keeps every entry (with a SecurityBlocked / ProcessingError
status marker) so the stage is 1:1.
"""

import asyncio

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


@pytest.mark.timeout(30)
def test_stage3_preserves_blocked_and_no_processor_entries():
    async def _run():
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        entries = [
            # security-blocked → kept with SecurityBlocked marker
            {"GlobalID": "g1", "DetectedRegion": "XX", "CanonicalLatin": "x"},
            # region with no processor → kept with ProcessingError marker
            {
                "GlobalID": "g2",
                "DetectedRegion": "ZZ_NO_PROCESSOR",
                "CanonicalLatin": "y",
            },
            # normal entry → processed and kept
            {
                "GlobalID": "g3",
                "DetectedRegion": "A1",
                "CanonicalLatin": "Euler, Leonhard",
            },
        ]
        return await pipeline._stage_3_region_hooks(entries)

    out = asyncio.run(_run())
    # 1:1 contract: every input row appears in the output.
    assert len(out) == 3, f"stage 3 dropped entries (broke 1:1): got {len(out)}"
    by_id = {e.get("GlobalID"): e for e in out}
    assert set(by_id) == {"g1", "g2", "g3"}
    # Blocked / failed entries are KEPT, with their status markers.
    assert by_id["g1"].get("SecurityBlocked") is True
    assert "ProcessingError" in by_id["g2"]
