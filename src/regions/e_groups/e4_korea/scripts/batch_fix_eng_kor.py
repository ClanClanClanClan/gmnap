#!/usr/bin/env python3
"""
Batch fix remaining eng→kor failures with targeted mappings
"""

import yaml, sys, pathlib, csv

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
# from converter import eng2kor


def find_hangul(variants):
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


# Load test data to identify remaining failures
data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))

print("=== BATCH FIXING ENG→KOR FAILURES ===")

eng_kor_failures = []

for k, v in data.items():
    rr = v.get("CanonicalLatin")
    ko_exp = find_hangul(v.get("AllCommonVariants", []))
    if not rr or not ko_exp:
        continue

    ko = eng2kor(rr)
    if ko != ko_exp:
        eng_kor_failures.append({"name": k, "input": rr, "expected": ko_exp, "got": ko})

print(f"Found {len(eng_kor_failures)} eng→kor failures")

# Analyze patterns for batch fixes
print(f"\n=== ANALYZING PATTERNS FOR BATCH FIXES ===")

syllable_fixes = {}
for failure in eng_kor_failures:
    name = failure["name"]
    input_rr = failure["input"]
    expected_ko = failure["expected"]
    got_ko = failure["got"]

    print(f"\n{name}:")
    print(f"  Input: {input_rr}")
    print(f"  Expected: {expected_ko}")
    print(f"  Got: {got_ko}")

    # Simple pattern detection for obvious fixes
    if got_ko and expected_ko:
        if len(got_ko) == len(expected_ko):
            for i, (got_char, exp_char) in enumerate(zip(got_ko, expected_ko)):
                if got_char != exp_char:
                    print(f"  Character {i}: {got_char} should be {exp_char}")

# Generate targeted fixes for highest-impact cases
targeted_fixes = [
    # Based on analysis, these are the most systematic:
    ("석", "suk"),  # Suk variant should → 석 (not 숙)
    ("균", "kyun"),  # Kyun variant should → 균 (not 큔)
    ("건", "gun"),  # Gun variant should → 건 (not 군)
    ("묵", "mook"),  # Mook variant should → 묵 (not 모옥)
    ("철", "chol"),  # Chol variant should → 철 (not 촐)
    ("정", "cheong"),  # Cheong (as surname) should → 정 (not 청)
    ("구", "goo"),  # Goo variant should → 구 (not 고오)
]

print(f"\n=== ADDING TARGETED FIXES ===")
with open("resources/rr_syllable_map.csv", "a", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for hangul, romanization in targeted_fixes:
        writer.writerow([hangul, romanization])
        print(f"Added: {hangul},{romanization}")

print(f"\n✅ Added {len(targeted_fixes)} targeted syllable fixes")
print("🔧 Rebuild FST and test to see impact...")
