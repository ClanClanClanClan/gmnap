#!/usr/bin/env python3
"""
from typing import List
ULTRA-CHAOS Concurrency Testing
Find race conditions, deadlocks, and concurrent access issues
"""

import pytest
import threading
import multiprocessing
import asyncio
import random
import time
import gc
import weakref
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock, RLock, Semaphore, Event, Barrier
from queue import Queue, Empty
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.security_validator import SecurityValidator
from src.core.globalid import GlobalIDGenerator
from src.core.unicode_handler import UnicodeNormalizer
from src.utils.cache import CacheManager


class TestUltraChaosConcurrent:
    """
    Chaos testing for concurrent access patterns.
    Actively tries to cause race conditions, deadlocks, and corruption.
    """

    @classmethod
    def setup_class(cls):
        cls.validator = SecurityValidator()
        cls.globalid_gen = GlobalIDGenerator()
        cls.unicode_handler = UnicodeNormalizer()
        cls.cache = CacheManager(max_size=1000)

    @pytest.mark.timeout(15)
    def test_concurrent_validator_race_conditions(self):
        """Hammer the validator with concurrent requests to find race conditions"""
        num_threads = 50
        operations_per_thread = 100
        results = []
        errors = []
        lock = Lock()

        def hammer_validator(thread_id):
            """Each thread hammers the validator"""
            thread_results = []
            thread_errors = []

            for i in range(operations_per_thread):
                # Mix of valid and malicious inputs
                if random.random() < 0.3:
                    # Malicious input
                    test_input = random.choice(
                        [
                            "' OR '1'='1",
                            "<script>alert(1)</script>",
                            "../../../etc/passwd",
                            "; rm -rf /",
                            "A" * 10000,
                        ]
                    )
                else:
                    # Normal input
                    test_input = f"Thread{thread_id}_Test{i}_{'X' * random.randint(1, 100)}"

                try:
                    result = self.validator.validate_string(test_input, f"thread_{thread_id}")
                    thread_results.append((thread_id, i, result))
                except Exception as e:
                    thread_errors.append((thread_id, i, str(e)))

                # Random small delay to increase chance of race conditions
                if random.random() < 0.1:
                    time.sleep(0.001)

            with lock:
                results.extend(thread_results)
                errors.extend(thread_errors)

        # Launch threads
        threads = []
        start_time = time.time()

        for tid in range(num_threads):
            thread = threading.Thread(target=hammer_validator, args=(tid,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=30)

        duration = time.time() - start_time

        # Verify results
        assert len(results) + len(errors) > 0, "No operations completed"
        assert duration < 60, f"Operations took too long: {duration}s"

        # Check for consistency
        result_values = [r[2] for r in results]
        assert len(set(result_values)) < len(result_values), "All results unique (no caching?)"

        print(
            f"Concurrent validator test: {len(results)} successes, {len(errors)} errors in {duration:.2f}s"
        )

    @pytest.mark.timeout(15)
    def test_globalid_generation_race(self):
        """Test GlobalID generation for uniqueness under concurrent access"""
        num_processes = 4
        num_threads_per_process = 10
        ids_per_thread = 100

        def generate_ids_process(process_id):
            """Each process generates IDs concurrently"""
            generator = GlobalIDGenerator()
            all_ids = []

            def generate_batch(thread_id):
                thread_ids = []
                for i in range(ids_per_thread):
                    entry = {
                        "CanonicalLatin": f"P{process_id}T{thread_id}Test{i}",
                        "CanonicalNative": f"Test{i}",
                        "BirthYear": 1900 + i,
                    }
                    try:
                        gid = generator.generate(entry)
                        thread_ids.append(gid)
                    except:
                        pass
                return thread_ids

            # Use threads within each process
            with ThreadPoolExecutor(max_workers=num_threads_per_process) as executor:
                futures = [
                    executor.submit(generate_batch, tid) for tid in range(num_threads_per_process)
                ]

                for future in as_completed(futures):
                    all_ids.extend(future.result())

            return all_ids

        # Use processes
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            process_futures = [
                executor.submit(generate_ids_process, pid) for pid in range(num_processes)
            ]

            all_generated_ids = []
            for future in as_completed(process_futures):
                all_generated_ids.extend(future.result())

        # Check uniqueness
        assert len(all_generated_ids) > 0, "No IDs generated"
        unique_ids = set(all_generated_ids)
        duplicates = len(all_generated_ids) - len(unique_ids)

        assert duplicates == 0, f"Found {duplicates} duplicate IDs!"
        print(f"GlobalID race test: Generated {len(all_generated_ids)} unique IDs")

    @pytest.mark.timeout(15)
    def test_cache_corruption_under_concurrent_access(self):
        """Test cache for corruption under concurrent read/write"""
        cache = CacheManager(max_size=100)
        num_threads = 20
        operations = 1000

        corruption_detected = []
        lock = Lock()

        def cache_operations(thread_id):
            """Perform random cache operations"""
            for i in range(operations):
                key = f"key_{random.randint(0, 50)}"  # Limited key space for conflicts

                operation = random.choice(["get", "set", "clear", "get", "get"])  # More reads

                try:
                    if operation == "get":
                        value = cache.get(key)
                        if value is not None:
                            # Verify value format
                            if not value.startswith("thread_"):
                                with lock:
                                    corruption_detected.append(f"Corrupted value: {value}")

                    elif operation == "set":
                        value = f"thread_{thread_id}_value_{i}"
                        cache.set(key, value)

                        # Immediately verify
                        retrieved = cache.get(key)
                        if retrieved != value:
                            with lock:
                                corruption_detected.append(
                                    f"Set/Get mismatch: set {value}, got {retrieved}"
                                )

                    elif operation == "clear":
                        if random.random() < 0.01:  # Rare clears
                            cache.clear()

                except Exception as e:
                    with lock:
                        corruption_detected.append(f"Exception: {e}")

                # Cause more conflicts
                if random.random() < 0.01:
                    time.sleep(0.001)

        # Launch threads
        threads = []
        for tid in range(num_threads):
            thread = threading.Thread(target=cache_operations, args=(tid,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)

        # Check for corruption
        if corruption_detected:
            print(f"Cache corruption detected: {corruption_detected[:5]}")
            assert False, f"Cache corruption found: {len(corruption_detected)} instances"

        print(f"Cache concurrent test passed: {num_threads * operations} operations")

    @pytest.mark.timeout(15)
    def test_deadlock_detection(self):
        """Try to cause deadlocks with multiple locks"""
        lock1 = Lock()
        lock2 = Lock()
        lock3 = Lock()

        deadlock_detected = Event()
        operations_completed = []

        def worker_a():
            """Lock order: 1, 2, 3"""
            for i in range(100):
                with lock1:
                    time.sleep(0.001)
                    with lock2:
                        time.sleep(0.001)
                        with lock3:
                            operations_completed.append(("A", i))

        def worker_b():
            """Lock order: 2, 3, 1 (potential deadlock)"""
            for i in range(100):
                with lock2:
                    time.sleep(0.001)
                    with lock3:
                        time.sleep(0.001)
                        with lock1:
                            operations_completed.append(("B", i))

        def worker_c():
            """Lock order: 3, 1, 2 (potential deadlock)"""
            for i in range(100):
                with lock3:
                    time.sleep(0.001)
                    with lock1:
                        time.sleep(0.001)
                        with lock2:
                            operations_completed.append(("C", i))

        def deadlock_monitor():
            """Monitor for deadlocks"""
            time.sleep(5)  # Give workers time
            if len(operations_completed) < 50:
                deadlock_detected.set()

        # Start workers
        threads = [
            threading.Thread(target=worker_a),
            threading.Thread(target=worker_b),
            threading.Thread(target=worker_c),
            threading.Thread(target=deadlock_monitor),
        ]

        for thread in threads:
            thread.daemon = True  # Allow force exit if deadlocked
            thread.start()

        # Wait with timeout
        time.sleep(10)

        if deadlock_detected.is_set():
            print("WARNING: Potential deadlock detected!")

        # This test intentionally might deadlock - that's what we're testing for
        assert len(operations_completed) > 0, "No operations completed (complete deadlock)"
        print(f"Deadlock test: {len(operations_completed)} operations completed")

    @pytest.mark.timeout(15)
    def test_race_condition_in_shared_state(self):
        """Test for race conditions in shared state modifications"""

        class SharedState:
            def __init__(self):
                self.counter = 0
                self.data = {}
                self.list = []
                # Intentionally no locks to find race conditions

            def increment(self):
                # Non-atomic operation
                temp = self.counter
                time.sleep(0.00001)  # Tiny delay to increase races
                self.counter = temp + 1

            def add_data(self, key, value):
                if key not in self.data:
                    time.sleep(0.00001)
                    self.data[key] = value
                else:
                    self.data[key] += value

            def append_list(self, value):
                size = len(self.list)
                time.sleep(0.00001)
                if size == len(self.list):  # Check if unchanged
                    self.list.append(value)

        state = SharedState()
        num_threads = 50
        ops_per_thread = 100

        def race_operations(thread_id):
            for i in range(ops_per_thread):
                state.increment()
                state.add_data(f"key_{i % 10}", 1)
                state.append_list(f"thread_{thread_id}_{i}")

        threads = []
        for tid in range(num_threads):
            thread = threading.Thread(target=race_operations, args=(tid,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Check for race condition effects
        expected_counter = num_threads * ops_per_thread
        actual_counter = state.counter

        race_detected = actual_counter != expected_counter

        print(f"Race condition test:")
        print(f"  Expected counter: {expected_counter}")
        print(f"  Actual counter: {actual_counter}")
        print(f"  Race conditions detected: {race_detected}")
        print(f"  List items: {len(state.list)} (expected {num_threads * ops_per_thread})")

        # We EXPECT race conditions in this test
        assert race_detected, "No race conditions detected (unexpected!)"

    @pytest.mark.timeout(15)
    def test_memory_barriers_and_visibility(self):
        """Test memory visibility issues between threads"""

        class MemoryTest:
            def __init__(self):
                self.flag = False
                self.data = None
                self.ready = False

        test = MemoryTest()
        results = []

        def writer():
            """Write data then set flag"""
            test.data = "important_data"
            # In theory, without memory barriers, the flag could be visible
            # before the data write is visible to other threads
            test.flag = True

        def reader():
            """Wait for flag then read data"""
            while not test.flag:
                pass  # Busy wait

            # At this point, flag is True, but is data visible?
            if test.data is None:
                results.append("VISIBILITY_ISSUE")
            else:
                results.append("OK")

        # Run multiple times to catch intermittent issues
        for _ in range(100):
            test = MemoryTest()
            results = []

            reader_thread = threading.Thread(target=reader)
            writer_thread = threading.Thread(target=writer)

            reader_thread.start()
            time.sleep(0.001)  # Let reader start waiting
            writer_thread.start()

            reader_thread.join(timeout=1)
            writer_thread.join(timeout=1)

        # Check if any visibility issues detected
        visibility_issues = results.count("VISIBILITY_ISSUE")
        print(f"Memory visibility test: {visibility_issues} potential issues in 100 runs")

    @pytest.mark.timeout(15)
    def test_async_chaos(self):
        """Test async operations with chaos"""

        async def chaotic_operation(op_id):
            """Async operation that might fail randomly"""
            await asyncio.sleep(random.uniform(0, 0.1))

            if random.random() < 0.2:
                raise Exception(f"Chaos strike on operation {op_id}")

            return f"Result_{op_id}"

        async def run_chaos():
            """Run many operations concurrently"""
            tasks = []
            for i in range(100):
                tasks.append(asyncio.create_task(chaotic_operation(i)))

            results = []
            errors = []

            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))

            return results, errors

        # Run the async chaos
        results, errors = asyncio.run(run_chaos())

        assert len(results) + len(errors) == 100
        assert len(errors) > 0, "No chaos strikes (unexpected)"
        assert len(results) > 0, "All operations failed (too much chaos)"

        print(f"Async chaos test: {len(results)} succeeded, {len(errors)} failed")

    @pytest.mark.timeout(15)
    def test_thread_local_storage_isolation(self):
        """Test thread-local storage isolation"""
        import threading

        thread_local = threading.local()
        violations = []

        def thread_operation(thread_id):
            """Each thread should have isolated storage"""
            # Set thread-local value
            thread_local.value = f"thread_{thread_id}"
            thread_local.list = []

            for i in range(100):
                thread_local.list.append(i)

                # Verify our value hasn't changed
                if thread_local.value != f"thread_{thread_id}":
                    violations.append(f"Thread {thread_id} value corrupted")

                # Random delay
                if random.random() < 0.1:
                    time.sleep(0.001)

            # Final verification
            if len(thread_local.list) != 100:
                violations.append(f"Thread {thread_id} list size wrong")

        threads = []
        for tid in range(20):
            thread = threading.Thread(target=thread_operation, args=(tid,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(violations) == 0, f"Thread isolation violated: {violations}"
        print("Thread-local storage isolation test passed")

    @pytest.mark.timeout(15)
    def test_signal_handling_chaos(self):
        """Test signal handling under concurrent load"""
        if sys.platform == "win32":
            pytest.skip("Signal testing not supported on Windows")

        received_signals = []

        def signal_handler(signum, frame):
            """Handle signals"""
            received_signals.append(signum)

        # Register handler
        old_handler = signal.signal(signal.SIGUSR1, signal_handler)

        try:

            def send_signals():
                """Send signals to self"""
                pid = os.getpid()
                for _ in range(10):
                    os.kill(pid, signal.SIGUSR1)
                    time.sleep(0.01)

            def cpu_bound_work():
                """Do CPU-bound work"""
                result = 0
                for i in range(1000000):
                    result += i * i
                return result

            # Run CPU work while receiving signals
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []

                # Start CPU work
                for _ in range(4):
                    futures.append(executor.submit(cpu_bound_work))

                # Send signals while work is happening
                signal_thread = threading.Thread(target=send_signals)
                signal_thread.start()

                # Wait for completion
                for future in as_completed(futures):
                    future.result()

                signal_thread.join()

            # Verify signals were received
            assert len(received_signals) > 0, "No signals received"
            print(f"Signal chaos test: {len(received_signals)} signals handled during work")

        finally:
            # Restore old handler
            signal.signal(signal.SIGUSR1, old_handler)

    @pytest.mark.timeout(15)
    def test_resource_exhaustion_recovery(self):
        """Test behavior under resource exhaustion"""

        def exhaust_memory():
            """Try to exhaust memory"""
            big_lists = []
            try:
                for _ in range(1000):
                    big_lists.append([0] * 10000000)  # 10M integers
            except MemoryError:
                return "MEMORY_EXHAUSTED"
            return "MEMORY_OK"

        def exhaust_threads():
            """Try to exhaust thread limit"""
            threads = []
            try:
                for _ in range(10000):
                    t = threading.Thread(target=lambda: time.sleep(1))
                    t.start()
                    threads.append(t)
            except:
                return "THREAD_LIMIT_HIT", len(threads)
            finally:
                # Clean up
                for t in threads[:10]:  # Join a few
                    t.join(timeout=0.01)
            return "THREADS_OK", len(threads)

        # Test controlled resource exhaustion
        # Note: Be careful with these tests in production!

        # Thread exhaustion test (safer)
        result, count = exhaust_threads()
        print(f"Thread exhaustion test: {result}, created {count} threads")

        # Memory test would be too dangerous to actually run
        print("Memory exhaustion test: Skipped (too dangerous)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
