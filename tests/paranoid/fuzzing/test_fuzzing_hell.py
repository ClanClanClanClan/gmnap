"""
from typing import Dict
from typing import Any
HELL-LEVEL PARANOID FUZZING TESTING
===================================

This module contains comprehensive fuzzing tests that generate random inputs
to stress-test the GMNAP system. Uses property-based testing to find edge cases
that manual testing would miss.

WARNING: These tests generate massive amounts of random data and may take time.
"""

import gc
import random
import string
import sys
import time
import unicodedata
from pathlib import Path

import pytest

try:
    from hypothesis import Verbosity, given, settings
    from hypothesis import strategies as st
    from hypothesis.strategies import composite, integers, lists, text

    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False

    # Fallback decorators for when hypothesis is not available
    def given(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    class st:
        @staticmethod
        def text(*args, **kwargs):
            return None


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.regions.manager_optimized import RegionManager


class RandomInputGenerator:
    """Generate random inputs for fuzzing."""

    def __init__(self, seed=None):
        if seed:
            random.seed(seed)

    def random_unicode_string(self, min_length=1, max_length=100):
        """Generate random Unicode string."""
        length = random.randint(min_length, max_length)
        chars = []

        for _ in range(length):
            # Choose from different Unicode categories
            category = random.choice(
                [
                    "Latin",
                    "Cyrillic",
                    "Greek",
                    "Arabic",
                    "Hebrew",
                    "CJK",
                    "Hangul",
                    "Hiragana",
                    "Katakana",
                    "Punctuation",
                    "Control",
                    "Symbol",
                ]
            )

            if category == "Latin":
                chars.append(random.choice(string.ascii_letters))
            elif category == "Cyrillic":
                chars.append(chr(random.randint(0x0400, 0x04FF)))
            elif category == "Greek":
                chars.append(chr(random.randint(0x0370, 0x03FF)))
            elif category == "Arabic":
                chars.append(chr(random.randint(0x0600, 0x06FF)))
            elif category == "Hebrew":
                chars.append(chr(random.randint(0x0590, 0x05FF)))
            elif category == "CJK":
                chars.append(chr(random.randint(0x4E00, 0x9FFF)))
            elif category == "Hangul":
                chars.append(chr(random.randint(0xAC00, 0xD7AF)))
            elif category == "Hiragana":
                chars.append(chr(random.randint(0x3040, 0x309F)))
            elif category == "Katakana":
                chars.append(chr(random.randint(0x30A0, 0x30FF)))
            elif category == "Punctuation":
                chars.append(random.choice(".,;:!?-_()[]{}\"'/\\"))
            elif category == "Control":
                chars.append(chr(random.randint(0x00, 0x1F)))
            elif category == "Symbol":
                chars.append(random.choice("@#$%^&*+=<>|~`"))

        return "".join(chars)

    def random_name_like_string(self):
        """Generate string that looks name-like."""
        patterns = [
            # Standard patterns
            lambda: f"{self.random_surname()}, {self.random_given_name()}",
            lambda: f"{self.random_surname()} {self.random_given_name()}",
            lambda: f"{self.random_surname()}{self.random_given_name()}",
            # Malformed patterns
            lambda: f"{self.random_surname()}, , {self.random_given_name()}",
            lambda: f", {self.random_given_name()}",
            lambda: f"{self.random_surname()},",
            lambda: ",",
            # With numbers
            lambda: f"{self.random_surname()}{random.randint(1,999)}, {self.random_given_name()}",
            lambda: f"{self.random_surname()}, {self.random_given_name()}{random.randint(1,99)}",
            # With special characters
            lambda: f"{self.random_surname()}@{random.choice('gmail.com')}, {self.random_given_name()}",
            lambda: f"{self.random_surname()}#{random.randint(1,999)}, {self.random_given_name()}",
            # Mixed scripts
            lambda: f"{self.random_unicode_string(3, 8)}, {self.random_unicode_string(3, 8)}",
            # Very long
            lambda: f"{self.random_surname() * random.randint(5, 20)}, {self.random_given_name()}",
            # Very short
            lambda: f"{random.choice(string.ascii_letters)}, {random.choice(string.ascii_letters)}",
        ]

        pattern = random.choice(patterns)
        return pattern()

    def random_surname(self):
        """Generate random surname-like string."""
        bases = [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Jones",
            "García",
            "Rodríguez",
            "Martínez",
            "López",
            "González",
            "Kim",
            "Lee",
            "Park",
            "Choi",
            "Jung",
            "Wang",
            "Li",
            "Zhang",
            "Liu",
            "Chen",
            "Müller",
            "Schmidt",
            "Schneider",
            "Fischer",
            "Weber",
            "Al-Ahmad",
            "Al-Hassan",
            "Al-Mahmoud",
            "Al-Ali",
            "Ivanov",
            "Petrov",
            "Volkov",
            "Smirnov",
        ]

        base = random.choice(bases)

        # Add random modifications
        modifications = [
            lambda x: x,  # No change
            lambda x: x.upper(),
            lambda x: x.lower(),
            lambda x: x + str(random.randint(1, 999)),
            lambda x: x + random.choice("abcdefgh"),
            lambda x: x[:-1] if len(x) > 1 else x,  # Remove last char
            lambda x: x + x,  # Double
            lambda x: "".join(reversed(x)),  # Reverse
        ]

        return random.choice(modifications)(base)

    def random_given_name(self):
        """Generate random given name-like string."""
        bases = [
            "John",
            "Mary",
            "James",
            "Patricia",
            "Robert",
            "José",
            "María",
            "Juan",
            "Ana",
            "Carlos",
            "정은",
            "민수",
            "은영",
            "지훈",
            "수진",
            "Wei",
            "Ming",
            "Ling",
            "Jun",
            "Yan",
            "Hans",
            "Greta",
            "Klaus",
            "Ingrid",
            "Mohammed",
            "Ahmed",
            "Ali",
            "Fatima",
            "Vladimir",
            "Sergei",
            "Natasha",
            "Igor",
        ]

        base = random.choice(bases)

        # Add random modifications (similar to surname)
        modifications = [
            lambda x: x,
            lambda x: x.upper(),
            lambda x: x.lower(),
            lambda x: x + "-" + random.choice(["un", "ho", "su", "min"]),
            lambda x: x * 2,
        ]

        return random.choice(modifications)(base)


class TestFuzzingHell:
    """Hell-level fuzzing testing."""

    @pytest.fixture
    def region_manager(self):
        """Fresh region manager."""
        return RegionManager()

    @pytest.fixture
    def input_generator(self):
        """Input generator with fixed seed for reproducibility."""
        return RandomInputGenerator(seed=42)

    # ========== RANDOM INPUT FUZZING ==========

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_random_unicode_fuzzing(self, region_manager, input_generator):
        """Fuzz with completely random Unicode strings."""

        crash_count = 0
        timeout_count = 0
        valid_results = 0
        invalid_regions = []

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

        for i in range(1000):  # Generate 1000 random inputs
            # Generate random input
            random_input = input_generator.random_unicode_string(1, 200)
            entry = {"CanonicalLatin": random_input}

            start_time = time.perf_counter()

            try:
                result = region_manager.detect_region(entry)
                processing_time = time.perf_counter() - start_time

                # Check for timeout
                if processing_time > 5.0:
                    timeout_count += 1
                    continue

                # Check result validity
                if hasattr(result, "region_code") and hasattr(result, "confidence"):
                    if result.region_code in valid_regions:
                        if 0.0 <= result.confidence <= 1.0:
                            valid_results += 1
                        else:
                            invalid_regions.append(
                                (
                                    random_input[:50],
                                    result.region_code,
                                    result.confidence,
                                )
                            )
                    else:
                        invalid_regions.append(
                            (random_input[:50], result.region_code, "invalid region")
                        )
                else:
                    invalid_regions.append(
                        (random_input[:50], "malformed result", str(result)[:100])
                    )

            except Exception as e:
                processing_time = time.perf_counter() - start_time

                # Check for crash vs timeout
                if processing_time > 5.0:
                    timeout_count += 1
                else:
                    # Check if it's a reasonable error
                    error_msg = str(e).lower()
                    if any(
                        term in error_msg
                        for term in ["memory", "recursion", "timeout", "size", "length"]
                    ):
                        # Acceptable error
                        valid_results += 1
                    else:
                        crash_count += 1
                        if crash_count <= 10:  # Log first 10 crashes
                            print(f"Crash {crash_count}: {random_input[:50]} -> {e}")

        # Analyze results
        total_tests = 1000
        crash_rate = crash_count / total_tests
        timeout_rate = timeout_count / total_tests
        validity_rate = valid_results / total_tests

        print(
            f"Random fuzzing: {crash_rate:.2%} crashes, {timeout_rate:.2%} timeouts, {validity_rate:.2%} valid"
        )

        # Should handle most random input without crashing
        assert crash_rate < 0.1, f"High crash rate on random input: {crash_rate:.2%}"
        assert (
            timeout_rate < 0.05
        ), f"High timeout rate on random input: {timeout_rate:.2%}"

        # Should not produce too many invalid results
        if invalid_regions:
            invalid_rate = len(invalid_regions) / total_tests
            assert (
                invalid_rate < 0.2
            ), f"High invalid result rate: {invalid_rate:.2%}, examples: {invalid_regions[:5]}"

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_name_like_fuzzing(self, region_manager, input_generator):
        """Fuzz with name-like strings."""

        results = {"crashes": [], "timeouts": [], "invalid": [], "valid": 0}

        for i in range(500):  # 500 name-like inputs
            name_like = input_generator.random_name_like_string()
            entry = {"CanonicalLatin": name_like}

            start_time = time.perf_counter()

            try:
                result = region_manager.detect_region(entry)
                processing_time = time.perf_counter() - start_time

                if processing_time > 3.0:
                    results["timeouts"].append((name_like[:50], processing_time))
                    continue

                # Validate result
                if hasattr(result, "region_code") and hasattr(result, "confidence"):
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

                    if (
                        result.region_code in valid_regions
                        and 0.0 <= result.confidence <= 1.0
                    ):
                        results["valid"] += 1
                    else:
                        results["invalid"].append(
                            (name_like[:50], result.region_code, result.confidence)
                        )
                else:
                    results["invalid"].append(
                        (name_like[:50], "malformed", str(result)[:50])
                    )

            except Exception as e:
                processing_time = time.perf_counter() - start_time

                if processing_time > 3.0:
                    results["timeouts"].append((name_like[:50], processing_time))
                else:
                    results["crashes"].append((name_like[:50], str(e)[:100]))

        # Analyze name-like fuzzing results
        total = 500
        crash_rate = len(results["crashes"]) / total
        timeout_rate = len(results["timeouts"]) / total
        invalid_rate = len(results["invalid"]) / total
        valid_rate = results["valid"] / total

        print(
            f"Name-like fuzzing: {crash_rate:.2%} crashes, {timeout_rate:.2%} timeouts, {invalid_rate:.2%} invalid, {valid_rate:.2%} valid"
        )

        # Name-like inputs should be handled better than random inputs
        assert (
            crash_rate < 0.05
        ), f"High crash rate on name-like input: {crash_rate:.2%}"
        assert (
            timeout_rate < 0.02
        ), f"High timeout rate on name-like input: {timeout_rate:.2%}"
        assert valid_rate > 0.8, f"Low valid rate on name-like input: {valid_rate:.2%}"

    # ========== PROPERTY-BASED TESTING ==========

    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not available")
    @pytest.mark.paranoid
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=200, deadline=5000)  # 200 examples, 5 second deadline
    @pytest.mark.timeout(15)
    def test_property_never_crashes(self, region_manager, text_input):
        """Property: System should never crash on any text input."""

        entry = {"CanonicalLatin": text_input}

        try:
            result = region_manager.detect_region(entry)

            # If it returns a result, it should be well-formed
            if hasattr(result, "region_code"):
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
                assert (
                    result.region_code in valid_regions
                ), f"Invalid region code: {result.region_code} for input: {repr(text_input)}"

            if hasattr(result, "confidence"):
                assert (
                    0.0 <= result.confidence <= 1.0
                ), f"Invalid confidence: {result.confidence} for input: {repr(text_input)}"

        except Exception as e:
            # Some exceptions are acceptable (memory limits, etc.)
            acceptable_errors = [
                "memory",
                "recursion",
                "timeout",
                "size",
                "length",
                "unicode",
                "encoding",
            ]
            error_msg = str(e).lower()

            if not any(term in error_msg for term in acceptable_errors):
                pytest.fail(f"Unacceptable crash on input {repr(text_input)}: {e}")

    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not available")
    @pytest.mark.paranoid
    @given(st.text(alphabet=string.ascii_letters + " ,-", min_size=3, max_size=50))
    @settings(max_examples=100, deadline=3000)
    @pytest.mark.timeout(15)
    def test_property_ascii_names_valid_regions(self, region_manager, ascii_name):
        """Property: ASCII name-like strings should produce valid regions."""

        entry = {"CanonicalLatin": ascii_name}

        try:
            result = region_manager.detect_region(entry)

            # Should produce valid result
            assert hasattr(
                result, "region_code"
            ), f"Missing region_code for: {ascii_name}"
            assert hasattr(
                result, "confidence"
            ), f"Missing confidence for: {ascii_name}"

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
            assert (
                result.region_code in valid_regions
            ), f"Invalid region for ASCII name {ascii_name}: {result.region_code}"
            assert (
                0.0 <= result.confidence <= 1.0
            ), f"Invalid confidence for ASCII name {ascii_name}: {result.confidence}"

        except Exception as e:
            # ASCII names should generally not cause exceptions
            acceptable_errors = ["memory", "size", "length"]
            error_msg = str(e).lower()

            if not any(term in error_msg for term in acceptable_errors):
                pytest.fail(f"Unacceptable error on ASCII name {ascii_name}: {e}")

    # ========== MUTATION FUZZING ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_mutation_fuzzing(self, region_manager, input_generator):
        """Mutation fuzzing - start with valid names and mutate them."""

        # Base valid names to mutate
        base_names = [
            "Smith, John",
            "García, José",
            "김정은",
            "Wang, Wei",
            "Al-Ahmad, Mohammed",
            "Müller, Hans",
            "Ivanov, Vladimir",
            "田中太郎",
            "Tanaka, Taro",
            "Singh, Raj",
        ]

        mutation_results = {
            "crashes": 0,
            "timeouts": 0,
            "valid": 0,
            "changed_region": 0,
        }

        for base_name in base_names:
            # Get baseline result
            baseline_entry = {"CanonicalLatin": base_name}

            try:
                baseline_result = region_manager.detect_region(baseline_entry)
                baseline_region = baseline_result.region_code
            except Exception:
                continue  # Skip if baseline fails

            # Apply mutations
            for mutation_round in range(20):  # 20 mutations per base name
                mutated_name = self.mutate_string(base_name)
                entry = {"CanonicalLatin": mutated_name}

                start_time = time.perf_counter()

                try:
                    result = region_manager.detect_region(entry)
                    processing_time = time.perf_counter() - start_time

                    if processing_time > 2.0:
                        mutation_results["timeouts"] += 1
                        continue

                    # Check result validity
                    if hasattr(result, "region_code") and hasattr(result, "confidence"):
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

                        if (
                            result.region_code in valid_regions
                            and 0.0 <= result.confidence <= 1.0
                        ):
                            mutation_results["valid"] += 1

                            # Track region changes
                            if result.region_code != baseline_region:
                                mutation_results["changed_region"] += 1
                        else:
                            # Invalid result is not a crash, but not ideal
                            pass
                    else:
                        # Malformed result
                        pass

                except Exception as e:
                    processing_time = time.perf_counter() - start_time

                    if processing_time > 2.0:
                        mutation_results["timeouts"] += 1
                    else:
                        # Check if acceptable error
                        error_msg = str(e).lower()
                        if any(
                            term in error_msg
                            for term in ["memory", "recursion", "size", "length"]
                        ):
                            mutation_results["valid"] += 1  # Acceptable failure
                        else:
                            mutation_results["crashes"] += 1

        # Analyze mutation results
        total_mutations = len(base_names) * 20
        crash_rate = mutation_results["crashes"] / total_mutations
        timeout_rate = mutation_results["timeouts"] / total_mutations
        valid_rate = mutation_results["valid"] / total_mutations

        print(
            f"Mutation fuzzing: {crash_rate:.2%} crashes, {timeout_rate:.2%} timeouts, {valid_rate:.2%} valid"
        )

        # Mutations should generally be handled gracefully
        assert (
            crash_rate < 0.1
        ), f"High crash rate in mutation fuzzing: {crash_rate:.2%}"
        assert (
            timeout_rate < 0.05
        ), f"High timeout rate in mutation fuzzing: {timeout_rate:.2%}"
        assert valid_rate > 0.7, f"Low valid rate in mutation fuzzing: {valid_rate:.2%}"

    def mutate_string(self, s: str) -> str:
        """Apply random mutation to a string."""

        if not s:
            return s

        mutations = [
            # Character-level mutations
            lambda x: self.flip_random_char(x),
            lambda x: self.insert_random_char(x),
            lambda x: self.delete_random_char(x),
            lambda x: self.duplicate_random_char(x),
            lambda x: self.swap_adjacent_chars(x),
            # String-level mutations
            lambda x: x.upper(),
            lambda x: x.lower(),
            lambda x: x[::-1],  # Reverse
            lambda x: x + x,  # Duplicate
            lambda x: x[len(x) // 2 :] + x[: len(x) // 2],  # Rotate
            # Unicode mutations
            lambda x: self.add_combining_chars(x),
            lambda x: self.add_zero_width_chars(x),
            lambda x: self.normalize_unicode(x),
            # Format mutations
            lambda x: x.replace(",", ""),
            lambda x: x.replace(" ", ""),
            lambda x: x.replace(",", ", "),
            lambda x: x.replace(" ", "  "),
        ]

        mutation = random.choice(mutations)

        try:
            return mutation(s)
        except (IndexError, ValueError, UnicodeError):
            return s  # Return original if mutation fails

    def flip_random_char(self, s: str) -> str:
        """Flip a random character to another random character."""
        if not s:
            return s

        pos = random.randint(0, len(s) - 1)
        new_char = chr(random.randint(32, 126))  # Printable ASCII
        return s[:pos] + new_char + s[pos + 1 :]

    def insert_random_char(self, s: str) -> str:
        """Insert a random character at random position."""
        pos = random.randint(0, len(s))
        new_char = chr(random.randint(32, 126))
        return s[:pos] + new_char + s[pos:]

    def delete_random_char(self, s: str) -> str:
        """Delete a random character."""
        if len(s) <= 1:
            return s

        pos = random.randint(0, len(s) - 1)
        return s[:pos] + s[pos + 1 :]

    def duplicate_random_char(self, s: str) -> str:
        """Duplicate a random character."""
        if not s:
            return s

        pos = random.randint(0, len(s) - 1)
        char = s[pos]
        return s[:pos] + char + char + s[pos + 1 :]

    def swap_adjacent_chars(self, s: str) -> str:
        """Swap two adjacent characters."""
        if len(s) < 2:
            return s

        pos = random.randint(0, len(s) - 2)
        chars = list(s)
        chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
        return "".join(chars)

    def add_combining_chars(self, s: str) -> str:
        """Add combining characters to random positions."""
        if not s:
            return s

        combining_chars = [
            "\u0300",
            "\u0301",
            "\u0302",
            "\u0303",
            "\u0327",
        ]  # Various combining marks
        pos = random.randint(0, len(s) - 1)
        combining = random.choice(combining_chars)
        return s[: pos + 1] + combining + s[pos + 1 :]

    def add_zero_width_chars(self, s: str) -> str:
        """Add zero-width characters."""
        if not s:
            return s

        zero_width = ["\u200b", "\u200c", "\u200d", "\u2060"]  # Zero-width chars
        pos = random.randint(0, len(s))
        zw_char = random.choice(zero_width)
        return s[:pos] + zw_char + s[pos:]

    def normalize_unicode(self, s: str) -> str:
        """Apply Unicode normalization."""
        normalizations = ["NFC", "NFD", "NFKC", "NFKD"]
        norm = random.choice(normalizations)
        try:
            return unicodedata.normalize(norm, s)
        except (ValueError, UnicodeError):
            return s

    # ========== STRESS FUZZING ==========

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_sustained_fuzzing_stress(self, region_manager, input_generator):
        """Sustained fuzzing stress test."""

        start_time = time.time()
        max_duration = 60  # 1 minute of sustained fuzzing
        iterations = 0

        stats = {"total": 0, "crashes": 0, "timeouts": 0, "valid": 0, "errors": []}

        while time.time() - start_time < max_duration:
            # Generate different types of inputs
            input_types = [
                lambda: input_generator.random_unicode_string(1, 50),
                lambda: input_generator.random_name_like_string(),
                lambda: "".join(
                    chr(random.randint(0, 0x10FFFF))
                    for _ in range(random.randint(1, 20))
                ),
                lambda: chr(0x0000) * random.randint(1, 100),  # Null bytes
                lambda: "A" * random.randint(1000, 10000),  # Very long
            ]

            input_func = random.choice(input_types)

            try:
                test_input = input_func()
            except (ValueError, OverflowError):
                continue  # Skip invalid Unicode

            entry = {"CanonicalLatin": test_input}

            op_start = time.perf_counter()
            stats["total"] += 1

            try:
                result = region_manager.detect_region(entry)
                op_time = time.perf_counter() - op_start

                if op_time > 1.0:
                    stats["timeouts"] += 1
                elif hasattr(result, "region_code") and hasattr(result, "confidence"):
                    stats["valid"] += 1
                else:
                    stats["errors"].append(f"Malformed result: {str(result)[:50]}")

            except Exception as e:
                op_time = time.perf_counter() - op_start

                if op_time > 1.0:
                    stats["timeouts"] += 1
                else:
                    error_msg = str(e).lower()
                    if any(
                        term in error_msg
                        for term in ["memory", "recursion", "size", "length", "unicode"]
                    ):
                        stats["valid"] += 1  # Acceptable error
                    else:
                        stats["crashes"] += 1
                        if len(stats["errors"]) < 10:  # Collect first 10 crash details
                            stats["errors"].append(f"Crash: {str(e)[:100]}")

            iterations += 1

            # Periodic garbage collection
            if iterations % 1000 == 0:
                gc.collect()

        # Analyze sustained fuzzing results
        duration = time.time() - start_time
        ops_per_second = stats["total"] / duration

        crash_rate = stats["crashes"] / stats["total"] if stats["total"] > 0 else 0
        timeout_rate = stats["timeouts"] / stats["total"] if stats["total"] > 0 else 0
        valid_rate = stats["valid"] / stats["total"] if stats["total"] > 0 else 0

        print(
            f"Sustained fuzzing: {stats['total']} ops in {duration:.1f}s ({ops_per_second:.1f} ops/sec)"
        )
        print(
            f"Results: {crash_rate:.2%} crashes, {timeout_rate:.2%} timeouts, {valid_rate:.2%} valid"
        )

        # Should maintain reasonable performance and stability
        assert (
            ops_per_second > 10
        ), f"Performance degraded during sustained fuzzing: {ops_per_second:.1f} ops/sec"
        assert (
            crash_rate < 0.1
        ), f"High crash rate during sustained fuzzing: {crash_rate:.2%}"
        assert (
            timeout_rate < 0.2
        ), f"High timeout rate during sustained fuzzing: {timeout_rate:.2%}"

        if stats["errors"]:
            print(f"Sample errors: {stats['errors'][:5]}")


@pytest.mark.paranoid
class TestPropertyInvariants:
    """Test system invariants that should always hold."""

    @pytest.fixture
    def region_manager(self):
        return RegionManager()

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_invariant_deterministic_results(self, region_manager):
        """Invariant: Same input should always produce same result."""

        test_inputs = [
            "Smith, John",
            "García, José",
            "김정은",
            "Wang, Wei",
            "Al-Ahmad, Mohammed",
            "",
            "X",
            "Very Long Name That Goes On And On",
            "Mixed김Scripts문자",
        ]

        for test_input in test_inputs:
            entry = {"CanonicalLatin": test_input}

            # Run multiple times
            results = []
            for _ in range(5):
                try:
                    result = region_manager.detect_region(entry)
                    results.append((result.region_code, result.confidence))
                except Exception as e:
                    results.append(("ERROR", str(e)))

            # All results should be identical
            unique_results = set(results)
            assert (
                len(unique_results) == 1
            ), f"Non-deterministic results for '{test_input}': {unique_results}"

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_invariant_confidence_bounds(self, region_manager):
        """Invariant: Confidence should always be between 0 and 1."""

        # Generate various inputs
        test_inputs = []

        # Add systematic inputs
        for length in [1, 5, 10, 50, 100]:
            test_inputs.append("A" * length)
            test_inputs.append("김" * length)
            test_inputs.append(
                "García" + "x" * (length - 6) if length >= 6 else "García"
            )

        # Add random inputs
        for _ in range(100):
            random_input = "".join(
                random.choices(
                    string.ascii_letters + string.digits + " ,-김정은García",
                    k=random.randint(1, 30),
                )
            )
            test_inputs.append(random_input)

        confidence_violations = []

        for test_input in test_inputs:
            entry = {"CanonicalLatin": test_input}

            try:
                result = region_manager.detect_region(entry)

                if hasattr(result, "confidence"):
                    if not (0.0 <= result.confidence <= 1.0):
                        confidence_violations.append(
                            (test_input[:30], result.confidence)
                        )

            except Exception:
                # Exceptions are acceptable, confidence violations are not
                pass

        assert (
            len(confidence_violations) == 0
        ), f"Confidence bound violations: {confidence_violations[:10]}..."


if __name__ == "__main__":
    # Run with: pytest tests/paranoid/fuzzing/test_fuzzing_hell.py -v --tb=short -s
    pytest.main([__file__, "-v", "--tb=short", "-s"])
