"""Regression guard for V7Pipeline.process_batch return-shape consistency.

The pipeline has three internal paths keyed on batch size:
  * ≤ 5 entries   — the plain per-chunk path
  * 6 – 25 entries — ``_process_small_batch_fast``
  * ≥ 26 entries   — the per-chunk / streaming path

All three must return a flat ``list`` of entry dicts. A regression
(R37) had the 6-25 fast path return a ``{"results": [...],
"metrics": {...}}`` dict instead, so the API's ``/api/v1/process``
(which does ``len(result)`` / iterates) reported ``processed: 0`` and
silently dropped every result for those batch sizes. This test pins
the shape across all three paths.
"""

from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("OFFLINE", "1")

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


def _entries(n: int):
    return [
        {"CanonicalLatin": f"Smith{i}, John{i}", "CountryCodes": ["US"]}
        for i in range(n)
    ]


@pytest.mark.timeout(120)
@pytest.mark.parametrize("n", [1, 5, 6, 7, 25, 26, 50])
def test_process_batch_always_returns_list_of_len_n(n):
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    out = asyncio.run(pipeline.process_batch(_entries(n)))
    assert isinstance(out, list), (
        f"process_batch({n}) returned {type(out).__name__}, not list "
        f"(batch-size fast-path shape regression)"
    )
    assert len(out) == n, f"process_batch({n}) returned {len(out)} entries"
    # Every element is an entry dict, not a stray metrics blob.
    for e in out:
        assert isinstance(e, dict)
