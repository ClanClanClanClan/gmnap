#!/usr/bin/env python3
"""
Batch Processing API for GMNAP V7
Implements parallel processing for improved throughput
"""

import asyncio
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import multiprocessing as mp
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.regions.manager_optimized import RegionManager, RegionDetectionResult


@dataclass
class BatchResult:
    """Result of batch processing."""

    total_entries: int
    successful: int
    failed: int
    processing_time: float
    entries_per_second: float
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]


class BatchProcessor:
    """
    Batch processing API for GMNAP with parallel execution support.
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize batch processor.

        Args:
            max_workers: Maximum number of parallel workers (default: CPU count)
        """
        self.max_workers = max_workers or mp.cpu_count()
        self._manager = None  # Lazy init

    @property
    def manager(self) -> RegionManager:
        """Get or create region manager (lazy initialization)."""
        if self._manager is None:
            self._manager = RegionManager()
        return self._manager

    def process_batch_sync(
        self, entries: List[Dict[str, Any]], chunk_size: int = 100
    ) -> BatchResult:
        """
        Process a batch of entries synchronously.

        Args:
            entries: List of entry dictionaries
            chunk_size: Size of chunks for progress reporting

        Returns:
            BatchResult with processing statistics
        """
        start_time = time.time()
        results = []
        errors = []

        # Process in chunks for progress reporting
        total = len(entries)
        for i in range(0, total, chunk_size):
            chunk = entries[i : i + chunk_size]
            chunk_results = self._process_chunk(chunk)

            for entry, result in zip(chunk, chunk_results):
                if isinstance(result, Exception):
                    errors.append({"entry": entry, "error": str(result)})
                else:
                    results.append({"entry": entry, "detection": result})

            # Progress report
            processed = min(i + chunk_size, total)
            print(f"Processed {processed}/{total} entries ({processed/total*100:.1f}%)")

        processing_time = time.time() - start_time

        return BatchResult(
            total_entries=total,
            successful=len(results),
            failed=len(errors),
            processing_time=processing_time,
            entries_per_second=total / processing_time if processing_time > 0 else 0,
            results=results,
            errors=errors,
        )

    def _process_chunk(self, entries: List[Dict[str, Any]]) -> List[Any]:
        """Process a chunk of entries."""
        results = []
        for entry in entries:
            try:
                result = self.manager.detect_region(entry, internal=True)
                results.append(result)
            except Exception as e:
                results.append(e)
        return results

    async def process_batch_async(
        self, entries: List[Dict[str, Any]], chunk_size: int = 100
    ) -> BatchResult:
        """
        Process a batch of entries asynchronously using thread pool.

        Args:
            entries: List of entry dictionaries
            chunk_size: Size of chunks for parallel processing

        Returns:
            BatchResult with processing statistics
        """
        start_time = time.time()

        # Split into chunks for parallel processing
        chunks = [
            entries[i : i + chunk_size] for i in range(0, len(entries), chunk_size)
        ]

        # Process chunks in parallel using thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            loop = asyncio.get_event_loop()

            # Submit all chunks for processing
            futures = [
                loop.run_in_executor(executor, self._process_chunk, chunk)
                for chunk in chunks
            ]

            # Wait for all chunks to complete
            chunk_results = await asyncio.gather(*futures)

        # Flatten results
        results = []
        errors = []

        for chunk, chunk_result in zip(chunks, chunk_results):
            for entry, result in zip(chunk, chunk_result):
                if isinstance(result, Exception):
                    errors.append({"entry": entry, "error": str(result)})
                else:
                    results.append({"entry": entry, "detection": result})

        processing_time = time.time() - start_time

        return BatchResult(
            total_entries=len(entries),
            successful=len(results),
            failed=len(errors),
            processing_time=processing_time,
            entries_per_second=(
                len(entries) / processing_time if processing_time > 0 else 0
            ),
            results=results,
            errors=errors,
        )

    def process_batch_multiprocess(
        self, entries: List[Dict[str, Any]], chunk_size: int = 1000
    ) -> BatchResult:
        """
        Process a batch using multiple processes for CPU-bound tasks.

        Args:
            entries: List of entry dictionaries
            chunk_size: Size of chunks per process

        Returns:
            BatchResult with processing statistics
        """
        start_time = time.time()

        # Split into chunks for multiprocessing
        chunks = [
            entries[i : i + chunk_size] for i in range(0, len(entries), chunk_size)
        ]

        # Process chunks in parallel using process pool
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            chunk_results = list(executor.map(_process_chunk_worker, chunks))

        # Flatten results
        results = []
        errors = []

        for chunk, chunk_result in zip(chunks, chunk_results):
            for entry, result in zip(chunk, chunk_result):
                if result.get("error"):
                    errors.append({"entry": entry, "error": result["error"]})
                else:
                    results.append({"entry": entry, "detection": result["detection"]})

        processing_time = time.time() - start_time

        return BatchResult(
            total_entries=len(entries),
            successful=len(results),
            failed=len(errors),
            processing_time=processing_time,
            entries_per_second=(
                len(entries) / processing_time if processing_time > 0 else 0
            ),
            results=results,
            errors=errors,
        )


