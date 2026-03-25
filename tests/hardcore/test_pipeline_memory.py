"""
Hardcore pipeline memory management testing for GMNAP.

Tests memory usage during data processing operations to ensure no leaks
or excessive usage.
"""

import gc
import tempfile
import threading
from queue import Queue
from typing import Any, Dict, List

import psutil
import pytest

from src.core.globalid import GlobalIDGenerator
from src.core.unicode_handler import UnicodeNormalizer


class TestPipelineMemoryManagement:
    """Test memory management during pipeline-style processing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        gc.collect()

    def _create_test_entries(self, count: int) -> List[Dict[str, Any]]:
        """Create test entries."""
        entries = []
        for i in range(count):
            entry = {
                "CanonicalLatin": f"TestPerson{i:06d}, John",
                "CanonicalNative": f"TestPerson{i:06d}, John",
                "BirthYear": 1950 + (i % 70),
                "countries": ["US"],
                "name_variants": [f"J. TestPerson{i:06d}"],
            }
            entries.append(entry)
        return entries

    def test_memory_usage_large_dataset(self):
        """Test memory usage processing large number of entries."""
        normalizer = UnicodeNormalizer()

        entries = self._create_test_entries(10000)

        start_memory = self.process.memory_info().rss / 1024 / 1024

        for entry in entries:
            _ = normalizer.normalize(entry["CanonicalLatin"])

        end_memory = self.process.memory_info().rss / 1024 / 1024
        memory_growth = end_memory - start_memory

        assert (
            memory_growth < 200
        ), f"Excessive memory growth: {memory_growth:.1f}MB for 10K entries"

    def test_chunk_processing_efficiency(self):
        """Test that chunked processing limits peak memory."""
        normalizer = UnicodeNormalizer()
        generator = GlobalIDGenerator()

        chunk_size = 1000
        total_entries = 5000
        entries = self._create_test_entries(total_entries)

        start_memory = self.process.memory_info().rss / 1024 / 1024
        max_memory = start_memory

        for i in range(0, total_entries, chunk_size):
            chunk = entries[i : i + chunk_size]

            # Process chunk
            for entry in chunk:
                normalizer.normalize(entry["CanonicalLatin"])
                gid = generator.generate(entry)
                assert isinstance(gid, str)

            # Check memory per chunk
            current_memory = self.process.memory_info().rss / 1024 / 1024
            max_memory = max(max_memory, current_memory)

            gc.collect()

        memory_growth = max_memory - start_memory
        assert memory_growth < 200, f"Excessive peak memory: {memory_growth:.1f}MB"

    def test_memory_leaks_during_pipeline(self):
        """Test for memory leaks in repeated processing."""
        normalizer = UnicodeNormalizer()
        generator = GlobalIDGenerator()

        start_memory = self.process.memory_info().rss / 1024 / 1024

        for iteration in range(10):
            entries = self._create_test_entries(1000)

            for entry in entries:
                _ = normalizer.normalize(entry["CanonicalLatin"])
                _ = generator.generate(entry)

            generator.clear()
            gc.collect()

        end_memory = self.process.memory_info().rss / 1024 / 1024
        memory_growth = end_memory - start_memory

        # Should not leak significantly over 10 iterations
        assert (
            memory_growth < 100
        ), f"Potential memory leak: {memory_growth:.1f}MB growth over 10 iterations"

    def test_memory_cleanup_between_stages(self):
        """Test that memory is reclaimed between processing stages."""
        normalizer = UnicodeNormalizer()

        entries = self._create_test_entries(5000)

        # Stage 1: Normalize
        stage1_results = []
        for entry in entries:
            stage1_results.append(normalizer.normalize(entry["CanonicalLatin"]))

        after_stage1 = self.process.memory_info().rss / 1024 / 1024

        # Clear stage 1 results
        del stage1_results
        gc.collect()

        after_cleanup = self.process.memory_info().rss / 1024 / 1024

        # Memory should decrease (or at least not increase significantly)
        # Python may not release all memory immediately
        assert after_cleanup < after_stage1 + 50, "Memory not reclaimed after stage cleanup"

    def test_memory_pressure_handling(self):
        """Test processing under memory pressure."""
        normalizer = UnicodeNormalizer()
        generator = GlobalIDGenerator()

        # Create entries with large metadata
        entries = []
        for i in range(2000):
            entry = {
                "CanonicalLatin": f"TestPerson{i:06d}, John",
                "CanonicalNative": f"TestPerson{i:06d}, John",
                "BirthYear": 1950 + (i % 70),
                "name_variants": [f"Variant{j}" for j in range(20)],
                "metadata": {f"field_{j}": f"value_{j}" * 10 for j in range(50)},
            }
            entries.append(entry)

        start_memory = self.process.memory_info().rss / 1024 / 1024

        for entry in entries:
            _ = normalizer.normalize(entry["CanonicalLatin"])
            _ = generator.generate(entry)

        end_memory = self.process.memory_info().rss / 1024 / 1024
        growth = end_memory - start_memory

        assert growth < 300, f"Excessive memory under pressure: {growth:.1f}MB"

    def test_concurrent_pipeline_memory_safety(self):
        """Test memory safety under concurrent processing."""
        normalizer = UnicodeNormalizer()
        results = Queue()

        def process_batch(batch_id, entries):
            try:
                for entry in entries:
                    _ = normalizer.normalize(entry["CanonicalLatin"])
                results.put((batch_id, len(entries), None))
            except Exception as e:
                results.put((batch_id, 0, str(e)))

        entries = self._create_test_entries(5000)
        num_workers = 4
        batch_size = len(entries) // num_workers

        threads = []
        for i in range(num_workers):
            batch = entries[i * batch_size : (i + 1) * batch_size]
            thread = threading.Thread(target=process_batch, args=(i, batch))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        worker_results = []
        while not results.empty():
            worker_results.append(results.get_nowait())

        assert len(worker_results) == num_workers
        for batch_id, count, error in worker_results:
            assert error is None, f"Worker {batch_id} failed: {error}"
            assert count > 0

    def test_memory_efficient_streaming(self):
        """Test streaming processing doesn't accumulate memory."""
        normalizer = UnicodeNormalizer()

        start_memory = self.process.memory_info().rss / 1024 / 1024

        # Process in streaming fashion (don't keep results)
        for i in range(10000):
            entry = {
                "CanonicalLatin": f"StreamPerson{i:06d}, John",
                "CanonicalNative": f"StreamPerson{i:06d}, John",
            }
            _ = normalizer.normalize(entry["CanonicalLatin"])

            if i % 2000 == 0:
                gc.collect()

        end_memory = self.process.memory_info().rss / 1024 / 1024
        growth = end_memory - start_memory

        assert growth < 100, f"Streaming should not accumulate memory: {growth:.1f}MB growth"

    def test_memory_limits_enforcement(self):
        """Test that processing stays within reasonable memory bounds."""
        normalizer = UnicodeNormalizer()
        generator = GlobalIDGenerator()

        entries = self._create_test_entries(5000)

        start_memory = self.process.memory_info().rss / 1024 / 1024

        for entry in entries:
            _ = normalizer.normalize(entry["CanonicalLatin"])
            _ = generator.generate(entry)

        end_memory = self.process.memory_info().rss / 1024 / 1024
        memory_per_entry_kb = ((end_memory - start_memory) * 1024) / len(entries)

        # Should use less than 50KB per entry
        assert memory_per_entry_kb < 50, f"Too much memory per entry: {memory_per_entry_kb:.1f}KB"

    def test_memory_optimization_strategies(self):
        """Test that clearing generators reclaims memory."""
        generator = GlobalIDGenerator()

        # Generate many IDs
        for i in range(5000):
            entry = {
                "CanonicalLatin": f"Person{i}, Test",
                "CanonicalNative": f"Person{i}, Test",
            }
            generator.generate(entry)

        assert len(generator._true_collisions) > 0

        # Clear should reclaim memory
        generator.clear()
        assert len(generator._true_collisions) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
