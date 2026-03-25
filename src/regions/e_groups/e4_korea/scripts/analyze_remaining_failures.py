#!/usr/bin/env python3
"""
Analyze the remaining 44 failures at 689/733 to identify patterns for final +10 cases
"""
import sys

sys.path.append("src")
from converter import eng2kor, kor2eng

print("=== ANALYZING REMAINING 44 FAILURES FOR FINAL PUSH ===")
print("Current: 689/733 (94.00%)")
print("Target: 699/733 (95.4%) - need +10 cases")
print()

# Sample the new failure patterns from validation output
new_failure_patterns = [
    ("Kim, J.", "kim j"),  # initials issue
    ("Lee, Hyeon-Jeong", "lee hyeon jeong"),  # surname preference
    ("Yi, Soo-Young", "yi soo young"),  # surname preference
    ("Ri, Young-Chul", "ri young chul"),  # surname preference
    ("Huh, June", "huh june"),  # surname + given name
]

print("Testing new failure patterns:")
for full_name, expected_romanization in new_failure_patterns:
    print(f"\n=== {full_name} ===")

    # Test roundtrip
    korean_result = eng2kor(full_name)
    if korean_result:
        roundtrip_result = kor2eng(korean_result, full_name)
        if roundtrip_result:
            roundtrip_clean = roundtrip_result.lower().replace(",", "").replace(".", "").strip()
            expected_clean = expected_romanization.lower().replace(",", "").replace(".", "").strip()

            print(f"Korean: {korean_result}")
            print(f"Expected: {expected_clean}")
            print(f"Actual:   {roundtrip_clean}")

            if roundtrip_clean != expected_clean:
                # Analyze specific differences
                exp_parts = expected_clean.split()
                act_parts = roundtrip_clean.split()

                for i, (exp, act) in enumerate(zip(exp_parts, act_parts)):
                    if exp != act:
                        print(f"  Issue[{i}]: '{exp}' ≠ '{act}'")

                        # Identify character mapping issues
                        if i == 0:  # Surname
                            print(f"    → Surname mapping issue")
                        else:  # Given name
                            print(f"    → Given name mapping issue")
            else:
                print("✅ This case actually works now!")

print("\n=== PATTERN ANALYSIS ===")
print("Main remaining issues:")
print("1. Surname romanization preferences (Lee/Yi/Ri confusion)")
print("2. Character-by-character vs compound processing")
print("3. Context-sensitive surname vs given name mappings")
print("\nStrategy: Fine-tune character weights for these specific patterns")
print("Focus on most common surname conflicts and given name mappings")
