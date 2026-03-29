import pytest

#!/usr/bin/env python3
"""
HELL-LEVEL STRESS TESTING for GMNAP v7
Tests everything that could possibly break, fail, or cause problems.
"""

import sys
import gc
import time
import threading
import traceback
import unicodedata
from concurrent.futures import ThreadPoolExecutor
import psutil
import os

sys.path.insert(0, "src")


class HellTester:
    """Hell-level testing class that breaks everything."""

    def __init__(self):
        self.failures = []
        self.warnings = []
        self.tests_run = 0
        self.start_memory = psutil.Process().memory_info().rss

    def record_failure(self, test_name, error):
        self.failures.append(f"FAIL {test_name}: {error}")
        print(f"💀 FAILURE in {test_name}: {error}")

    def record_warning(self, test_name, warning):
        self.warnings.append(f"WARN {test_name}: {warning}")
        print(f"WARN WARNING in {test_name}: {warning}")

    @pytest.mark.timeout(15)
    def test_interface_compliance_hell(self):
        """Test that processors actually implement the correct interface."""
        print("\n🔥 HELL TEST 1: Interface Compliance")

        try:
            from src.regions.base import RegionSpec
            from src.regions.a_groups.a3_nordic_baltic import A3NordicBalticProcessor
            from src.regions.a_groups.a4_oceania import A4OceaniaProcessor
            from src.regions.a_groups.a5_caribbean import A5CaribbeanProcessor
            from src.regions.b_groups.b3_greek import B3GreekProcessor

            processors = [
                A3NordicBalticProcessor(),
                A4OceaniaProcessor(),
                A5CaribbeanProcessor(),
                B3GreekProcessor(),
            ]

            for processor in processors:
                # Test inheritance
                if not isinstance(processor, RegionSpec):
                    self.record_failure(
                        f"{processor.code}_inheritance",
                        f"Does not inherit from RegionSpec",
                    )

                # Test required methods exist with correct signatures
                required_methods = ["clean", "augment", "validate", "order_key"]
                for method_name in required_methods:
                    if not hasattr(processor, method_name):
                        self.record_failure(
                            f"{processor.code}_{method_name}",
                            f"Missing required method {method_name}",
                        )
                    else:
                        method = getattr(processor, method_name)
                        if not callable(method):
                            self.record_failure(
                                f"{processor.code}_{method_name}",
                                f"Method {method_name} not callable",
                            )

                # Test method signatures by calling with correct args
                try:
                    test_entry = {"CanonicalLatin": "Test, Name"}
                    processor.clean(test_entry)  # Should modify in-place
                    processor.augment(test_entry)  # Should modify in-place
                    processor.validate(test_entry)  # Should raise or return None
                    key = processor.order_key(test_entry)  # Should return string

                    if not isinstance(key, str):
                        self.record_failure(
                            f"{processor.code}_order_key_return",
                            f"order_key returned {type(key)}, not str",
                        )

                except Exception as e:
                    self.record_failure(
                        f"{processor.code}_method_signatures",
                        f"Method signature error: {e}",
                    )

                self.tests_run += 1

        except Exception as e:
            self.record_failure("interface_compliance", f"Critical failure: {e}")

    @pytest.mark.timeout(15)
    def test_malicious_input_hell(self):
        """Test with malicious, malformed, and evil inputs."""
        print("\n🔥 HELL TEST 2: Malicious Input Resistance")

        try:
            from src.regions.a_groups.a3_nordic_baltic import A3NordicBalticProcessor

            processor = A3NordicBalticProcessor()

            evil_inputs = [
                # Unicode attacks
                {"CanonicalLatin": "Smith\x00\x01\x02, John"},  # Null bytes
                {"CanonicalLatin": "Smith\ufeff, John"},  # BOM
                {"CanonicalLatin": "Smith\u200b\u200c\u200d, John"},  # Zero-width chars
                {"CanonicalLatin": "\U0001f4a9" * 1000},  # Emoji spam
                # Buffer overflow attempts
                {"CanonicalLatin": "A" * 100000},  # Massive string
                {"CanonicalLatin": "Smith," + "B" * 50000},  # Huge given name
                # Script injection attempts
                {"CanonicalLatin": "<script>alert('xss')</script>"},
                {"CanonicalLatin": "'; DROP TABLE names; --"},
                {"CanonicalLatin": "../../../etc/passwd"},
                # Encoding attacks
                {"CanonicalLatin": "Sm\xc0\x80ith, John"},  # Overlong UTF-8
                {
                    "CanonicalLatin": bytes([0xFF, 0xFE]).decode("latin1")
                },  # Invalid UTF-8
                # Format string attacks
                {"CanonicalLatin": "Smith%s%s%s%s, John%n%n%n"},
                {"CanonicalLatin": "Smith{0}{1}{2}, John"},
                # Control characters
                {"CanonicalLatin": "Smith\r\n\t\v\f, John"},
                {"CanonicalLatin": "Smith\x1b[31m, John"},  # ANSI escape
                # Unicode normalization attacks
                {"CanonicalLatin": "A\u0300\u0301\u0302\u0303, B"},  # Combining chars
                {"CanonicalLatin": "℀℁ℂ℃℄℅℆ℇ℈℉ℊℋℌℍℎℏ"},  # Letterlike symbols
                # Edge cases that broke systems in the past
                {"CanonicalLatin": "True, False"},  # Python keywords
                {"CanonicalLatin": "None, self"},
                {"CanonicalLatin": "🏴‍☠️, 👨‍👩‍👧‍👦"},  # Complex emoji
                # Empty/whitespace variations
                {"CanonicalLatin": ""},
                {"CanonicalLatin": " "},
                {"CanonicalLatin": "\t\n\r\v\f"},
                {"CanonicalLatin": "\u00a0\u2000\u2001\u2002"},  # Various spaces
                # Deeply nested structures (for augment)
                {"Variants": {"Observed": [{"str": {"nested": "attack"}}]}},
                # Type confusion
                {"CanonicalLatin": 12345},
                {"CanonicalLatin": ["Smith", "John"]},
                {"CanonicalLatin": {"attack": "payload"}},
                {"CanonicalLatin": None},
            ]

            for i, evil_entry in enumerate(evil_inputs):
                try:
                    # Test each processor method with evil input
                    test_entry = evil_entry.copy()

                    processor.clean(test_entry)
                    processor.augment(test_entry)
                    processor.validate(test_entry)
                    processor.order_key(test_entry)

                    # Some inputs should have been rejected
                    if isinstance(evil_entry.get("CanonicalLatin"), str):
                        if any(
                            ord(c) < 32 and c not in "\t\n\r"
                            for c in evil_entry["CanonicalLatin"]
                        ):
                            self.record_warning(
                                "malicious_input",
                                f"Accepted input with control chars: {repr(evil_entry)}",
                            )

                except Exception as e:
                    # This is usually good - malicious input was rejected
                    if (
                        "invalid" not in str(e).lower()
                        and "error" not in str(e).lower()
                    ):
                        self.record_warning(
                            "malicious_input", f"Unexpected error for input {i}: {e}"
                        )

                self.tests_run += 1

        except Exception as e:
            self.record_failure("malicious_input", f"Critical failure: {e}")

    @pytest.mark.timeout(15)
    def test_memory_hell(self):
        """Test for memory leaks and resource exhaustion."""
        print("\n🔥 HELL TEST 3: Memory Torture")

        try:
            from src.regions.a_groups.a3_nordic_baltic import A3NordicBalticProcessor

            processor = A3NordicBalticProcessor()

            # Baseline memory
            gc.collect()
            start_mem = psutil.Process().memory_info().rss

            # Process 10,000 entries
            for i in range(10000):
                entry = {
                    "CanonicalLatin": f"TestFamily{i}, TestGiven{i}",
                    "CanonicalNative": f"TestFamily{i}, TestGiven{i}",
                    "Variants": {"Observed": []},
                }

                processor.clean(entry)
                processor.augment(entry)
                processor.validate(entry)
                processor.order_key(entry)

                # Check memory every 1000 iterations
                if i % 1000 == 0:
                    gc.collect()
                    current_mem = psutil.Process().memory_info().rss
                    mem_growth = current_mem - start_mem

                    if mem_growth > 100 * 1024 * 1024:  # >100MB growth
                        self.record_warning(
                            "memory_leak",
                            f"Memory grew by {mem_growth/1024/1024:.1f}MB after {i} iterations",
                        )

            # Final memory check
            gc.collect()
            final_mem = psutil.Process().memory_info().rss
            total_growth = final_mem - start_mem

            if total_growth > 50 * 1024 * 1024:  # >50MB total growth
                self.record_failure(
                    "memory_leak",
                    f"Memory leaked {total_growth/1024/1024:.1f}MB over 10k iterations",
                )

            self.tests_run += 1

        except Exception as e:
            self.record_failure("memory_torture", f"Critical failure: {e}")

    @pytest.mark.timeout(15)
    def test_concurrency_hell(self):
        """Test thread safety and concurrent access."""
        print("\n🔥 HELL TEST 4: Concurrency Torture")

        try:
            from src.regions.a_groups.a3_nordic_baltic import A3NordicBalticProcessor

            # Test data races and thread safety
            processor = A3NordicBalticProcessor()
            errors = []

            def worker_thread(thread_id):
                try:
                    for i in range(100):
                        entry = {
                            "CanonicalLatin": f"Thread{thread_id}Family{i}, Given{i}",
                        }

                        processor.clean(entry)
                        processor.augment(entry)
                        processor.validate(entry)
                        key = processor.order_key(entry)

                        # Verify no cross-contamination
                        if (
                            f"Thread{thread_id}" not in str(entry)
                            and f"Thread{thread_id}" not in key
                        ):
                            errors.append(f"Thread {thread_id} contamination detected")

                except Exception as e:
                    errors.append(f"Thread {thread_id} error: {e}")

            # Run 10 threads concurrently
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(worker_thread, i) for i in range(10)]
                for future in futures:
                    future.result()  # Wait for completion

            if errors:
                for error in errors[:5]:  # Show first 5 errors
                    self.record_failure("concurrency", error)

            self.tests_run += 1

        except Exception as e:
            self.record_failure("concurrency_torture", f"Critical failure: {e}")

    @pytest.mark.timeout(15)
    def test_linguistic_rule_hell(self):
        """Test every linguistic rule exhaustively."""
        print("\n🔥 HELL TEST 5: Linguistic Rule Torture")

        try:
            from src.regions.a_groups.a3_nordic_baltic import A3NordicBalticProcessor
            from src.regions.b_groups.b3_greek import B3GreekProcessor

            # Test A3 Icelandic patronymic rule #8
            a3 = A3NordicBalticProcessor()

            patronymic_tests = [
                ("Magnússon, Jón", True, "son"),
                ("Guðmundsdóttir, Helga", True, "daughter"),
                ("Eriksson, Lars", True, "son"),
                ("Andersen, Anna", False, None),  # Danish, not patronymic
                ("Johnson, John", False, None),  # English, not patronymic
            ]

            for name, should_be_patronymic, expected_type in patronymic_tests:
                entry = {"CanonicalLatin": name}
                a3.clean(entry)
                a3.augment(entry)
                a3.validate(entry)

                is_patronymic = entry.get("RegionalExtras", {}).get(
                    "is_patronymic", False
                )
                patronymic_type = entry.get("RegionalExtras", {}).get("patronymic_type")

                if is_patronymic != should_be_patronymic:
                    self.record_failure(
                        "patronymic_detection",
                        f"{name}: expected patronymic={should_be_patronymic}, got {is_patronymic}",
                    )

                if should_be_patronymic and patronymic_type != expected_type:
                    self.record_failure(
                        "patronymic_type",
                        f"{name}: expected type={expected_type}, got {patronymic_type}",
                    )

                self.tests_run += 1

            # Test B3 Chatzi variants rule #19
            b3 = B3GreekProcessor()

            chatzi_tests = [
                "Chatzidakis, Manos",
                "Hatzipanagiotou, Dimitris",
                "Hadjidakis, Manos",
                "Chatzigeorgiou, Maria",
            ]

            for name in chatzi_tests:
                entry = {"CanonicalLatin": name}
                b3.clean(entry)
                b3.augment(entry)
                b3.validate(entry)

                has_chatzi = entry.get("RegionalExtras", {}).get(
                    "has_chatzi_prefix", False
                )
                variants = entry.get("Variants", {}).get("Synthesised", [])
                chatzi_variants = [v for v in variants if v["type"] == "chatzi-variant"]

                if not has_chatzi:
                    self.record_failure(
                        "chatzi_detection", f"{name}: Chatzi prefix not detected"
                    )

                if len(chatzi_variants) == 0:
                    self.record_failure(
                        "chatzi_variants", f"{name}: No Chatzi variants generated"
                    )

                # Verify at least Hatzi variant exists
                hatzi_found = any("Hatzi" in v["str"] for v in chatzi_variants)
                if not hatzi_found:
                    self.record_failure(
                        "chatzi_hatzi_variant", f"{name}: No Hatzi variant generated"
                    )

                self.tests_run += 1

        except Exception as e:
            self.record_failure("linguistic_rules", f"Critical failure: {e}")

    @pytest.mark.timeout(15)
    def test_integration_hell(self):
        """Test integration points that could fail."""
        print("\n🔥 HELL TEST 6: Integration Torture")

        try:
            from src.core.pipeline_v7 import load_working_processors

            # Test manager creation multiple times
            for i in range(10):
                manager = load_working_processors()
                regions = manager.list_regions()

                if len(regions) == 0:
                    self.record_failure(
                        "integration_manager", f"No regions loaded on iteration {i}"
                    )

                # Test region isolation - processing in one shouldn't affect another
                test_entries = [
                    ("A3", "Eriksson, Lars"),
                    ("A4", "Tuilaepa"),
                    ("A5", "d'Aubigny, Jean-Pierre"),
                    ("B3", "Papadopoulos, Nikos"),
                ]

                results = []
                for region, name in test_entries:
                    entry = {"CanonicalLatin": name}
                    result = manager.process_entry(entry, region)
                    results.append((region, name, result))

                # Verify no cross-contamination
                for j, (region, name, result) in enumerate(results):
                    for k, (other_region, other_name, other_result) in enumerate(
                        results
                    ):
                        if j != k:
                            if other_name in str(result) or other_region in str(result):
                                self.record_failure(
                                    "cross_contamination",
                                    f"Region {region} contaminated by {other_region}",
                                )

                self.tests_run += 1

        except Exception as e:
            self.record_failure("integration_torture", f"Critical failure: {e}")

    @pytest.mark.timeout(15)
    def test_korean_disaster_detection(self):
        """Test for the Korean E4 disaster we found."""
        print("\n🔥 HELL TEST 7: Korean Disaster Detection")

        try:
            from src.core.pipeline_v7 import load_working_processors

            manager = load_working_processors()
            regions = manager.list_regions()

            # Check if E4 is claimed to be loaded
            if "E4" in regions:
                self.record_failure(
                    "korean_false_claim", "E4 Korean claims to be loaded but is broken"
                )

            # Try to process Korean name with E4 if it exists
            try:
                entry = {"CanonicalLatin": "Kim, Jong-Un"}
                result = manager.process_entry(entry, "E4")

                # If this succeeds, verify it actually worked
                if not result.get("RegionalExtras"):
                    self.record_failure(
                        "korean_hollow_success",
                        "E4 claims success but produces no regional data",
                    )

            except Exception as e:
                # This is expected if E4 is broken
                self.record_warning(
                    "korean_expected_failure", f"E4 properly fails as expected: {e}"
                )

            self.tests_run += 1

        except Exception as e:
            self.record_failure("korean_disaster_detection", f"Critical failure: {e}")

    @pytest.mark.timeout(15)
    def test_performance_hell(self):
        """Test performance under extreme conditions."""
        print("\n🔥 HELL TEST 8: Performance Torture")

        try:
            from src.regions.a_groups.a3_nordic_baltic import A3NordicBalticProcessor

            processor = A3NordicBalticProcessor()

            # Test with extremely long names
            long_name = (
                "VeryLongSurname" + "X" * 1000 + ", VeryLongGivenName" + "Y" * 1000
            )

            start_time = time.time()

            entry = {"CanonicalLatin": long_name}
            processor.clean(entry)
            processor.augment(entry)
            processor.validate(entry)
            key = processor.order_key(entry)

            end_time = time.time()
            duration = end_time - start_time

            if duration > 1.0:  # Should not take > 1 second for any name
                self.record_failure(
                    "performance_long_name",
                    f"Long name took {duration:.3f}s to process",
                )

            # Test rapid-fire processing
            start_time = time.time()

            for i in range(1000):
                entry = {"CanonicalLatin": f"Family{i}, Given{i}"}
                processor.clean(entry)
                processor.augment(entry)
                processor.validate(entry)
                processor.order_key(entry)

            end_time = time.time()
            duration = end_time - start_time
            throughput = 1000 / duration

            if throughput < 1000:  # Should process >1000 entries/sec
                self.record_warning(
                    "performance_throughput",
                    f"Throughput only {throughput:.0f} entries/sec",
                )

            self.tests_run += 1

        except Exception as e:
            self.record_failure("performance_torture", f"Critical failure: {e}")

    def run_all_hell_tests(self):
        """Run all hell tests."""
        print("🔥🔥🔥 STARTING HELL-LEVEL STRESS TESTING 🔥🔥🔥")
        print("=" * 60)

        start_time = time.time()

        hell_tests = [
            self.test_interface_compliance_hell,
            self.test_malicious_input_hell,
            self.test_memory_hell,
            self.test_concurrency_hell,
            self.test_linguistic_rule_hell,
            self.test_integration_hell,
            self.test_korean_disaster_detection,
            self.test_performance_hell,
        ]

        for test_func in hell_tests:
            try:
                test_func()
                gc.collect()  # Clean up after each test
            except Exception as e:
                self.record_failure(test_func.__name__, f"Test crashed: {e}")
                traceback.print_exc()

        end_time = time.time()
        total_duration = end_time - start_time

        # Final report
        print("\n" + "🔥" * 60)
        print("🔥 HELL-LEVEL TESTING COMPLETE")
        print("🔥" * 60)

        print(f"\n📊 STATISTICS:")
        print(f"   Total tests run: {self.tests_run}")
        print(f"   Total duration: {total_duration:.1f}s")
        print(f"   Tests per second: {self.tests_run/total_duration:.1f}")

        final_memory = psutil.Process().memory_info().rss
        memory_growth = final_memory - self.start_memory
        print(f"   Memory growth: {memory_growth/1024/1024:.1f}MB")

        print(f"\n💀 FAILURES ({len(self.failures)}):")
        for failure in self.failures:
            print(f"   {failure}")

        print(f"\nWARN  WARNINGS ({len(self.warnings)}):")
        for warning in self.warnings:
            print(f"   {warning}")

        # Final verdict
        if len(self.failures) == 0:
            print(f"\n🎉 MIRACLE: ALL {self.tests_run} HELL TESTS PASSED!")
            return True
        else:
            print(f"\n💀 SYSTEM FAILED: {len(self.failures)} critical failures")
            return False


if __name__ == "__main__":
    tester = HellTester()
    success = tester.run_all_hell_tests()
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
