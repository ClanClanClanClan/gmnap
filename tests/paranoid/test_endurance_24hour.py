#!/usr/bin/env python3
"""
from typing import List
from typing import Optional
from typing import Any
24-HOUR ENDURANCE TEST SUITE
Tests system stability over extended periods to find:
- Memory leaks
- Resource exhaustion
- Performance degradation
- File handle leaks
- Thread leaks
- Database connection exhaustion
- Cache overflow
- Log file growth
"""

import gc
import os
import random
import string
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict

import psutil

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.globalid import GlobalIDGenerator
from src.core.security_validator import SecurityValidator
from src.core.unicode_handler import UnicodeNormalizer
from src.regions.manager import RegionManager


class EnduranceMonitor:
    """Monitor system health during endurance tests"""

    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            "memory": [],
            "cpu": [],
            "threads": [],
            "file_descriptors": [],
            "errors": [],
            "operations": 0,
            "degradation_events": [],
        }
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
        self.initial_threads = threading.active_count()
        self.initial_fds = len(self.process.open_files())

    def checkpoint(self):
        """Record current system metrics"""
        current_memory = self.process.memory_info().rss
        memory_growth = (current_memory - self.initial_memory) / (1024 * 1024)  # MB

        self.metrics["memory"].append(
            {
                "time": time.time() - self.start_time,
                "rss_mb": current_memory / (1024 * 1024),
                "growth_mb": memory_growth,
                "percent": self.process.memory_percent(),
            }
        )

        self.metrics["cpu"].append(
            {
                "time": time.time() - self.start_time,
                "percent": self.process.cpu_percent(interval=0.1),
            }
        )

        self.metrics["threads"].append(
            {
                "time": time.time() - self.start_time,
                "count": threading.active_count(),
                "growth": threading.active_count() - self.initial_threads,
            }
        )

        try:
            fd_count = len(self.process.open_files())
            self.metrics["file_descriptors"].append(
                {
                    "time": time.time() - self.start_time,
                    "count": fd_count,
                    "growth": fd_count - self.initial_fds,
                }
            )
        except:
            pass

        self.metrics["operations"] += 1

        # Check for degradation
        if memory_growth > 100:  # More than 100MB growth
            self.metrics["degradation_events"].append(
                {
                    "type": "memory_leak",
                    "time": time.time() - self.start_time,
                    "value": memory_growth,
                }
            )

        if threading.active_count() - self.initial_threads > 50:
            self.metrics["degradation_events"].append(
                {
                    "type": "thread_leak",
                    "time": time.time() - self.start_time,
                    "value": threading.active_count(),
                }
            )

    def report(self) -> Dict[str, Any]:
        """Generate endurance report"""
        runtime = time.time() - self.start_time

        return {
            "runtime_hours": runtime / 3600,
            "total_operations": self.metrics["operations"],
            "ops_per_second": (
                self.metrics["operations"] / runtime if runtime > 0 else 0
            ),
            "memory_growth_mb": (self.process.memory_info().rss - self.initial_memory)
            / (1024 * 1024),
            "thread_growth": threading.active_count() - self.initial_threads,
            "degradation_events": len(self.metrics["degradation_events"]),
            "errors": len(self.metrics["errors"]),
            "final_metrics": {
                "memory_mb": self.process.memory_info().rss / (1024 * 1024),
                "threads": threading.active_count(),
                "cpu_percent": self.process.cpu_percent(),
            },
        }


