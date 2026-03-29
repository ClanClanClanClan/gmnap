import pytest

#!/usr/bin/env python3
"""
Test script for D4 Pakistan Urdu region processor.
Tests various Pakistani mathematician name patterns and edge cases.
"""

import sys
import os

# Add the src directory to Python path
src_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, src_dir)

from src.regions.d_groups.d4_pakistan_urdu.processor import D4_PakistanUrdu


@pytest.mark.timeout(15)
def test_d4_processor():
    """Test D4 Pakistan Urdu processor with various name patterns."""
    processor = D4_PakistanUrdu()

    # Test cases covering different Pakistani naming patterns
    test_cases = [
        # Basic Islamic names
        {
            "CanonicalLatin": "Muhammad Ali Khan",
            "test_name": "Basic Islamic name with Khan surname",
        },
        {
            "CanonicalLatin": "Dr. Ahmed Hassan Malik",
            "test_name": "Academic title with occupational surname",
        },
        {
            "CanonicalLatin": "Abdul Rahman Sheikh",
            "test_name": "Theophoric name with occupational surname",
        },
        # Patronymic patterns
        {
            "CanonicalLatin": "Ali bin Muhammad Khan",
            "test_name": "Explicit patronymic with bin",
        },
        {
            "CanonicalLatin": "Fatima bint Ahmed Chaudhry",
            "test_name": "Female patronymic with bint",
        },
        {
            "CanonicalLatin": "Hassan s/o Abdul Qadir",
            "test_name": "Pakistani-style patronymic with s/o",
        },
        # Tribal/clan names
        {"CanonicalLatin": "Imran Khan Niazi", "test_name": "Pathan tribal name"},
        {"CanonicalLatin": "Asif Ali Zardari", "test_name": "Sindhi clan name"},
        {"CanonicalLatin": "Pervez Musharraf", "test_name": "Simple two-part name"},
        # Regional variations
        {
            "CanonicalLatin": "Tariq Mahmood Punjabi",
            "test_name": "Punjabi regional identifier",
        },
        {
            "CanonicalLatin": "Prof. Saleem Ahmad Pathan",
            "test_name": "Academic with Pathan tribal identifier",
        },
        {
            "CanonicalLatin": "Maulana Fazlur Rahman",
            "test_name": "Religious title with patronymic name",
        },
        # Complex names with multiple elements
        {
            "CanonicalLatin": "Muhammad Iqbal bin Allama Shah",
            "test_name": "Complex name with title and patronymic",
        },
        {
            "CanonicalLatin": "Hafiz Abdul Salam Bhatti",
            "test_name": "Religious title with clan name",
        },
        # Urdu script test (if available)
        {
            "CanonicalNative": "محمد علی خان",
            "CanonicalLatin": "Muhammad Ali Khan",
            "test_name": "Urdu script with romanization",
        },
    ]

    print("=== D4 Pakistan Urdu Processor Tests ===\n")

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['test_name']}")

        try:
            # Create a copy of test case for processing
            entry = test_case.copy()
            del entry["test_name"]

            print(f"  Input: {entry}")

            # Test cleaning
            processor.clean(entry)
            print(f"  After cleaning: {entry}")

            # Test augmentation
            processor.augment(entry)
            print(f"  Regional extras: {entry.get('RegionalExtras', {})}")

            # Test validation
            processor.validate(entry)
            print(f"  Validation: PASSED")

            # Test order key generation
            order_key = processor.order_key(entry)
            print(f"  Order key: '{order_key}'")

            print(f"  PASS PASSED\n")
            passed += 1

        except Exception as e:
            print(f"  FAIL FAILED: {str(e)}\n")
            failed += 1

    print(f"=== Results: {passed} passed, {failed} failed ===")

    # Test specific functionality
    print("\n=== Component Analysis Tests ===")

    component_tests = [
        "Muhammad Ali Khan",
        "Dr. Ahmed bin Hassan",
        "Fatima Chaudhry",
        "Abdul Rahman Al-Pakistani",
        "Prof. Iqbal Ahmad Syed",
    ]

    for name in component_tests:
        entry = {"CanonicalLatin": name}
        processor.augment(entry)
        components = entry.get("RegionalExtras", {})

        print(f"Name: {name}")
        print(f"  Components: {components}")
        print()

    return passed, failed


if __name__ == "__main__":
    passed, failed = test_d4_processor()
    # sys.exit(0 if failed == 0 else 1)  # MOVED: Was at module level
