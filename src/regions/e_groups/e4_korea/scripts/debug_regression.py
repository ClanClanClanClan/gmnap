#!/usr/bin/env python3
"""
Debug the math dataset regression from comprehensive fixes
"""

import yaml, sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
# from converter import eng2kor, kor2eng
import unicodedata


def norm(s):
    s = s.replace(",", "").replace("-", " ")
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))


def dice(a, b):
    a, b = set(zip(a, a[1:])), set(zip(b, b[1:]))
    return 2 * len(a & b) / (len(a) + len(b) or 1)


def find_hangul(variants):
    for v in variants:
        if isinstance(v, str) and any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


print("=== DEBUGGING MATH DATASET REGRESSION ===\n")
print("Before: 680/733 (92.77%)")
print("After:  668/733 (91.13%)")
print("Regression: -12 cases\n")

# Load test data
with open("data/korean.yaml", encoding="utf8") as f:
    data = yaml.safe_load(f)

# Find all current failures
current_failures = []
for k, v in data.items():
    if isinstance(v, dict):
        rr = v.get("CanonicalLatin")
        ko_exp = find_hangul(v.get("AllCommonVariants", []))
        if not rr or not ko_exp:
            continue

        ko = eng2kor(rr)
        if ko != ko_exp:
            current_failures.append((k, "eng→kor", rr, ko_exp, ko))
            continue

        rr2 = kor2eng(ko, rr) or ""
        if dice(norm(rr), norm(rr2)) < 0.90:
            current_failures.append((k, "roundtrip", rr, ko, rr2))

print(f"Current failures: {len(current_failures)}")

# Look for patterns in the new failures
print("\n=== ANALYZING NEW FAILURES ===")

# Group by potential causes
vowel_conflicts = []
consonant_conflicts = []
segmentation_issues = []
weight_conflicts = []

# Recently added mappings that might cause conflicts
recent_mappings = ["jung", "gun", "mook", "heu", "zy", "duk", "yo", "sun", "sin", "kun"]

problem_cases = []
for name, fail_type, input_text, expected, actual in current_failures:
    # Check if name contains recently added patterns
    input_lower = input_text.lower()
    for mapping in recent_mappings:
        if mapping in input_lower:
            problem_cases.append((name, mapping, input_text, expected, actual))
            break

print(f"Cases potentially affected by recent mappings: {len(problem_cases)}")
print("\nFirst 10:")
for name, pattern, input_text, exp, act in problem_cases[:10]:
    print(f"  {name} ('{pattern}'): {input_text}")
    print(f"    Expected: {exp}")
    print(f"    Actual: {act}")

# Check specific problematic mappings
print("\n=== SPECIFIC CONFLICT ANALYSIS ===")

# Test specific cases that might have regressed
test_cases = [
    "Kim, Hee-Sun",
    "Kim, Sun-Young",
    "Jung, Min-Ho",
    "Park, Jong-Gun",
    "Lee, Duk-Soo",
]

for case in test_cases:
    result = eng2kor(case)
    print(f"{case} → {result}")

# Check if weight conflicts are causing FST to choose wrong paths
print("\n=== WEIGHT CONFLICT ANALYSIS ===")
print("Recent mappings with their weights:")
print("- jung → 중 (weight: -0.3) - conflicts with jung → 정 (weight: -0.916)")
print("- yo → 여 (weight: -0.2) - may conflict with existing 요")
print("- gun → 건 (weight: -0.1) - new mapping")
print("- kun → 건 (weight: -0.2) - conflicts with gun → 건!")

print("\n=== RECOMMENDATION ===")
print("1. Remove conflicting mappings (jung → 중, yo → 여)")
print("2. Fix duplicate mappings (gun/kun → 건)")
print("3. Use higher weights for alternatives to avoid breaking existing cases")
print("4. Focus only on true missing mappings, not alternatives")
