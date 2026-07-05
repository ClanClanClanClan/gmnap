"""
Hardcore pipeline memory management testing for GMNAP.

Tests memory usage and memory-leak behaviour of the V7 async pipeline
under large batches.

Migrated 2026-06-29 from the deleted ``src.core.pipeline_v6.GMNAPPipeline``.
The v6 tests drove private file-ingest stages
(``_stage_1_ingest(input_dir)`` reading YAML into ``pipeline._entries``)
and patched ``_load_authorities`` / ``_load_regions`` /
``_verify_file_ownership`` / ``_check_licenses`` — none of which exist on
``V7Pipeline``. V7 instead takes a ``list[dict]`` and returns a
``list[dict]`` from the single public async entry point
``process_batch``. The genuinely meaningful memory tests (large-dataset
RSS bound, cross-run leak detection, bounded streaming) were re-expressed
against ``process_batch``.

RETIRED (v6-only behaviour with NO v7 analog):
  * ``test_chunk_processing_efficiency`` and
    ``test_memory_optimization_strategies`` asserted that setting a
    smaller ``pipeline.chunk_size`` attribute yields lower memory. V7 has
    no caller-settable ``chunk_size`` attribute — chunking is an internal
    detail auto-derived from batch size inside ``process_batch``.
  * ``test_memory_pressure_handling`` and
    ``test_memory_limits_enforcement`` asserted v6 auto-shrinks its chunk
    size under pressure / raises ``ResourceExhaustedError`` at a memory
    cap. V7 has no such self-throttling mechanism, so there is nothing to
    assert.
"""

import asyncio
import gc
import tempfile
from typing import Any, Dict, List

import psutil
import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


class TestPipelineMemoryManagement:
    """Test V7 pipeline memory management under various loads."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Monitor memory
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Force garbage collection
        gc.collect()

    def _create_test_entries(
        self, count: int, entry_size: str = "medium"
    ) -> List[Dict[str, Any]]:
        """Create a list of test entry dicts for memory testing."""
        entries: List[Dict[str, Any]] = []

        # Different entry sizes
        size_configs = {
            "small": {"name_variants": 2, "affiliations": 1, "metadata_size": 10},
            "medium": {"name_variants": 5, "affiliations": 3, "metadata_size": 50},
            "large": {"name_variants": 20, "affiliations": 10, "metadata_size": 200},
            "huge": {"name_variants": 100, "affiliations": 50, "metadata_size": 1000},
        }

        config = size_configs.get(entry_size, size_configs["medium"])

        for i in range(count):
            canonical_name = f"TestPerson{i:06d}, John"

            # Generate name variants
            name_variants = []
            for j in range(config["name_variants"]):
                variant = f"TestVariant{i:06d}-{j:02d}, John"
                name_variants.append(variant)

            # Generate affiliations
            affiliations = []
            for j in range(config["affiliations"]):
                affiliation = {
                    "name": f"University{i:06d}-{j:02d}",
                    "department": f"Department of Mathematics {j:02d}",
                    "position": f"Professor {j:02d}",
                    "years": [2020 + j, 2021 + j],
                    "country": "US",
                }
                affiliations.append(affiliation)

            # Generate metadata
            metadata = {}
            for j in range(config["metadata_size"]):
                metadata[f"field_{j:03d}"] = f"value_{j:03d}_" + "x" * 10

            entry = {
                "CanonicalLatin": canonical_name,
                "CanonicalNative": canonical_name,
                "name_variants": name_variants,
                "affiliations": affiliations,
                "BirthYear": 1970 + (i % 50),
                "msc_codes": [f"11A{i % 100:02d}", f"11B{i % 100:02d}"],
                "CountryCodes": ["US", "GB"],
                "metadata": metadata,
            }

            entries.append(entry)

        return entries

    @pytest.mark.asyncio
    async def test_memory_usage_large_dataset(self):
        """Test memory usage with a large dataset stays bounded."""
        # Create a moderately large dataset (kept smaller than the v6
        # 50k figure so the suite runs in seconds on a laptop while still
        # exercising the batch path).
        entries = self._create_test_entries(count=400, entry_size="medium")

        gc.collect()
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        results = await pipeline.process_batch(entries)

        # 1:1 contract — every entry comes back processed.
        assert len(results) == len(
            entries
        ), f"Not all entries processed: {len(results)}/{len(entries)}"

        peak_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        growth = peak_memory - initial_memory

        # Memory should not balloon out of proportion to the dataset.
        assert growth < 1500, f"Excessive memory usage: {growth}MB"

        # Memory per entry should be bounded.
        memory_per_entry = max(growth, 0.0) / len(entries)
        assert (
            memory_per_entry < 0.5
        ), f"Too much memory per entry: {memory_per_entry}MB"

    @pytest.mark.asyncio
    async def test_memory_leaks_during_pipeline(self):
        """Test for memory leaks across repeated pipeline runs."""
        entries = self._create_test_entries(count=200, entry_size="medium")

        memory_measurements = []

        for _iteration in range(3):
            gc.collect()
            start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            pipeline = V7Pipeline(mode=PipelineMode.QUICK)
            results = await pipeline.process_batch(entries)
            assert len(results) == len(entries)

            del pipeline
            del results
            gc.collect()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            memory_measurements.append(end_memory - start_memory)

        # Memory usage should not grow without bound across iterations.
        if len(memory_measurements) > 1:
            memory_trend = memory_measurements[-1] - memory_measurements[0]
            assert (
                memory_trend < 200
            ), f"Possible memory leak: {memory_trend}MB growth across iterations"

    @pytest.mark.asyncio
    async def test_concurrent_pipeline_memory_safety(self):
        """Test memory safety with concurrent pipeline execution."""
        # Build several independent batches.
        datasets = [
            self._create_test_entries(count=200, entry_size="small") for _ in range(3)
        ]

        gc.collect()
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        async def run_pipeline(batch):
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)
            results = await pipeline.process_batch(batch)
            return len(results)

        tasks = [run_pipeline(batch) for batch in datasets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All pipelines should complete and process every entry.
        successful = [r for r in results if isinstance(r, int)]
        assert len(successful) == len(
            datasets
        ), f"Not all pipelines completed successfully: {results}"
        for count, batch in zip(successful, datasets):
            assert count == len(batch), "Entry count mismatch in concurrent run"

        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        assert (
            memory_growth < 1500
        ), f"Excessive memory from concurrent pipelines: {memory_growth}MB"

    @pytest.mark.asyncio
    async def test_memory_bounded_across_batch_sizes(self):
        """Test memory stays bounded as batch size grows (no per-entry blowup)."""
        results_summary = []

        for count in (100, 200, 400):
            entries = self._create_test_entries(count=count, entry_size="small")

            gc.collect()
            start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            pipeline = V7Pipeline(mode=PipelineMode.QUICK)
            processed = await pipeline.process_batch(entries)

            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            memory_usage = end_memory - start_memory

            assert len(processed) == count, f"Not all entries processed for {count}"
            results_summary.append((count, memory_usage))

            del pipeline
            del processed
            gc.collect()

        # Memory should not scale catastrophically with batch size: the
        # largest batch must not use wildly more than the smallest.
        smallest = max(results_summary[0][1], 1.0)
        largest = results_summary[-1][1]
        assert (
            largest <= smallest * 50 + 500
        ), f"Memory scales too steeply with batch size: {results_summary}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
