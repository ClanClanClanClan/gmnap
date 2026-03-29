#!/usr/bin/env python3
"""
Investigate the new surname failure patterns revealed after FST fixes
"""

import sys

sys.path.append("src")
# from converter import eng2kor, kor2eng

print("=== INVESTIGATING NEW SURNAME FAILURES ===")
print("Post-FST fix failures - all surname romanization issues")
print()

# Test cases from new failure patterns
surname_cases = [
    ("Rhee, Dong-Won", "rhee dong won"),
    ("Pak, Hyeong-Ju", "pak hyeong ju"),
    ("You, Soojin", "you soojin"),
    ("Gu, Yeonju", "gu yeonju"),
    ("Kim, J.", "kim j"),
]

for full_name, expected_romanization in surname_cases:
    print(f"=== TESTING: {full_name} ===")
    print(f"Expected roundtrip: {expected_romanization}")

    # Step 1: English → Korean
    korean_result = eng2kor(full_name)
    print(f"English → Korean: {full_name} → {korean_result}")

    if korean_result:
        # Step 2: Korean → English (roundtrip)
        roundtrip_result = kor2eng(korean_result, full_name)
        print(f"Korean → English: {korean_result} → {roundtrip_result}")

        if roundtrip_result:
            roundtrip_clean = (
                roundtrip_result.lower().replace(",", "").replace(".", "").strip()
            )
            expected_clean = (
                expected_romanization.lower().replace(",", "").replace(".", "").strip()
            )

            if roundtrip_clean == expected_clean:
                print("✅ ROUNDTRIP SUCCESS")
            else:
                print(f"❌ ROUNDTRIP FAILURE")
                print(f"   Expected: '{expected_clean}'")
                print(f"   Actual:   '{roundtrip_clean}'")

                # Analyze surname issue specifically
                exp_parts = expected_clean.split()
                act_parts = roundtrip_clean.split()
                if len(exp_parts) > 0 and len(act_parts) > 0:
                    surname_exp = exp_parts[0]
                    surname_act = act_parts[0]
                    if surname_exp != surname_act:
                        print(f"   SURNAME ISSUE: '{surname_exp}' ≠ '{surname_act}'")
        else:
            print("❌ Korean → English failed")
    else:
        print("❌ English → Korean failed")
    print()

print("=== SURNAME MAPPING ANALYSIS ===")
print("Need to check Korean → English surname preferences:")
print("- What Korean character maps to 'rhee' vs 'ee'?")
print("- What Korean character maps to 'pak' vs 'park'?")
print("- What Korean character maps to 'you' vs 'yu'?")
print("- What Korean character maps to 'gu' vs 'goo'?")
