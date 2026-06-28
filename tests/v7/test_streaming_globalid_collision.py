"""Regression guard: the >100k streaming path must keep GlobalID
collision suffixes across microbatches.

Root cause (fixed): ``reset_collision_tracking()`` used to live at the
top of ``V7Pipeline._process_batch_internal``. In the streaming path the
``StreamingPipelineAdapter`` invokes that method once PER coalesced
microbatch, so the reset wiped the cross-batch collision cache between
microbatches. Two copies of the same person (identical CanonicalNative /
BirthYear / DeathYear) landing in different microbatches both received
the SAME unsuffixed GlobalID — a silent primary-key collision in the
stage-9 YAML / DuckDB changelog on the documented 1M production path.

The fix moves the reset to the public ``process_batch`` entry point so it
fires exactly once per run; ``_process_batch_internal`` (the per-microbatch
worker) no longer resets. This test models two microbatches by invoking
``_process_batch_internal`` twice inside one reset window — exactly how
the streaming adapter drives it.
"""

import asyncio

import pytest

from src.core.global_id import reset_collision_tracking
from src.core.pipeline_v7 import PipelineMode, V7Pipeline


def _dup():
    # Identical person on every field that feeds the GlobalID hash.
    return {
        "CanonicalNative": "Euler, Leonhard",
        "CanonicalLatin": "Euler, Leonhard",
        "BirthYear": 1707,
        "DeathYear": 1783,
    }


@pytest.mark.timeout(60)
def test_streaming_microbatches_keep_collision_suffix():
    async def _run():
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        # process_batch() does this once per run; the streaming adapter
        # then calls _process_batch_internal once per microbatch.
        reset_collision_tracking()

        mb1 = await pipeline._process_batch_internal([_dup()])
        mb2 = await pipeline._process_batch_internal([_dup()])
        return mb1, mb2

    mb1, mb2 = asyncio.run(_run())
    assert isinstance(mb1, list) and isinstance(mb2, list)
    g1 = mb1[0].get("GlobalID")
    g2 = mb2[0].get("GlobalID")
    assert g1 and g2, f"missing GlobalID(s): {g1!r}, {g2!r}"
    # The duplicate in the second microbatch must be suffixed, not a
    # bare clone of the first. On the pre-fix code (reset per microbatch)
    # g2 == g1 and this fails.
    assert g1 != g2, (
        "duplicate person across microbatches got the SAME GlobalID "
        f"({g1!r}) — collision suffix lost (reset fired per microbatch)"
    )


@pytest.mark.timeout(60)
def test_process_batch_resets_between_runs():
    """Each independent process_batch run starts a fresh collision
    window — two separate runs of the same single entry must produce the
    SAME base GlobalID (the reset still happens, just once per run)."""

    async def _one():
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        out = await pipeline.process_batch([_dup()])
        return out[0].get("GlobalID")

    g_run1 = asyncio.run(_one())
    g_run2 = asyncio.run(_one())
    assert g_run1 and g_run2
    # Distinct runs reset independently, so a lone entry gets the same
    # base id both times (no cross-run suffix bleed).
    assert g_run1 == g_run2, (
        f"independent runs produced different base GlobalIDs "
        f"({g_run1!r} vs {g_run2!r}) — reset is not per-run"
    )


@pytest.mark.timeout(60)
def test_small_batch_fast_path_uses_canonical_globalid():
    """The 6-25 entry fast path must mint canonical deterministic
    GlobalIDs (SHA-256 base32), NOT the old
    f"gmnap_{region}_{abs(hash(native))%1e6}" scheme.

    Regression (R39): that scheme used Python's per-process-salted hash()
    so IDs were non-deterministic across runs (idempotency violation) and
    a different format from every other pipeline path.
    """
    import re

    entries = [
        {
            "CanonicalNative": f"Euler{i}, Leonhard",
            "CanonicalLatin": f"Euler{i}, Leonhard",
        }
        for i in range(10)  # 6..25 -> fast path
    ]

    def _run():
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        return asyncio.run(pipeline.process_batch([dict(e) for e in entries]))

    out1 = _run()
    out2 = _run()
    ids1 = [e["GlobalID"] for e in out1]
    ids2 = [e["GlobalID"] for e in out2]

    canonical = re.compile(r"[A-Z2-7]{22}(--\d+)?$")
    assert all(canonical.match(g) for g in ids1), ids1
    assert not any(g.startswith("gmnap_") for g in ids1)
    # Deterministic across independent runs (idempotency).
    assert ids1 == ids2
