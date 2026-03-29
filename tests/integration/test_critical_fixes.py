import pytest

#!/usr/bin/env python3
"""
Quick verification test for critical security and regional bias fixes.
Tests:
1. Security sanitization (injection payloads should be sanitized in output)
2. Regional bias fix ("Lee, John" should -> A1, not E4)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager


@pytest.mark.timeout(15)
def test_security_sanitization():
    """Test that malicious payloads are sanitized in metadata output."""
    print("🔒 TESTING SECURITY SANITIZATION...")

    manager = RegionManager()

    # Test SQL injection payload
    malicious_entry = {"CanonicalLatin": "Smith'; DROP TABLE users; --"}

    result = manager.detect_region(malicious_entry)

    # Check that the malicious payload is NOT reflected in any metadata values
    metadata_str = str(result.metadata)
    dangerous_patterns = ["DROP TABLE", "';", "--", "<script>", "javascript:"]

    sanitization_passed = True
    for pattern in dangerous_patterns:
        if pattern in metadata_str:
            print(
                f"FAIL SECURITY FAILURE: Found dangerous pattern '{pattern}' in metadata: {metadata_str}"
            )
            sanitization_passed = False

    if sanitization_passed:
        print(f"PASS SECURITY SANITIZATION: PASSED - No dangerous patterns in metadata")
        print(f"   Input: {malicious_entry['CanonicalLatin']}")
        print(f"   Output metadata: {result.metadata}")

    return sanitization_passed


@pytest.mark.timeout(15)
def test_regional_bias_fix():
    """Test that 'Lee, John' is classified as A1 (Anglo), not E4 (Korean)."""
    print("\n🎯 TESTING REGIONAL BIAS FIX...")

    manager = RegionManager()

    # Test the specific case that was failing
    test_entry = {"CanonicalLatin": "Lee, John"}

    result = manager.detect_region(test_entry)

    print(f"   Input: {test_entry['CanonicalLatin']}")
    print(f"   Detected region: {result.region_code}")
    print(f"   Detection method: {result.detection_method}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Metadata: {result.metadata}")

    # Lee, John should be classified as A1 (Anglo) due to "John" being an English given name
    if result.region_code == "A1":
        print("PASS REGIONAL BIAS FIX: PASSED - 'Lee, John' correctly classified as A1 (Anglo)")
        return True
    else:
        print(
            f"FAIL REGIONAL BIAS FIX: FAILED - 'Lee, John' classified as {result.region_code}, expected A1"
        )
        return False


@pytest.mark.timeout(15)
def test_additional_ambiguous_cases():
    """Test additional ambiguous surname cases."""
    print("\n🔍 TESTING ADDITIONAL AMBIGUOUS CASES...")

    manager = RegionManager()

    test_cases = [
        ("Kim, Michael", "A1", "Korean surname + English given name -> Anglo"),
        ("Park, Sarah", "A1", "Korean surname + English given name -> Anglo"),
        ("Kim, Jong-un", "E4", "Korean surname + Korean given name -> Korean"),
        ("Lee, Min-ho", "E4", "Korean surname + Korean given name -> Korean"),
    ]

    all_passed = True

    for name, expected_region, description in test_cases:
        result = manager.detect_region({"CanonicalLatin": name})

        if result.region_code == expected_region:
            print(f"PASS {name} -> {result.region_code} ({description})")
        else:
            print(
                f"FAIL {name} -> {result.region_code}, expected {expected_region} ({description})"
            )
            all_passed = False

    return all_passed


def main():
    """Run all verification tests."""
    print("🔥 CRITICAL FIXES VERIFICATION TEST 🔥")
    print("=" * 60)

    # Test security sanitization
    security_passed = test_security_sanitization()

    # Test regional bias fix
    bias_fix_passed = test_regional_bias_fix()

    # Test additional cases
    additional_passed = test_additional_ambiguous_cases()

    # Overall results
    print("\n" + "=" * 60)
    print("📊 VERIFICATION RESULTS:")
    print(f"   Security Sanitization: {'PASS PASSED' if security_passed else 'FAIL FAILED'}")
    print(f"   Regional Bias Fix: {'PASS PASSED' if bias_fix_passed else 'FAIL FAILED'}")
    print(f"   Additional Cases: {'PASS PASSED' if additional_passed else 'FAIL FAILED'}")

    if security_passed and bias_fix_passed and additional_passed:
        print("\n🎉 ALL CRITICAL FIXES VERIFIED! Ready for hell-level testing.")
        sys.exit(0)
    else:
        print("\n🚨 SOME FIXES FAILED! Review and fix before hell-level testing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
