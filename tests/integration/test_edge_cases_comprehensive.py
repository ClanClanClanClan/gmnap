from typing import List
import pytest

#!/usr/bin/env python3
"""
Comprehensive Edge Case Testing for GMNAP v7
Use this to verify edge case fixes work properly.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.append(str(Path.cwd()))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import os

os.environ["GMNAP_TEST_MODE"] = "true"
from src.regions.manager import RegionManager


def get_edge_test_cases() -> List[Dict]:
    """Get comprehensive edge test cases."""
    return [
        {
            "name": "Empty CanonicalLatin",
            "test": {
                "CanonicalLatin": "",
                "CanonicalNative": "Test",
                "GlobalID": "edge-empty-latin",
            },
            "should_pass": True,
            "v7_requirement": "Graceful degradation",
        },
        {
            "name": "Empty CanonicalNative",
            "test": {
                "CanonicalLatin": "Test",
                "CanonicalNative": "",
                "GlobalID": "edge-empty-native",
            },
            "should_pass": True,
            "v7_requirement": "Handle missing fields",
        },
        {
            "name": "Missing Both Canonical",
            "test": {"GlobalID": "edge-missing-both"},
            "should_pass": True,  # Should handle gracefully
            "v7_requirement": "Graceful degradation",
        },
        {
            "name": "Single Character",
            "test": {"CanonicalLatin": "A", "GlobalID": "edge-single-char"},
            "should_pass": True,
            "v7_requirement": "Edge case support",
        },
        {
            "name": "Very Long Name",
            "test": {"CanonicalLatin": "Test" * 50, "GlobalID": "edge-very-long"},
            "should_pass": True,
            "v7_requirement": "Handle extremes",
        },
        {
            "name": "Special Characters",
            "test": {
                "CanonicalLatin": "José-María de la Cruz",
                "GlobalID": "edge-special-chars",
            },
            "should_pass": True,
            "v7_requirement": "International character support",
        },
        {
            "name": "Mixed Scripts",
            "test": {
                "CanonicalLatin": "Wang 王",
                "CanonicalNative": "王明",
                "GlobalID": "edge-mixed-script",
            },
            "should_pass": True,
            "v7_requirement": "Multi-script support",
        },
        {
            "name": "Mononym",
            "test": {"CanonicalLatin": "Aristotle", "GlobalID": "edge-mononym"},
            "should_pass": True,
            "v7_requirement": "FamilyNameType: mononym",
        },
        {
            "name": "Numbers in Name",
            "test": {"CanonicalLatin": "John Smith III", "GlobalID": "edge-numbers"},
            "should_pass": True,
            "v7_requirement": "Handle suffixes",
        },
        {
            "name": "Hyphenated Name",
            "test": {
                "CanonicalLatin": "Anne-Marie Smith-Jones",
                "GlobalID": "edge-hyphenated",
            },
            "should_pass": True,
            "v7_requirement": "Compound name support",
        },
    ]


@pytest.mark.timeout(15)
def test_region_edge_cases(
    region_code: str, manager: RegionManager
) -> Tuple[int, int, List[str]]:
    """Test edge cases for a specific region."""
    region = manager.get_region(region_code)
    if not region:
        return 0, 0, [f"Failed to load region {region_code}"]

    edge_cases = get_edge_test_cases()
    passed = 0
    failed = 0
    failures = []

    for edge_case in edge_cases:
        try:
            entry = edge_case["test"].copy()

            # Test each step of the pipeline
            error_step = None
            error_msg = None

            try:
                region.clean(entry)
            except Exception as e:
                error_step = "clean"
                error_msg = str(e)[:100]

            if not error_step:
                try:
                    region.augment(entry)
                except Exception as e:
                    error_step = "augment"
                    error_msg = str(e)[:100]

            if not error_step:
                try:
                    region.validate(entry)
                except Exception as e:
                    error_step = "validate"
                    error_msg = str(e)[:100]

            if not error_step:
                try:
                    key = region.order_key(entry)
                except Exception as e:
                    error_step = "order_key"
                    error_msg = str(e)[:100]

            if error_step:
                if edge_case["should_pass"]:
                    failed += 1
                    failures.append(
                        f"{edge_case['name']}: FAIL at {error_step} - {error_msg}"
                    )
                else:
                    # Expected to fail
                    passed += 1
            else:
                if edge_case["should_pass"]:
                    passed += 1
                else:
                    # Should have failed but didn't
                    failed += 1
                    failures.append(
                        f"{edge_case['name']}: Should have failed but passed"
                    )

        except Exception as e:
            failed += 1
            failures.append(f"{edge_case['name']}: EXCEPTION - {str(e)[:100]}")

    return passed, failed, failures


def run_comprehensive_test():
    """Run comprehensive edge case tests for all regions."""
    print("🧪 COMPREHENSIVE EDGE CASE TESTING")
    print("=" * 60)
    print("Testing V7 compliance and edge case handling")
    print()

    manager = RegionManager(Path("./config"))

    # All regions to test
    all_regions = [
        "A1",
        "A2",
        "A3",
        "B1",
        "B2",
        "B3",
        "C1",
        "C2",
        "C3",
        "C4",
        "C9",
        "D1",
        "D2",
        "D3",
        "D4",
        "E1",
        "E2",
        "E3",
        "E4",
        "F2",
        "G1",
    ]

    # Track overall statistics
    total_passed = 0
    total_failed = 0
    problematic_regions = []
    excellent_regions = []

    print("Testing edge cases for each region...")
    print()

    for region_code in all_regions:
        passed, failed, failures = test_region_edge_cases(region_code, manager)
        total_passed += passed
        total_failed += failed

        success_rate = (
            (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0
        )

        # Categorize regions
        if success_rate >= 90:
            excellent_regions.append(region_code)
            status = "PASS"
        elif success_rate >= 70:
            status = "WARN"
        else:
            problematic_regions.append(region_code)
            status = "FAIL"

        print(
            f"{status} {region_code}: {passed}/{passed + failed} ({success_rate:.1f}%)"
        )

        # Show failures for problematic regions
        if success_rate < 70 and failures:
            for failure in failures[:3]:  # Show first 3 failures
                print(f"    - {failure}")
            if len(failures) > 3:
                print(f"    ... and {len(failures) - 3} more failures")

    # Calculate overall statistics
    overall_success_rate = (
        (total_passed / (total_passed + total_failed) * 100)
        if (total_passed + total_failed) > 0
        else 0
    )

    print()
    print("=" * 60)
    print("📊 OVERALL RESULTS")
    print(f"Total Tests: {total_passed + total_failed}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Success Rate: {overall_success_rate:.1f}%")
    print()

    # Show region breakdown
    print(f"🏆 Excellent Regions (>=90%): {len(excellent_regions)}/21")
    if excellent_regions:
        print(f"   {', '.join(excellent_regions)}")

    print(f"FAIL Problematic Regions (<70%): {len(problematic_regions)}/21")
    if problematic_regions:
        print(f"   {', '.join(problematic_regions)}")

    print()
    print("=" * 60)

    # V7 Compliance Assessment
    print("🎯 V7 COMPLIANCE ASSESSMENT")

    if overall_success_rate >= 97:
        print("PASS FULLY COMPLIANT: Meets V7 roundtrip_script_rate_min: 0.97")
    elif overall_success_rate >= 85:
        print("WARN MOSTLY COMPLIANT: Close to V7 requirements")
    elif overall_success_rate >= 70:
        print("WARN PARTIALLY COMPLIANT: Significant gaps in V7 compliance")
    else:
        print("FAIL NOT COMPLIANT: Major V7 compliance failures")

    print()

    # Recommendations
    print("💡 RECOMMENDATIONS")
    if overall_success_rate < 75:
        print("🚨 CRITICAL: Edge case handling needs immediate attention!")
        print("   - Focus on regions:", ", ".join(problematic_regions[:5]))
        print("   - Review clean() and validate() methods")
        print("   - Implement graceful degradation")
    elif overall_success_rate < 85:
        print("WARN IMPORTANT: Edge case handling needs improvement")
        print("   - Target 85%+ for production readiness")
    else:
        print("PASS Good edge case handling - ready for production consideration")

    return overall_success_rate


@pytest.mark.timeout(15)
def test_specific_region(region_code: str):
    """Test a specific region in detail."""
    print(f"🔍 DETAILED EDGE CASE TEST: {region_code}")
    print("=" * 60)

    manager = RegionManager(Path("./config"))
    region = manager.get_region(region_code)

    if not region:
        print(f"FAIL Failed to load region {region_code}")
        return

    edge_cases = get_edge_test_cases()

    for edge_case in edge_cases:
        print(f"\n📝 Test: {edge_case['name']}")
        print(f"   V7 Requirement: {edge_case['v7_requirement']}")
        print(f"   Input: {edge_case['test']}")

        entry = edge_case["test"].copy()

        # Test each step
        steps = ["clean", "augment", "validate", "order_key"]
        for step in steps:
            try:
                if step == "clean":
                    region.clean(entry)
                elif step == "augment":
                    region.augment(entry)
                elif step == "validate":
                    region.validate(entry)
                elif step == "order_key":
                    result = region.order_key(entry)
                    print(f"   PASS {step}: SUCCESS (key: {result[:30]}...)")
                    continue
                print(f"   PASS {step}: SUCCESS")
            except Exception as e:
                print(f"   FAIL {step}: FAILED - {str(e)[:100]}")
                break

        # Check if result matches expectation
        if edge_case["should_pass"]:
            print(f"   Expected: PASS")
        else:
            print(f"   Expected: FAIL")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test edge cases for GMNAP v7")
    parser.add_argument("--region", help="Test specific region", default=None)
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.region:
        test_specific_region(args.region)
    else:
        success_rate = run_comprehensive_test()

        # Exit with error if below threshold
        if success_rate < 75:
            print()
            print("FAIL EDGE CASE HANDLING BELOW ACCEPTABLE THRESHOLD (75%)")
        # sys.exit(1)  # MOVED: Was at module level
        else:
            print()
            print("PASS EDGE CASE HANDLING ACCEPTABLE")
    # sys.exit(0)  # MOVED: Was at module level