class TestEndurance24Hour:
    """
    24-hour endurance tests
    Run with: ENDURANCE_HOURS=24 pytest tests/paranoid/test_endurance_24hour.py -v
    For quick test: ENDURANCE_HOURS=0.1 pytest tests/paranoid/test_endurance_24hour.py -v
    """

    @classmethod
    def setup_class(cls):
        cls.validator = SecurityValidator()
        cls.unicode_handler = UnicodeNormalizer()
        cls.globalid_gen = GlobalIDGenerator()
        try:
            cls.region_manager = RegionManager(Path("./config"))
        except:
            cls.region_manager = None

        # Get test duration from environment
        cls.test_hours = float(
            os.environ.get("ENDURANCE_HOURS", "0.1")
        )  # Default 6 minutes for quick test
        cls.test_seconds = cls.test_hours * 3600

    @pytest.mark.timeout(15)
    def test_validator_memory_leak_24h(self):
        """Test validator for memory leaks over 24 hours"""
        monitor = EnduranceMonitor()
        end_time = time.time() + self.test_seconds

        test_strings = [
            "Normal string",
            "String with émojis 😀",
            "Very " * 100 + "long string",
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "\x00\x01\x02\x03",
            "混合 Unicode 测试",
            "مرحبا بالعالم",
            "שלום עולם",
        ]

        iteration = 0
        while time.time() < end_time:
            try:
                # Cycle through test strings
                test_str = test_strings[iteration % len(test_strings)]

                # Add some randomization
                if random.random() < 0.1:
                    test_str = "".join(
                        random.choices(string.printable, k=random.randint(1, 1000))
                    )

                # Validate string
                self.validator.validate_string(
                    test_str, f"endurance_{iteration}"
                )

                # Every 1000 iterations, checkpoint
                if iteration % 1000 == 0:
                    monitor.checkpoint()
                    gc.collect()  # Force garbage collection

                    # Check for excessive memory growth
                    current_memory = monitor.process.memory_info().rss
                    memory_growth_mb = (current_memory - monitor.initial_memory) / (
                        1024 * 1024
                    )

                    if memory_growth_mb > 500:  # Alert if > 500MB growth
                        print(
                            f"WARNING: Memory growth detected: {memory_growth_mb:.2f}MB"
                        )

                iteration += 1

            except Exception as e:
                monitor.metrics["errors"].append(
                    {
                        "time": time.time() - monitor.start_time,
                        "error": str(e),
                        "iteration": iteration,
                    }
                )

        report = monitor.report()
        print("\nEndurance Report:")
        print(f"  Runtime: {report['runtime_hours']:.2f} hours")
        print(f"  Operations: {report['total_operations']:,}")
        print(f"  Ops/sec: {report['ops_per_second']:.2f}")
        print(f"  Memory growth: {report['memory_growth_mb']:.2f}MB")
        print(f"  Thread growth: {report['thread_growth']}")
        print(f"  Errors: {report['errors']}")
        print(f"  Degradation events: {report['degradation_events']}")

        # Assert no major leaks
        assert (
            report["memory_growth_mb"] < 1000
        ), f"Excessive memory growth: {report['memory_growth_mb']}MB"
        assert (
            report["thread_growth"] < 100
        ), f"Thread leak detected: {report['thread_growth']} new threads"
        assert (
            report["degradation_events"] < 10
        ), f"Too many degradation events: {report['degradation_events']}"

    @pytest.mark.timeout(15)
    def test_concurrent_load_24h(self):
        """Test system under concurrent load for 24 hours"""
        monitor = EnduranceMonitor()
        end_time = time.time() + self.test_seconds

        def worker_thread(thread_id: int):
            """Worker thread that continuously processes data"""
            local_validator = SecurityValidator()
            operations = 0

            while time.time() < end_time:
                try:
                    # Generate random workload
                    if random.random() < 0.7:
                        # Normal operation
                        text = f"Thread-{thread_id}-Op-{operations}"
                        local_validator.validate_string(text, "concurrent")
                    elif random.random() < 0.9:
                        # Heavy operation
                        text = "X" * random.randint(100, 1000)
                        local_validator.validate_string(text, "heavy")
                    else:
                        # Attack simulation
                        attack = random.choice(
                            [
                                "' OR '1'='1",
                                "<script>alert(1)</script>",
                                "../../../etc/passwd",
                                "\x00\x01\x02",
                            ]
                        )
                        try:
                            local_validator.validate_string(attack, "attack")
                        except:
                            pass  # Expected to fail

                    operations += 1

                    # Occasional sleep to simulate real workload
                    if random.random() < 0.01:
                        time.sleep(random.uniform(0.01, 0.1))

                except Exception:
                    pass  # Log but continue

            return operations

        # Start worker threads
        num_threads = 10
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(num_threads)]

            # Monitor while threads run
            check_interval = 60  # Check every minute
            next_check = time.time() + check_interval

            while time.time() < end_time:
                if time.time() >= next_check:
                    monitor.checkpoint()
                    next_check = time.time() + check_interval

                    # Print progress
                    elapsed = time.time() - monitor.start_time
                    remaining = end_time - time.time()
                    print(
                        f"Progress: {elapsed/3600:.1f}h elapsed, {remaining/3600:.1f}h remaining"
                    )

                time.sleep(1)

            # Wait for threads to complete
            total_operations = sum(f.result() for f in futures)

        report = monitor.report()
        report["total_thread_operations"] = total_operations

        print("\nConcurrent Load Report:")
        print(f"  Runtime: {report['runtime_hours']:.2f} hours")
        print(f"  Total operations: {total_operations:,}")
        print(
            f"  Ops/sec/thread: {total_operations / (num_threads * self.test_seconds):.2f}"
        )
        print(f"  Memory growth: {report['memory_growth_mb']:.2f}MB")
        print(f"  Thread stability: {report['thread_growth']} unexpected threads")

        # Assertions
        assert (
            report["memory_growth_mb"] < 2000
        ), f"Memory leak under load: {report['memory_growth_mb']}MB"
        assert (
            report["thread_growth"] < 20
        ), f"Thread leak: {report['thread_growth']} extra threads"

    @pytest.mark.timeout(15)
    def test_resource_exhaustion_24h(self):
        """Test system behavior when resources are exhausted"""
        monitor = EnduranceMonitor()
        end_time = time.time() + self.test_seconds

        # Track resource exhaustion attempts
        exhaustion_tests = {"memory": 0, "threads": 0, "file_descriptors": 0, "cpu": 0}

        while time.time() < end_time:
            test_type = random.choice(["memory", "threads", "file_descriptors", "cpu"])

            try:
                if test_type == "memory":
                    # Try to allocate large amounts of memory
                    big_strings = []
                    for _ in range(100):
                        big_strings.append("X" * (1024 * 1024))  # 1MB strings
                        self.validator.validate_string(
                            big_strings[-1][:100], "memory_test"
                        )
                    del big_strings
                    gc.collect()

                elif test_type == "threads":
                    # Spawn many threads
                    threads = []
                    for i in range(50):
                        t = threading.Thread(
                            target=lambda: self.validator.validate_string(
                                f"thread-{i}", "thread"
                            )
                        )
                        t.start()
                        threads.append(t)
                    for t in threads:
                        t.join(timeout=0.1)

                elif test_type == "file_descriptors":
                    # Open many files (simulated)
                    temp_files = []
                    for i in range(10):
                        try:
                            f = open(f"/tmp/endurance_test_{i}.tmp", "w")
                            temp_files.append(f)
                            f.write("test")
                        except:
                            break
                    for f in temp_files:
                        f.close()

                elif test_type == "cpu":
                    # CPU intensive operations
                    for _ in range(1000):
                        text = "".join(random.choices(string.ascii_letters, k=100))
                        self.validator.validate_string(text, "cpu_test")

                exhaustion_tests[test_type] += 1

                # Checkpoint every 100 tests
                if sum(exhaustion_tests.values()) % 100 == 0:
                    monitor.checkpoint()

            except Exception as e:
                monitor.metrics["errors"].append(
                    {"test_type": test_type, "error": str(e)}
                )

            # Small delay to prevent tight loop
            time.sleep(0.01)

        report = monitor.report()
        print("\nResource Exhaustion Report:")
        print(f"  Runtime: {report['runtime_hours']:.2f} hours")
        print(f"  Exhaustion attempts: {exhaustion_tests}")
        print(f"  Errors handled: {len(monitor.metrics['errors'])}")
        print(f"  System remained stable: {report['degradation_events'] < 20}")

        # System should handle resource exhaustion gracefully
        assert (
            report["degradation_events"] < 50
        ), "System unstable under resource pressure"

    @pytest.mark.timeout(15)
    def test_cache_overflow_24h(self):
        """Test cache behavior over 24 hours with many unique entries"""
        monitor = EnduranceMonitor()
        end_time = time.time() + self.test_seconds

        unique_count = 0
        cache_hits = 0
        cache_misses = 0

        while time.time() < end_time:
            # Generate unique or repeated strings
            if random.random() < 0.8:
                # New unique string
                text = f"unique_{unique_count}_{random.random()}"
                unique_count += 1
                cache_misses += 1
            else:
                # Repeat previous string (cache hit)
                text = f"unique_{random.randint(0, max(0, unique_count-1))}_{random.random()}"
                cache_hits += 1

            try:
                self.validator.validate_string(text, "cache_test")

                # Force cache pressure with large strings occasionally
                if random.random() < 0.05:
                    big_text = "BIG" * 10000 + str(unique_count)
                    self.validator.validate_string(big_text[:1000], "cache_pressure")

                # Checkpoint periodically
                if unique_count % 1000 == 0:
                    monitor.checkpoint()
                    gc.collect()

            except Exception as e:
                monitor.metrics["errors"].append(str(e))

        report = monitor.report()
        print("\nCache Overflow Report:")
        print(f"  Runtime: {report['runtime_hours']:.2f} hours")
        print(f"  Unique entries: {unique_count:,}")
        print(f"  Cache hits (simulated): {cache_hits:,}")
        print(f"  Cache misses: {cache_misses:,}")
        print(f"  Memory growth: {report['memory_growth_mb']:.2f}MB")

        # Cache should not cause unbounded memory growth
        memory_per_entry = (
            report["memory_growth_mb"] / max(1, unique_count) * 1000
        )  # KB per entry
        assert (
            memory_per_entry < 10
        ), f"Excessive memory per cache entry: {memory_per_entry:.2f}KB"

    @pytest.mark.timeout(15)
    def test_log_file_growth_24h(self):
        """Monitor log file growth over 24 hours"""
        monitor = EnduranceMonitor()
        end_time = time.time() + self.test_seconds

        # Track log-worthy events
        log_events = {"info": 0, "warning": 0, "error": 0, "security": 0}

        while time.time() < end_time:
            event_type = random.choices(
                ["info", "warning", "error", "security"],
                weights=[70, 20, 8, 2],  # Realistic distribution
                k=1,
            )[0]

            try:
                if event_type == "info":
                    # Normal operation
                    self.validator.validate_string(f"info_{log_events['info']}", "info")

                elif event_type == "warning":
                    # Suspicious but valid
                    self.validator.validate_string("admin' --", "warning")

                elif event_type == "error":
                    # Invalid input
                    try:
                        self.validator.validate_string("\x00\x01\x02", "error")
                    except:
                        pass  # Expected

                elif event_type == "security":
                    # Security event
                    try:
                        self.validator.validate_string(
                            "'; DROP TABLE users; --", "security"
                        )
                    except:
                        pass  # Expected

                log_events[event_type] += 1

                # Checkpoint periodically
                if sum(log_events.values()) % 10000 == 0:
                    monitor.checkpoint()

            except Exception:
                pass

        report = monitor.report()
        print("\nLog Growth Report:")
        print(f"  Runtime: {report['runtime_hours']:.2f} hours")
        print(f"  Log events: {log_events}")
        print(f"  Total events: {sum(log_events.values()):,}")
        print(f"  Events/sec: {sum(log_events.values()) / self.test_seconds:.2f}")

        # Verify logging doesn't cause issues
        assert (
            report["memory_growth_mb"] < 1000
        ), f"Possible log memory leak: {report['memory_growth_mb']}MB"

    @pytest.mark.timeout(15)
    def test_degradation_pattern_24h(self):
        """Test for performance degradation patterns over time"""
        monitor = EnduranceMonitor()
        end_time = time.time() + self.test_seconds

        # Track performance over time
        performance_buckets = []
        bucket_size = self.test_seconds / 100  # 100 buckets
        current_bucket = []
        next_bucket_time = time.time() + bucket_size

        while time.time() < end_time:
            start = time.time()

            # Perform standard operation
            self.validator.validate_string("performance_test_string", "perf")

            operation_time = time.time() - start
            current_bucket.append(operation_time)

            # Check if we should move to next bucket
            if time.time() >= next_bucket_time:
                if current_bucket:
                    avg_time = sum(current_bucket) / len(current_bucket)
                    performance_buckets.append(
                        {
                            "time": time.time() - monitor.start_time,
                            "avg_ms": avg_time * 1000,
                            "operations": len(current_bucket),
                        }
                    )
                current_bucket = []
                next_bucket_time = time.time() + bucket_size
                monitor.checkpoint()

        # Analyze degradation
        if len(performance_buckets) > 10:
            first_10_avg = sum(b["avg_ms"] for b in performance_buckets[:10]) / 10
            last_10_avg = sum(b["avg_ms"] for b in performance_buckets[-10:]) / 10
            degradation_percent = ((last_10_avg - first_10_avg) / first_10_avg) * 100

            print("\nPerformance Degradation Report:")
            print(f"  Runtime: {monitor.report()['runtime_hours']:.2f} hours")
            print(f"  Initial performance: {first_10_avg:.3f}ms")
            print(f"  Final performance: {last_10_avg:.3f}ms")
            print(f"  Degradation: {degradation_percent:.1f}%")

            # Performance should not degrade more than 50%
            assert (
                degradation_percent < 50
            ), f"Excessive performance degradation: {degradation_percent:.1f}%"

    @pytest.mark.timeout(15)
    def test_recovery_after_stress_24h(self):
        """Test system recovery after stress periods during 24h run"""
        monitor = EnduranceMonitor()
        end_time = time.time() + self.test_seconds

        stress_periods = []
        recovery_times = []

        while time.time() < end_time:
            # Normal operation for a while
            normal_duration = min(
                60, (end_time - time.time()) / 4
            )  # 1 minute or remaining/4
            normal_end = time.time() + normal_duration

            baseline_times = []
            while time.time() < normal_end:
                start = time.time()
                self.validator.validate_string("normal_operation", "normal")
                baseline_times.append(time.time() - start)
                time.sleep(0.01)

            if baseline_times:
                baseline_avg = sum(baseline_times) / len(baseline_times)
            else:
                baseline_avg = 0.001

            # Stress period
            stress_duration = min(
                10, (end_time - time.time()) / 2
            )  # 10 seconds or remaining/2
            time.time() + stress_duration
            stress_start = time.time()

            # Apply stress
            stress_threads = []
            for i in range(20):
                t = threading.Thread(
                    target=lambda: [
                        self.validator.validate_string("X" * 1000, "stress")
                        for _ in range(100)
                    ]
                )
                t.start()
                stress_threads.append(t)

            # Wait for stress to complete
            for t in stress_threads:
                t.join(timeout=stress_duration)

            stress_periods.append(
                {
                    "duration": time.time() - stress_start,
                    "time": stress_start - monitor.start_time,
                }
            )

            # Measure recovery
            recovery_start = time.time()
            recovered = False
            recovery_measurements = []

            while time.time() < min(
                recovery_start + 60, end_time
            ):  # Max 1 minute recovery
                start = time.time()
                self.validator.validate_string("recovery_test", "recovery")
                operation_time = time.time() - start
                recovery_measurements.append(operation_time)

                # Check if recovered (within 150% of baseline)
                if operation_time <= baseline_avg * 1.5:
                    recovered = True
                    recovery_time = time.time() - recovery_start
                    recovery_times.append(recovery_time)
                    break

                time.sleep(0.1)

            if not recovered and recovery_measurements:
                recovery_times.append(60)  # Max recovery time

            monitor.checkpoint()

        report = monitor.report()
        avg_recovery = (
            sum(recovery_times) / len(recovery_times) if recovery_times else 0
        )

        print("\nStress Recovery Report:")
        print(f"  Runtime: {report['runtime_hours']:.2f} hours")
        print(f"  Stress periods: {len(stress_periods)}")
        print(f"  Average recovery time: {avg_recovery:.2f} seconds")
        print(
            f"  Max recovery time: {max(recovery_times) if recovery_times else 0:.2f} seconds"
        )

        # System should recover quickly
        assert (
            avg_recovery < 30
        ), f"Slow recovery from stress: {avg_recovery:.2f}s average"


def run_endurance_suite():
    """Run the full 24-hour endurance suite"""
    import pytest

    # Set environment for full 24-hour run
    if "ENDURANCE_HOURS" not in os.environ:
        print("Setting ENDURANCE_HOURS=24 for full endurance test")
        print("Use ENDURANCE_HOURS=0.1 for quick 6-minute test")
        os.environ["ENDURANCE_HOURS"] = "24"

    print(f"Starting {os.environ['ENDURANCE_HOURS']} hour endurance test...")
    print("This will test for:")
    print("- Memory leaks")
    print("- Thread leaks")
    print("- Resource exhaustion")
    print("- Performance degradation")
    print("- Cache overflow")
    print("- Log growth issues")
    print("- Recovery after stress")

    pytest.main([__file__, "-v", "--tb=short", "-s"])


if __name__ == "__main__":
    run_endurance_suite()
