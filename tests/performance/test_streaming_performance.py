#!/usr/bin/env python3
"""V7 batch-processing throughput / completeness smoke test.

Migrated 2026-06-29 from V6. The original compared a
`GMNAPPipeline` against a separate `StreamingPipeline` class
(`src.core.streaming_pipeline.StreamingPipeline` + `StreamingConfig`)
and extrapolated a 1 M-entry projection. Those two classes no longer
exist: streaming is now an *internal* path of `V7Pipeline.process_batch`
(it switches to the `StreamingPipelineAdapter` / `AsyncBatchAggregator`
above 100k entries). There is therefore no two-pipeline comparison to
port.

The durable property worth keeping is the streaming contract that
`tests/v7/test_v7_batch_shape.py` also guards: `process_batch` returns
one enriched dict per input entry, each with a GlobalID, regardless of
batch size. This rewrite asserts that over a region-diverse batch via
the real async pipeline.

The original `test_pipeline_performance(pipeline_class, dataset_size,
config, ...)` took positional args pytest cannot inject, so it never
executed as a pytest case — it was a helper for the `__main__`
benchmark. This version is a self-contained pytest case.
"""

import asyncio
import time

import psutil
import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


def _generate_entries(num_entries: int) -> list[dict]:
    """Generate a region-diverse batch of entry dicts."""
    sample_patterns = [
        {"name": "Smith, John {}", "country": "US"},
        {"name": "Brown, Sarah {}", "country": "GB"},
        {"name": "Davis, Michael {}", "country": "CA"},
        {"name": "राम प्रकाश शर्मा {}", "country": "IN"},
        {"name": "Иванов Иван Петрович {}", "country": "RU"},
        {"name": "王小明 {}", "country": "CN"},
        {"name": "محمد عبد الله {}", "country": "EG"},
    ]
    entries = []
    for i in range(num_entries):
        pattern = sample_patterns[i % len(sample_patterns)]
        name = pattern["name"].format(i)
        entries.append(
            {
                "CanonicalLatin": name,
                "CanonicalNative": name,
                "BirthYear": 1980 + (i % 40),
                "CountryCodes": [pattern["country"]],
                "Confidence": 85 + (i % 15),
            }
        )
    return entries


def _measure_memory_mb() -> float:
    try:
        return psutil.Process().memory_info().rss / 1024 / 1024
    except Exception:
        return 0.0


@pytest.mark.timeout(60)
def test_pipeline_streaming_contract():
    """process_batch returns one GlobalID-bearing dict per input entry."""
    dataset_size = 200
    entries = _generate_entries(dataset_size)

    initial_memory = _measure_memory_mb()
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    start = time.time()
    results = asyncio.run(pipeline.process_batch(entries))
    duration = time.time() - start

    assert isinstance(results, list)
    assert len(results) == dataset_size, "1:1 entry contract violated"
    ids = [r["GlobalID"] for r in results]
    assert all(ids), "every processed entry must carry a GlobalID"
    for r in results:
        assert r["DetectedRegion"], "every entry must resolve to a region"

    # Informational throughput / memory figures (not asserted as a hard
    # benchmark — laptop run-to-run variance is high; this only guards
    # against a pathological blow-up).
    entries_per_second = dataset_size / duration if duration else 0.0
    memory_increase = _measure_memory_mb() - initial_memory
    print(
        f"{dataset_size} entries in {duration:.2f}s "
        f"({entries_per_second:.1f}/s), +{memory_increase:.1f} MB RSS"
    )
    assert entries_per_second > 0


if __name__ == "__main__":
    test_pipeline_streaming_contract()
    print("\nStreaming contract test passed.")
