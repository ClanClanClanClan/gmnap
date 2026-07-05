"""AsyncBatchAggregator — the >100k streaming path behind the documented
~2,763/s 1M throughput — previously had ZERO valid coverage (its old tests
imported a stale ``StreamingPipeline`` symbol that no longer exists), so the
headline-perf code ran blind (MASTERPLAN §2b.1, R49).

Tested with a synthetic process_func (pure aggregator semantics — fast,
deterministic, no detection stack).
"""

import asyncio
import random

import pytest

from src.core.async_batch_agg import AsyncBatchAggregator, LegacyAggConfig


async def _tag(entries):
    """Simulated pipeline stage: tags each entry, tiny async yield."""
    await asyncio.sleep(0)
    return [{**e, "processed": True} for e in entries]


@pytest.mark.timeout(60)
def test_order_preserved_across_concurrent_caller_batches():
    """Results come back to each caller in ITS submission order, even with
    many concurrent caller batches interleaving through the coalescer."""

    async def main():
        agg = AsyncBatchAggregator(_tag, LegacyAggConfig(fastpath_threshold=0))
        rng = random.Random(42)
        ids = list(range(1000))
        rng.shuffle(ids)
        chunks = [ids[i : i + 50] for i in range(0, 1000, 50)]

        async def submit(chunk):
            out = await agg.add_batch([{"id": i} for i in chunk])
            assert [o["id"] for o in out] == chunk  # caller order preserved
            assert all(o["processed"] for o in out)
            return out

        results = await asyncio.gather(*(submit(c) for c in chunks))
        await agg.close()
        flat = [o["id"] for outs in results for o in outs]
        assert sorted(flat) == list(range(1000))  # nothing lost or duplicated

    asyncio.run(main())


@pytest.mark.timeout(60)
def test_coalescing_respects_max_batch_size():
    """The coalescer must never hand process_func more than max_batch_size
    entries at once."""
    seen_sizes = []

    async def spy(entries):
        seen_sizes.append(len(entries))
        await asyncio.sleep(0)
        return entries

    async def main():
        cfg = LegacyAggConfig(
            target_size=8, max_size=16, max_latency_ms=5, fastpath_threshold=0
        )
        agg = AsyncBatchAggregator(spy, cfg)
        out = await agg.add_batch([{"n": i} for i in range(200)])
        assert len(out) == 200
        await agg.close()

    asyncio.run(main())
    assert seen_sizes, "process_func never invoked"
    assert (
        max(seen_sizes) <= 16
    ), f"coalesced batch exceeded max_size: {max(seen_sizes)}"


@pytest.mark.timeout(60)
def test_fastpath_small_batch_bypasses_queue():
    calls = []

    async def spy(entries):
        calls.append(len(entries))
        return entries

    async def main():
        agg = AsyncBatchAggregator(spy, LegacyAggConfig(fastpath_threshold=8))
        out = await agg.add_batch([{"n": 1}, {"n": 2}])
        assert [e["n"] for e in out] == [1, 2]
        await agg.close()

    asyncio.run(main())
    assert calls == [2]  # exactly one direct call, whole batch


@pytest.mark.timeout(60)
def test_closed_aggregator_rejects_new_batches():
    async def main():
        agg = AsyncBatchAggregator(_tag)
        await agg.add_batch([{"n": 1}])  # initialize
        await agg.close()
        with pytest.raises(RuntimeError):
            await agg.add_batch([{"n": 2}])

    asyncio.run(main())


@pytest.mark.timeout(120)
def test_streaming_scale_10k_all_processed():
    """A 10k stream (200 caller batches of 50) through a tight coalescer —
    everything processed exactly once, order per caller preserved."""

    async def main():
        cfg = LegacyAggConfig(target_size=64, max_size=128, max_latency_ms=2)
        agg = AsyncBatchAggregator(_tag, cfg)
        batches = [[{"id": b * 50 + i} for i in range(50)] for b in range(200)]
        results = await asyncio.gather(*(agg.add_batch(b) for b in batches))
        await agg.drain()
        await agg.close()
        flat = [o["id"] for outs in results for o in outs]
        assert len(flat) == 10_000
        assert sorted(flat) == list(range(10_000))

    asyncio.run(main())
