"""
from typing import Dict
HELL-LEVEL PARANOID PERFORMANCE TESTING
=======================================

This module contains comprehensive performance stress tests designed to find
memory leaks, performance degradation, resource exhaustion, and scalability issues.

These tests push the system to its absolute limits.
"""

import pytest
import time
import gc
import threading
import multiprocessing
import psutil
import os
import sys
import tracemalloc
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from collections import deque
import random
import string
from typing import List, Dict, Tuple
import weakref

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.regions.manager_optimized import RegionManager
from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
from src.core.config import GMNAPConfig


class MemoryMonitor:
    """Monitor memory usage during tests."""

    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
        tracemalloc.start()

    def get_memory_mb(self):
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def get_memory_growth_mb(self):
        """Get memory growth since initialization."""
        current = self.process.memory_info().rss
        return (current - self.initial_memory) / 1024 / 1024

    def get_tracemalloc_top(self, limit=10):
        """Get top memory allocations."""
        snapshot = tracemalloc.take_snapshot()
        return snapshot.statistics("lineno")[:limit]

    def cleanup(self):
        """Cleanup monitoring."""
        tracemalloc.stop()


class TestPerformanceHell:
    """Hell-level performance testing."""

    @pytest.fixture
    def memory_monitor(self):
        """Memory monitoring fixture."""
        monitor = MemoryMonitor()
        yield monitor
        monitor.cleanup()

    @pytest.fixture
    def region_manager(self):
        """Fresh region manager."""
        return RegionManager()

    # ========== MEMORY LEAK HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_memory_leak_detection_sustained(self, region_manager, memory_monitor):
        """Test for memory leaks under sustained load."""

        # Test data
        test_names = [
            "Smith, John",
            "García, José",
            "김정은",
            "Wang, Wei",
            "Al-Ahmad, Mohammed",
            "Müller, Hans",
            "Ivanov, Vladimir",
            "田中太郎",
        ]

        initial_memory = memory_monitor.get_memory_mb()
        memory_samples = []

        # Run sustained processing for 1000 iterations
        for iteration in range(1000):
            # Process each test name
            for name in test_names:
                entry = {"CanonicalLatin": name}
                result = region_manager.detect_region(entry)

                # Ensure we're actually using the result
                _ = str(result)
                _ = result.region_code
                _ = result.confidence

            # Sample memory every 100 iterations
            if iteration % 100 == 0:
                gc.collect()  # Force garbage collection
                current_memory = memory_monitor.get_memory_mb()
                memory_growth = current_memory - initial_memory
                memory_samples.append((iteration, current_memory, memory_growth))

                print(f"Iteration {iteration}: {current_memory:.2f} MB (+{memory_growth:.2f} MB)")

        # Analyze memory growth
        final_memory = memory_monitor.get_memory_mb()
        total_growth = final_memory - initial_memory

        # Memory growth should be minimal (< 50 MB)
        assert (
            total_growth < 50.0
        ), f"Excessive memory growth detected: {total_growth:.2f} MB. Samples: {memory_samples}"

        # Memory growth should be sub-linear (slope decreasing)
        if len(memory_samples) >= 3:
            growth_rates = []
            for i in range(1, len(memory_samples)):
                prev_iter, prev_mem, prev_growth = memory_samples[i - 1]
                curr_iter, curr_mem, curr_growth = memory_samples[i]

                iter_diff = curr_iter - prev_iter
                mem_diff = curr_mem - prev_mem
                growth_rate = mem_diff / iter_diff if iter_diff > 0 else 0
                growth_rates.append(growth_rate)

            # Growth rate should stabilize or decrease
            if len(growth_rates) >= 2:
                avg_early = sum(growth_rates[: len(growth_rates) // 2]) / (len(growth_rates) // 2)
                avg_late = sum(growth_rates[len(growth_rates) // 2 :]) / (
                    len(growth_rates) - len(growth_rates) // 2
                )

                # Later growth rate should not be significantly higher
                assert (
                    avg_late <= avg_early * 2.0
                ), f"Memory leak detected: growth rate increasing {avg_early:.4f} -> {avg_late:.4f}"

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_memory_leak_object_references(self, region_manager, memory_monitor):
        """Test for object reference leaks."""

        # Track object counts
        initial_objects = len(gc.get_objects())

        # Create weak references to track object lifecycle
        weak_refs = []

        for i in range(100):
            entry = {"CanonicalLatin": f"Smith{i}, John{i}"}
            result = region_manager.detect_region(entry)

            # Create weak reference to track if objects are being released
            try:
                weak_refs.append(weakref.ref(result))
            except TypeError:
                pass  # Some objects can't have weak references

        # Force garbage collection
        gc.collect()

        # Check object count growth
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        # Should not create excessive objects
        assert object_growth < 1000, f"Excessive object creation: {object_growth} new objects"

        # Check weak references - some should have been released
        live_refs = sum(1 for ref in weak_refs if ref() is not None)
        dead_refs = len(weak_refs) - live_refs

        # At least some objects should have been garbage collected
        assert (
            dead_refs > 0
        ), f"No objects were garbage collected: {live_refs}/{len(weak_refs)} still live"

    # ========== CONCURRENCY HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_concurrent_access_stress(self, memory_monitor):
        """Test concurrent access under extreme stress."""

        results = []
        errors = []

        def worker(worker_id, iterations):
            """Worker function for stress testing."""
            manager = RegionManager()  # Each worker gets its own manager
            worker_results = []

            for i in range(iterations):
                try:
                    test_names = [
                        f"Smith{worker_id}-{i}",
                        f"García{worker_id}-{i}",
                        f"김{worker_id}-{i}",
                        f"Wang{worker_id}-{i}",
                    ]

                    for name in test_names:
                        entry = {"CanonicalLatin": name}
                        result = manager.detect_region(entry)
                        worker_results.append(
                            (worker_id, i, name, result.region_code, result.confidence)
                        )

                except Exception as e:
                    errors.append((worker_id, i, str(e)))

            return worker_results

        # Launch many concurrent workers
        num_workers = min(20, multiprocessing.cpu_count() * 2)  # Don't overwhelm the system
        iterations_per_worker = 50

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []

            for worker_id in range(num_workers):
                future = executor.submit(worker, worker_id, iterations_per_worker)
                futures.append(future)

            # Wait for all workers to complete
            for future in futures:
                try:
                    worker_results = future.result(timeout=60)  # 60 second timeout
                    results.extend(worker_results)
                except Exception as e:
                    errors.append(("executor", -1, str(e)))

        # Analyze results
        total_expected = num_workers * iterations_per_worker * 4  # 4 names per iteration
        total_actual = len(results)

        assert (
            len(errors) == 0
        ), f"Concurrent access errors: {errors[:10]}..."  # Show first 10 errors
        assert (
            total_actual == total_expected
        ), f"Missing results: expected {total_expected}, got {total_actual}"

        # Check for data corruption
        region_codes = [r[3] for r in results]
        valid_regions = {
            "A1",
            "A2",
            "B1",
            "B2",
            "C2",
            "C3",
            "C4",
            "D1",
            "E1",
            "E3",
            "E4",
            "G1",
            "A3",
            "B3",
        }
        invalid_regions = [code for code in region_codes if code not in valid_regions]

        assert (
            len(invalid_regions) == 0
        ), f"Data corruption detected: invalid regions {set(invalid_regions)}"

        # Check memory growth
        memory_growth = memory_monitor.get_memory_growth_mb()
        assert (
            memory_growth < 200
        ), f"Excessive memory growth during concurrency: {memory_growth:.2f} MB"

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_thread_safety_data_races(self):
        """Test for thread safety and data races."""

        # Shared state to detect races
        shared_counter = {"value": 0}
        results = []
        lock = threading.Lock()

        def racing_worker(worker_id):
            """Worker that might cause data races."""
            manager = RegionManager()

            for i in range(100):
                # Increment shared counter (potential race condition)
                with lock:
                    shared_counter["value"] += 1
                    expected_count = shared_counter["value"]

                # Process name
                entry = {"CanonicalLatin": f"RaceTest{worker_id}-{i}"}
                result = manager.detect_region(entry)

                # Store result with expected count
                results.append((worker_id, i, expected_count, result.region_code))

                # Brief sleep to increase chance of race conditions
                time.sleep(0.001)

        # Launch racing threads
        threads = []
        num_threads = 10

        for i in range(num_threads):
            thread = threading.Thread(target=racing_worker, args=(i,))
            threads.append(thread)

        # Start all threads simultaneously
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)

        end_time = time.time()

        # Verify results
        expected_total = num_threads * 100
        assert len(results) == expected_total, f"Missing results: {len(results)}/{expected_total}"
        assert (
            shared_counter["value"] == expected_total
        ), f"Counter race condition: {shared_counter['value']}/{expected_total}"

        # Check for duplicate or missing sequence numbers
        sequence_numbers = [r[2] for r in results]
        unique_sequences = set(sequence_numbers)

        assert (
            len(unique_sequences) == expected_total
        ), f"Sequence race condition: {len(unique_sequences)}/{expected_total}"
        assert min(sequence_numbers) == 1, f"Missing early sequences: min={min(sequence_numbers)}"
        assert (
            max(sequence_numbers) == expected_total
        ), f"Missing late sequences: max={max(sequence_numbers)}"

        # Performance check
        total_time = end_time - start_time
        ops_per_second = expected_total / total_time

        print(f"Thread safety test: {ops_per_second:.2f} ops/sec, {total_time:.2f}s total")

        # Should maintain reasonable performance under concurrency
        assert (
            ops_per_second > 50
        ), f"Performance degraded under concurrency: {ops_per_second:.2f} ops/sec"

    # ========== RESOURCE EXHAUSTION HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_massive_input_handling(self, region_manager, memory_monitor):
        """Test handling of massive inputs."""

        # Test increasingly large inputs
        sizes = [1024, 10 * 1024, 100 * 1024, 1024 * 1024]  # 1KB to 1MB

        for size in sizes:
            # Create massive input
            massive_input = "A" * size
            entry = {"CanonicalLatin": massive_input}

            start_memory = memory_monitor.get_memory_mb()
            start_time = time.perf_counter()

            try:
                result = region_manager.detect_region(entry)

                end_time = time.perf_counter()
                end_memory = memory_monitor.get_memory_mb()

                processing_time = end_time - start_time
                memory_used = end_memory - start_memory

                # Should handle gracefully without excessive resource usage
                assert (
                    processing_time < 5.0
                ), f"Excessive processing time for {size} bytes: {processing_time:.2f}s"

                assert (
                    memory_used < size / 1024 + 50
                ), f"Excessive memory usage for {size} bytes: {memory_used:.2f} MB"

                # Result should not contain the massive input
                result_str = str(result)
                assert (
                    len(result_str) < 1000
                ), f"Result too large for massive input: {len(result_str)} chars"

            except Exception as e:
                # Should fail gracefully for very large inputs
                error_msg = str(e).lower()
                processing_time = time.perf_counter() - start_time

                # Should fail quickly, not hang
                assert (
                    processing_time < 5.0
                ), f"Slow failure for {size} bytes: {processing_time:.2f}s"

                # Should be a reasonable error, not a crash
                assert (
                    "memory" in error_msg or "size" in error_msg or "length" in error_msg
                ), f"Unexpected error for massive input: {e}"

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_batch_processing_scalability(self, memory_monitor):
        """Test scalability of batch processing."""

        manager = RegionManager()

        # Test batch sizes from small to very large
        batch_sizes = [10, 100, 1000, 5000]
        performance_metrics = []

        for batch_size in batch_sizes:
            # Generate batch
            batch = []
            for i in range(batch_size):
                names = [
                    f"Smith{i}, John{i}",
                    f"García{i}, José{i}",
                    f"김{i}, 정은{i}",
                    f"Wang{i}, Wei{i}",
                ]
                batch.extend(names)

            # Process batch
            start_time = time.perf_counter()
            start_memory = memory_monitor.get_memory_mb()

            results = []
            for name in batch:
                entry = {"CanonicalLatin": name}
                result = manager.detect_region(entry)
                results.append(result)

            end_time = time.perf_counter()
            end_memory = memory_monitor.get_memory_mb()

            # Calculate metrics
            total_time = end_time - start_time
            memory_used = end_memory - start_memory
            ops_per_second = len(batch) / total_time
            memory_per_op = memory_used / len(batch) if len(batch) > 0 else 0

            performance_metrics.append(
                {
                    "batch_size": len(batch),
                    "total_time": total_time,
                    "ops_per_second": ops_per_second,
                    "memory_used": memory_used,
                    "memory_per_op": memory_per_op,
                }
            )

            # Force garbage collection between batches
            gc.collect()

            print(f"Batch {len(batch)}: {ops_per_second:.2f} ops/sec, {memory_used:.2f} MB")

        # Analyze scalability
        # Performance should not degrade dramatically with larger batches
        first_ops = performance_metrics[0]["ops_per_second"]
        last_ops = performance_metrics[-1]["ops_per_second"]

        performance_ratio = first_ops / last_ops if last_ops > 0 else float("inf")

        assert (
            performance_ratio < 3.0
        ), f"Performance degradation too severe: {first_ops:.2f} -> {last_ops:.2f} ops/sec (ratio: {performance_ratio:.2f})"

        # Memory usage per operation should remain reasonable
        max_memory_per_op = max(m["memory_per_op"] for m in performance_metrics)
        assert (
            max_memory_per_op < 1.0
        ), f"Excessive memory per operation: {max_memory_per_op:.2f} MB/op"

    # ========== STRESS TESTING HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_sustained_load_endurance(self, memory_monitor):
        """Test system endurance under sustained load."""

        manager = RegionManager()

        # Run for 5 minutes or 10,000 operations, whichever comes first
        max_duration = 300  # 5 minutes
        max_operations = 10000

        start_time = time.time()
        operations = 0
        errors = []
        performance_samples = []

        test_names = [
            "Smith, John",
            "García, José María",
            "김정은",
            "Wang, Wei Ming",
            "Al-Ahmad, Mohammed",
            "Müller, Hans-Peter",
            "Ivanov, Vladimir Sergeevich",
            "田中太郎",
        ]

        while time.time() - start_time < max_duration and operations < max_operations:
            # Select random name
            name = random.choice(test_names)
            entry = {"CanonicalLatin": name}

            op_start = time.perf_counter()

            try:
                result = region_manager.detect_region(entry)

                # Verify result integrity
                valid_regions = {
                    "A1",
                    "A2",
                    "B1",
                    "B2",
                    "C2",
                    "C3",
                    "C4",
                    "D1",
                    "E1",
                    "E3",
                    "E4",
                    "G1",
                    "A3",
                    "B3",
                }
                if result.region_code not in valid_regions:
                    errors.append(f"Invalid region: {result.region_code}")

                if not (0.0 <= result.confidence <= 1.0):
                    errors.append(f"Invalid confidence: {result.confidence}")

            except Exception as e:
                errors.append(f"Operation {operations}: {str(e)}")

            op_end = time.perf_counter()
            op_time = op_end - op_start
            operations += 1

            # Sample performance every 1000 operations
            if operations % 1000 == 0:
                current_memory = memory_monitor.get_memory_mb()
                elapsed_time = time.time() - start_time
                ops_per_second = operations / elapsed_time

                performance_samples.append(
                    {
                        "operations": operations,
                        "elapsed_time": elapsed_time,
                        "ops_per_second": ops_per_second,
                        "memory_mb": current_memory,
                        "op_time": op_time,
                    }
                )

                print(
                    f"Endurance {operations}: {ops_per_second:.2f} ops/sec, {current_memory:.2f} MB"
                )

                # Force periodic garbage collection
                gc.collect()

        total_time = time.time() - start_time
        final_ops_per_sec = operations / total_time

        # Check for errors
        error_rate = len(errors) / operations if operations > 0 else 1.0
        assert (
            error_rate < 0.01
        ), f"High error rate during endurance test: {error_rate:.2%}, errors: {errors[:10]}..."

        # Check performance stability
        if len(performance_samples) >= 2:
            first_sample = performance_samples[0]
            last_sample = performance_samples[-1]

            performance_degradation = first_sample["ops_per_second"] / last_sample["ops_per_second"]

            assert (
                performance_degradation < 2.0
            ), f"Performance degraded during endurance test: {first_sample['ops_per_second']:.2f} -> {last_sample['ops_per_second']:.2f}"

        # Check memory stability
        memory_growth = memory_monitor.get_memory_growth_mb()
        assert (
            memory_growth < 100
        ), f"Excessive memory growth during endurance: {memory_growth:.2f} MB"

        print(
            f"Endurance test completed: {operations} operations in {total_time:.2f}s ({final_ops_per_sec:.2f} ops/sec)"
        )

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_pathological_input_stress(self, region_manager, memory_monitor):
        """Test with pathological inputs designed to stress the system."""

        pathological_inputs = [
            # Extremely repetitive
            "A" * 10000,
            "김" * 1000,
            "," * 500,
            # Deeply nested structures (conceptual)
            "(" * 1000 + "Smith" + ")" * 1000,
            "[" * 500 + "García" + "]" * 500,
            # Unicode normalization stress
            "e" + "\u0301" * 100,  # Many combining characters
            "a" + "\u0300\u0301\u0302\u0303\u0304" * 50,
            # Mixed scripts chaos
            "Smith김García王Ahmed田中José" * 100,
            # Every Unicode category
            "".join(chr(i) for i in range(0x20, 0x7E)) * 10,  # Basic Latin
            "".join(chr(i) for i in range(0xA0, 0xFF)) * 10,  # Latin-1 Supplement
            # RTL/LTR chaos
            "Smith أحمد García محمد Kim עברית Wang" * 50,
            # Zero-width character bombing
            "Smith" + "\u200b" * 1000 + "John",
            "García" + "\u200c" * 500 + "José",
            # Homograph attacks
            "Ѕmith" * 100,  # Cyrillic S
            "Αlex" * 200,  # Greek Alpha
            # Format string attempts
            "%s" * 1000,
            "{}" * 500,
            "${}" * 300,
            # Regex DoS attempts
            "a" * 10000 + "!",
            "(" * 5000 + "a" + ")" * 5000,
        ]

        errors = []
        slow_operations = []

        for i, pathological_input in enumerate(pathological_inputs):
            entry = {"CanonicalLatin": pathological_input}

            start_memory = memory_monitor.get_memory_mb()
            start_time = time.perf_counter()

            try:
                result = region_manager.detect_region(entry)

                end_time = time.perf_counter()
                end_memory = memory_monitor.get_memory_mb()

                processing_time = end_time - start_time
                memory_used = end_memory - start_memory

                # Should handle pathological input quickly
                if processing_time > 1.0:
                    slow_operations.append((i, processing_time, len(pathological_input)))

                # Should not use excessive memory
                if memory_used > 100:
                    errors.append(f"Input {i}: Excessive memory {memory_used:.2f} MB")

                # Result should be reasonable
                result_str = str(result)
                if len(result_str) > 1000:
                    errors.append(f"Input {i}: Result too large {len(result_str)} chars")

            except Exception as e:
                end_time = time.perf_counter()
                processing_time = end_time - start_time

                # Should fail quickly
                if processing_time > 1.0:
                    slow_operations.append((i, processing_time, len(pathological_input)))

                # Should be a reasonable error
                error_msg = str(e).lower()
                if "crash" in error_msg or "segmentation" in error_msg:
                    errors.append(f"Input {i}: Hard crash - {e}")

            # Force cleanup between pathological inputs
            gc.collect()

        # Check results
        assert len(errors) == 0, f"Pathological input errors: {errors}"

        if slow_operations:
            print(f"Slow operations detected: {slow_operations}")

            # Allow some slow operations, but not too many
            slow_ratio = len(slow_operations) / len(pathological_inputs)
            assert slow_ratio < 0.2, f"Too many slow operations: {slow_ratio:.2%}"

            # Very slow operations are not acceptable
            very_slow = [op for op in slow_operations if op[1] > 5.0]
            assert len(very_slow) == 0, f"Very slow operations (>5s): {very_slow}"


@pytest.mark.paranoid
class TestResourceLimits:
    """Test resource limit handling."""

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_cpu_time_limits(self):
        """Test CPU time limit handling."""
        manager = RegionManager()

        # CPU intensive operations
        cpu_intensive_inputs = [
            # Regex backtracking worst case
            "a" * 1000 + "X",
            "(" * 500 + "a" + ")" * 500,
            # Unicode normalization intensive
            "e" + "\u0301" * 500,
            # Large input processing
            "김" * 5000,
            "García" * 2000,
        ]

        cpu_times = []

        for cpu_input in cpu_intensive_inputs:
            entry = {"CanonicalLatin": cpu_input}

            start_time = time.perf_counter()

            try:
                result = manager.detect_region(entry)

                end_time = time.perf_counter()
                cpu_time = end_time - start_time
                cpu_times.append(cpu_time)

                # No single operation should take more than 5 seconds
                assert (
                    cpu_time < 5.0
                ), f"CPU time limit exceeded: {cpu_time:.2f}s for input length {len(cpu_input)}"

            except Exception as e:
                end_time = time.perf_counter()
                cpu_time = end_time - start_time
                cpu_times.append(cpu_time)

                # Even failures should be quick
                assert (
                    cpu_time < 5.0
                ), f"Slow failure: {cpu_time:.2f}s for input length {len(cpu_input)}"

        # Average CPU time should be reasonable
        avg_cpu_time = sum(cpu_times) / len(cpu_times)
        assert avg_cpu_time < 1.0, f"Average CPU time too high: {avg_cpu_time:.2f}s"

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_file_descriptor_limits(self):
        """Test file descriptor limit handling."""

        # This test creates many managers to potentially exhaust file descriptors
        managers = []

        try:
            for i in range(100):  # Create many instances
                manager = RegionManager()
                managers.append(manager)

                # Test that each manager still works
                entry = {"CanonicalLatin": f"Smith{i}, John{i}"}
                result = manager.detect_region(entry)

                assert hasattr(result, "region_code"), f"Manager {i} not functional"

        except Exception as e:
            # Should fail gracefully if resource limits hit
            error_msg = str(e).lower()
            assert (
                "file" in error_msg or "descriptor" in error_msg or "resource" in error_msg
            ), f"Unexpected error when hitting resource limits: {e}"

        finally:
            # Cleanup
            managers.clear()
            gc.collect()


if __name__ == "__main__":
    # Run with: pytest tests/paranoid/performance/test_performance_hell.py -v --tb=short -s
    pytest.main([__file__, "-v", "--tb=short", "-s"])