def _process_chunk_worker(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Worker function for multiprocessing (runs in separate process)."""
    # Import here to avoid serialization issues
    from src.regions.manager_optimized import RegionManager

    manager = RegionManager()
    results = []

    for entry in entries:
        try:
            detection = manager.detect_region(entry, internal=True)
            results.append(
                {
                    "detection": {
                        "region_code": detection.region_code,
                        "confidence": detection.confidence,
                        "method": detection.detection_method,
                    },
                    "error": None,
                }
            )
        except Exception as e:
            results.append({"detection": None, "error": str(e)})

    return results


async def benchmark_batch_processing():
    """Benchmark different batch processing methods."""

    print("📊 BATCH PROCESSING BENCHMARK")
    print("=" * 50)

    # Generate test data
    test_sizes = [100, 1000, 5000]
    test_entries = [
        {"name": f"Test User {i}", "year": 2024} for i in range(max(test_sizes))
    ]

    processor = BatchProcessor(max_workers=4)

    for size in test_sizes:
        entries = test_entries[:size]
        print(f"\n\nTesting with {size} entries:")
        print("-" * 40)

        # Synchronous
        print("\n1. Synchronous processing:")
        result_sync = processor.process_batch_sync(entries, chunk_size=100)
        print(f"  Time: {result_sync.processing_time:.2f}s")
        print(f"  Speed: {result_sync.entries_per_second:.0f} entries/second")

        # Asynchronous
        print("\n2. Async processing (threads):")
        result_async = await processor.process_batch_async(entries, chunk_size=100)
        print(f"  Time: {result_async.processing_time:.2f}s")
        print(f"  Speed: {result_async.entries_per_second:.0f} entries/second")
        print(
            f"  Speedup: {result_sync.processing_time / result_async.processing_time:.1f}x"
        )

        # Multiprocess (only for larger batches)
        if size >= 1000:
            print("\n3. Multiprocess processing:")
            result_mp = processor.process_batch_multiprocess(entries, chunk_size=250)
            print(f"  Time: {result_mp.processing_time:.2f}s")
            print(f"  Speed: {result_mp.entries_per_second:.0f} entries/second")
            print(
                f"  Speedup: {result_sync.processing_time / result_mp.processing_time:.1f}x"
            )


def main():
    """Run benchmarks."""
    asyncio.run(benchmark_batch_processing())

    print("\n\n" + "=" * 50)
    print("BATCH PROCESSING API READY")
    print("=" * 50)
    print("\nUsage example:")
    print("```python")
    print("processor = BatchProcessor(max_workers=4)")
    print("result = processor.process_batch_sync(entries)")
    print(
        "print(f'Processed {result.successful} entries in {result.processing_time:.1f}s')"
    )
    print("```")


if __name__ == "__main__":
    main()
