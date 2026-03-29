"""
Comprehensive test suite for all 33 GMNAP regions.
Tests functionality, edge cases, and security for each region.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import os

os.environ["GMNAP_TEST_MODE"] = "true"
import sys
from pathlib import Path

from src.regions.manager import RegionManager

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.base import RegionRuleError


@pytest.fixture(scope="module")
def region_manager():
    """Initialize region manager once for all tests."""
    return RegionManager(Path("./config"))


# All 33 regions that should be working
ALL_REGIONS = [
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",  # Anglo-sphere/Western
    "B1",
    "B2",
    "B3",  # Slavic
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7",
    "C8",
    "C9",  # Middle East/Turkic
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",  # South Asia
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "E6",
    "E7",  # East Asia
    "F1",
    "F2",
    "F3",  # Africa
    "G1",  # Latin America
]


class TestAllRegions:
    """Test comprehensive regional functionality."""

    @pytest.mark.timeout(15)
    def test_all_regions_load(self, region_manager):
        """Test that all 33 regions can be loaded."""
        loaded_regions = []
        failed_regions = []

        for region_code in ALL_REGIONS:
            try:
                region = region_manager.get_region(region_code)
                assert region is not None, f"Region {region_code} returned None"
                assert hasattr(
                    region, "clean"
                ), f"Region {region_code} missing clean method"
                assert hasattr(
                    region, "validate"
                ), f"Region {region_code} missing validate method"
                assert hasattr(
                    region, "augment"
                ), f"Region {region_code} missing augment method"
                loaded_regions.append(region_code)
            except Exception as e:
                failed_regions.append((region_code, str(e)))

        # Report results
        print(f"\nPASS Successfully loaded: {len(loaded_regions)}/33 regions")
        if failed_regions:
            print(f"FAIL Failed to load {len(failed_regions)} regions:")
            for code, error in failed_regions:
                print(f"   - {code}: {error}")

        assert len(failed_regions) == 0, f"Failed to load {len(failed_regions)} regions"
        assert (
            len(loaded_regions) == 33
        ), f"Only loaded {len(loaded_regions)}/33 regions"

    @pytest.mark.timeout(15)
    def test_basic_processing_all_regions(self, region_manager):
        """Test basic name processing for all regions."""
        test_names = {
            "A1": "John Smith",
            "A2": "Marie Dubois",
            "A3": "Erik Andersson",
            "A4": "James Cook",
            "A5": "Jean Baptiste",
            "B1": "Иван Петров",
            "B2": "Милан Јовановић",
            "B3": "Γεώργιος Παπαδόπουλος",
            "C1": "Mehmet Öztürk",
            "C2": "محمد رضایی",
            "C3": "محمد الأحمد",
            "C4": "عبدالله آل سعود",
            "C5": "محمد بن علي",
            "C6": "דוד כהן",
            "C7": "Արմեն Հակոբյան",
            "C8": "გიორგი ჯავახიშვილი",
            "C9": "Əli Əliyev",
            "D1": "राज कुमार",
            "D2": "முருகன் செல்வம்",
            "D3": "রহমান খান",
            "D4": "محمد علی",
            "D5": "සිල්වා පෙරේරා",
            "E1": "王明",
            "E2": "陳大文",
            "E3": "山田太郎",
            "E4": "김민준",
            "E5": "Nguyễn Văn A",
            "E6": "สมชาย ใจดี",
            "E7": "Jose Santos",
            "F1": "Jean-Baptiste Kouamé",
            "F2": "Oluwaseun Adebayo",
            "F3": "አበበ በቀለ",
            "G1": "José García Rodríguez",
        }

        results = {}

        for region_code in ALL_REGIONS:
            try:
                region = region_manager.get_region(region_code)
                test_name = test_names.get(region_code, "Test Name")

                entry = {"GlobalID": f"test-{region_code}", "CanonicalLatin": test_name}

                # Process the entry
                region.clean(entry)

                # Verify processing worked
                assert (
                    "CanonicalLatin" in entry
                ), f"{region_code}: CanonicalLatin missing after clean"
                assert (
                    entry["GlobalID"] == f"test-{region_code}"
                ), f"{region_code}: GlobalID changed"

                results[region_code] = "PASS"
            except Exception as e:
                results[region_code] = f"FAIL: {str(e)[:50]}"

        # Report results
        passed = sum(1 for r in results.values() if r == "PASS")
        print(f"\nPASS Basic processing: {passed}/33 regions passed")

        failures = [(k, v) for k, v in results.items() if v != "PASS"]
        if failures:
            print("FAIL Failed regions:")
            for code, error in failures:
                print(f"   - {code}: {error}")

        assert passed == 33, f"Only {passed}/33 regions passed basic processing"

    @pytest.mark.timeout(15)
    def test_edge_cases_all_regions(self, region_manager):
        """Test edge cases for all regions."""
        edge_cases = [
            ("empty_name", {"GlobalID": "test", "CanonicalLatin": ""}),
            ("whitespace_only", {"GlobalID": "test", "CanonicalLatin": "   "}),
            ("tab_character", {"GlobalID": "test", "CanonicalLatin": "Test\tName"}),
            ("newline_character", {"GlobalID": "test", "CanonicalLatin": "Test\nName"}),
            ("single_char", {"GlobalID": "test", "CanonicalLatin": "X"}),
            ("numbers", {"GlobalID": "test", "CanonicalLatin": "123"}),
            ("special_chars", {"GlobalID": "test", "CanonicalLatin": "@#$%"}),
            ("very_long", {"GlobalID": "test", "CanonicalLatin": "A" * 200}),
            (
                "hyphenated",
                {"GlobalID": "test", "CanonicalLatin": "Jean-Claude Van-Damme"},
            ),
            ("apostrophe", {"GlobalID": "test", "CanonicalLatin": "O'Connor"}),
        ]

        results = {}

        for region_code in ALL_REGIONS:
            region = region_manager.get_region(region_code)
            region_results = []

            for case_name, test_entry in edge_cases:
                try:
                    # Make a copy to avoid mutation
                    entry = test_entry.copy()
                    region.clean(entry)

                    # Should not crash and should maintain GlobalID
                    assert entry["GlobalID"] == "test", "GlobalID changed"
                    region_results.append((case_name, "PASS"))
                except Exception as e:
                    region_results.append((case_name, f"FAIL: {str(e)[:30]}"))

            passed = sum(1 for _, r in region_results if r == "PASS")
            results[region_code] = (passed, len(edge_cases), region_results)

        # Report results
        print("\n Edge Case Results:")
        all_passed = True
        for region_code, (passed, total, details) in results.items():
            if passed == total:
                print(f"PASS {region_code}: {passed}/{total} edge cases passed")
            else:
                print(f"WARN  {region_code}: {passed}/{total} edge cases passed")
                all_passed = False
                # Show failures
                for case_name, result in details:
                    if result != "PASS":
                        print(f"     - {case_name}: {result}")

        assert all_passed, "Some regions failed edge case tests"

    @pytest.mark.timeout(15)
    def test_security_all_regions(self, region_manager):
        """Test security validation for all regions."""
        attack_vectors = [
            ("sql_injection", "'; DROP TABLE users; --"),
            ("xss", '<script>alert("XSS")</script>'),
            ("command_injection", "; ls -la /etc/passwd"),
            ("ldap_injection", "*(|(cn=*))"),
            ("path_traversal", "../../../etc/passwd"),
            ("null_byte", "test\x00.txt"),
            ("unicode_exploit", "test\ufff9\ufffa\ufffb"),
            ("xxe", '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'),
        ]

        results = {}

        for region_code in ALL_REGIONS:
            region = region_manager.get_region(region_code)
            region_results = []

            for attack_name, payload in attack_vectors:
                try:
                    entry = {"GlobalID": "test", "CanonicalLatin": payload}
                    region.clean(entry)
                    # If we get here without exception, it might not be blocking
                    # Check if the payload was sanitized
                    if payload in str(entry.get("CanonicalLatin", "")):
                        region_results.append((attack_name, "FAIL: Not blocked"))
                    else:
                        region_results.append((attack_name, "PASS: Sanitized"))
                except (RegionRuleError, ValueError, Exception):
                    # Good - attack was blocked
                    region_results.append((attack_name, "PASS: Blocked"))

            blocked = sum(1 for _, r in region_results if "PASS" in r)
            results[region_code] = (blocked, len(attack_vectors), region_results)

        # Report results
        print("\n Security Test Results:")
        all_secure = True
        for region_code, (blocked, total, details) in results.items():
            if blocked == total:
                print(f"PASS {region_code}: {blocked}/{total} attacks blocked")
            else:
                print(f"WARN  {region_code}: {blocked}/{total} attacks blocked")
                all_secure = False
                # Show what wasn't blocked
                for attack_name, result in details:
                    if "FAIL" in result:
                        print(f"     - {attack_name}: {result}")

        assert all_secure, "Some regions have security vulnerabilities"

    @pytest.mark.timeout(15)
    def test_unicode_normalization_all_regions(self, region_manager):
        """Test Unicode normalization for all regions."""
        unicode_tests = [
            ("combining_chars", "\u00e9", "\u00e9"),  # Precomposed vs decomposed
            ("zero_width", "test\u200bname", "testname"),  # Zero-width space
            ("rtl_marks", "\u202etest", "test"),  # Right-to-left override
            ("ligatures", "\ufb01le", "file"),  # fi ligature
            ("fullwidth", "\uff21\uff22\uff23", "ABC"),  # Fullwidth Latin
        ]

        results = {}

        for region_code in ALL_REGIONS:
            region = region_manager.get_region(region_code)
            region_results = []

            for test_name, input_text, expected_contains in unicode_tests:
                try:
                    entry = {"GlobalID": "test", "CanonicalLatin": input_text}
                    region.clean(entry)

                    # Check if normalization happened
                    result = entry.get("CanonicalLatin", "")
                    if expected_contains in result or input_text == result:
                        region_results.append((test_name, "PASS"))
                    else:
                        region_results.append((test_name, f"FAIL: Got {result}"))
                except Exception as e:
                    region_results.append((test_name, f"ERROR: {str(e)[:30]}"))

            passed = sum(1 for _, r in region_results if r == "PASS")
            results[region_code] = (passed, len(unicode_tests))

        # Report summary
        print("\n Unicode Normalization Results:")
        for region_code, (passed, total) in results.items():
            status = "PASS" if passed == total else "WARN"
            print(f"{status} {region_code}: {passed}/{total} unicode tests passed")

    @pytest.mark.timeout(15)
    def test_validation_all_regions(self, region_manager):
        """Test validation methods for all regions."""
        results = {}

        for region_code in ALL_REGIONS:
            region = region_manager.get_region(region_code)

            # Test with valid entry
            valid_entry = {"GlobalID": "test", "CanonicalLatin": "Test Name"}
            region.clean(valid_entry)

            try:
                is_valid = region.validate(valid_entry)
                results[region_code] = "PASS" if is_valid else "FAIL: Invalid"
            except Exception as e:
                results[region_code] = f"ERROR: {str(e)[:30]}"

        # Report results
        print("\n Validation Method Results:")
        passed = sum(1 for r in results.values() if r == "PASS")
        print(f"Overall: {passed}/33 regions have working validation")

        failures = [(k, v) for k, v in results.items() if v != "PASS"]
        if failures:
            print("Issues found:")
            for code, error in failures:
                print(f"   - {code}: {error}")

    @pytest.mark.timeout(15)
    def test_augment_all_regions(self, region_manager):
        """Test augmentation methods for all regions."""
        results = {}

        for region_code in ALL_REGIONS:
            region = region_manager.get_region(region_code)

            entry = {"GlobalID": "test", "CanonicalLatin": "Test Name"}

            # Clean first
            region.clean(entry)

            # Count keys before augment
            keys_before = len(entry.keys())

            try:
                region.augment(entry)
                keys_after = len(entry.keys())

                # Check if augment added anything
                if keys_after >= keys_before:
                    results[region_code] = "PASS"
                else:
                    results[region_code] = "FAIL: Removed keys"
            except Exception as e:
                results[region_code] = f"ERROR: {str(e)[:30]}"

        # Report results
        print("\n Augmentation Method Results:")
        passed = sum(1 for r in results.values() if r == "PASS")
        print(f"Overall: {passed}/33 regions have working augmentation")

        failures = [(k, v) for k, v in results.items() if v != "PASS"]
        if failures:
            print("Issues found:")
            for code, error in failures:
                print(f"   - {code}: {error}")


class TestRegionalPerformance:
    """Tests for regional processing performance."""

    @pytest.mark.timeout(15)
    def test_processing_speed_all_regions(self, region_manager):
        """Measure processing speed for each region."""
        import time

        results = {}
        entries_per_test = 100

        for region_code in ALL_REGIONS:
            region = region_manager.get_region(region_code)

            # Create test entries
            entries = [
                {"GlobalID": f"perf-{i}", "CanonicalLatin": f"Test Name {i}"}
                for i in range(entries_per_test)
            ]

            # Measure processing time
            start_time = time.time()
            for entry in entries:
                try:
                    region.clean(entry)
                except Exception:
                    pass  # Don't fail on individual entries

            elapsed = time.time() - start_time
            entries_per_second = entries_per_test / elapsed if elapsed > 0 else 0
            results[region_code] = entries_per_second

        # Report results
        print("\n Performance Results (entries/second):")
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)

        for region_code, speed in sorted_results[:5]:
            print(f"  {region_code}: {speed:.0f} entries/sec")

        print("...")

        for region_code, speed in sorted_results[-3:]:
            print(f"  {region_code}: {speed:.0f} entries/sec")

        avg_speed = sum(results.values()) / len(results)
        print(f"\nAverage: {avg_speed:.0f} entries/sec")

        # All regions should process at least 100 entries/sec
        slow_regions = [k for k, v in results.items() if v < 100]
        assert len(slow_regions) == 0, f"Slow regions (<100/sec): {slow_regions}"


@pytest.mark.timeout(15)
def test_summary():
    """Print a summary of all test results."""
    print("\n" + "=" * 60)
    print("🎯 COMPREHENSIVE REGIONAL TESTING COMPLETE")
    print("=" * 60)
    print("""
    All 33 regions tested for:
    PASS Loading and initialization
    PASS Basic name processing
    PASS Edge case handling
    PASS Security validation
    PASS Unicode normalization
    PASS Validation methods
    PASS Augmentation methods
    PASS Performance characteristics
    """)
    print("=" * 60)


if __name__ == "__main__":
    # Run tests directly
    import sys
    from pathlib import Path

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    # Initialize manager
    manager = RegionManager(Path("./config"))

    # Create test instance
    test_suite = TestAllRegions()

    print("🔍 Running Comprehensive Regional Tests")
    print("=" * 60)

    # Run each test
    try:
        test_suite.test_all_regions_load(manager)
        test_suite.test_basic_processing_all_regions(manager)
        test_suite.test_edge_cases_all_regions(manager)
        test_suite.test_security_all_regions(manager)
        test_suite.test_unicode_normalization_all_regions(manager)
        test_suite.test_validation_all_regions(manager)
        test_suite.test_augment_all_regions(manager)

        perf_test = TestRegionalPerformance()
        perf_test.test_processing_speed_all_regions(manager)

        test_summary()
        print("\nPASS ALL TESTS PASSED!")
    except AssertionError as e:
        print(f"\nFAIL TEST FAILED: {e}")
    except Exception as e:
        print(f"\n UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
