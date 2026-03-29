#!/usr/bin/env python3
"""
Investigate roundtrip failures to understand bidirectional mapping issues
"""

import sys

sys.path.append("src")
# from converter import eng2kor, kor2eng

print("=== INVESTIGATING ROUNDTRIP FAILURES ===")
print()

# Test cases from persistent failures
test_cases = [
    ("Chung, Kai-Lai", "chung kai lai"),
    ("Jeong, Min-Jeong", "jeong min jeong"),
    ("Oh, SeongJoon", "oh seongjoon"),
    ("Ri, Young-Chul", "ri young chul"),
    ("Kim, J.", "kim j"),
]

for full_name, expected_romanization in test_cases:
    print(f"=== TESTING: {full_name} ===")
    print(f"Expected roundtrip: {expected_romanization}")

    # Step 1: English → Korean
    try:
        korean_result = eng2kor(full_name)
        print(f"English → Korean: {full_name} → {korean_result}")

        if korean_result:
            # Step 2: Korean → English (roundtrip)
            try:
                roundtrip_result = kor2eng(korean_result, full_name)
                print(f"Korean → English: {korean_result} → {roundtrip_result}")

                # Compare
                if roundtrip_result:
                    roundtrip_clean = (
                        roundtrip_result.lower()
                        .replace(",", "")
                        .replace(".", "")
                        .strip()
                    )
                    expected_clean = (
                        expected_romanization.lower()
                        .replace(",", "")
                        .replace(".", "")
                        .strip()
                    )

                    if roundtrip_clean == expected_clean:
                        print("✅ ROUNDTRIP SUCCESS")
                    else:
                        print(f"❌ ROUNDTRIP FAILURE")
                        print(f"   Expected: '{expected_clean}'")
                        print(f"   Actual:   '{roundtrip_clean}'")

                        # Analyze differences
                        expected_parts = expected_clean.split()
                        actual_parts = roundtrip_clean.split()
                        for i, (exp, act) in enumerate(
                            zip(expected_parts, actual_parts)
                        ):
                            if exp != act:
                                print(f"   Diff[{i}]: '{exp}' ≠ '{act}'")
                else:
                    print("❌ Korean → English failed")
            except Exception as e:
                print(f"❌ Korean → English error: {e}")
        else:
            print("❌ English → Korean failed")
    except Exception as e:
        print(f"❌ English → Korean error: {e}")

    print()

print("=== ANALYSIS COMPLETE ===")
print("Look for systematic patterns in the roundtrip differences")
print("This will reveal which Korean→English mappings need adjustment")
