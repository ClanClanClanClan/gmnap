#!/usr/bin/env python3
"""
Analyze diverse dataset regression to find what broke
"""
import yaml
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from converter import eng2kor


def find_hangul(variants):
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


# Load diverse test data
data = yaml.safe_load(open("data/korean_diverse_test.yaml", encoding="utf8"))

print("=== DIVERSE DATASET ANALYSIS ===")
print(f"Total diverse test cases: {len(data)}")

failures = []
successes = []

for name_key, info in data.items():
    # Get the canonical romanization to convert
    input_name = info.get("CanonicalLatin", "")
    expected_variants = info.get("AllCommonVariants", [])

    if not input_name:
        continue

    # Convert input to Korean
    korean_result = eng2kor(input_name)

    # Check if result matches expected Hangul
    expected_hangul = find_hangul(expected_variants)

    if korean_result == expected_hangul:
        successes.append((input_name, korean_result, expected_hangul))
    else:
        failures.append((input_name, korean_result, expected_hangul))

print(f"Successes: {len(successes)}/200 ({len(successes)/2:.1f}%)")
print(f"Failures: {len(failures)}/200 ({len(failures)/2:.1f}%)")

print("\n=== FIRST 20 FAILURES ===")
for i, (input_name, got, expected) in enumerate(failures[:20]):
    print(f"{i+1:2d}. {input_name}")
    print(f"    Got: {got}")
    print(f"    Exp: {expected}")
    print()

# Look for patterns in failures
print("=== FAILURE PATTERNS ===")
surname_failures = {}
for input_name, got, expected in failures:
    if "," in input_name:
        surname = input_name.split(",")[0].strip()
        if surname not in surname_failures:
            surname_failures[surname] = []
        surname_failures[surname].append((input_name, got, expected))

sorted_surnames = sorted(surname_failures.items(), key=lambda x: len(x[1]), reverse=True)
print("Top surname failure patterns:")
for surname, surname_fails in sorted_surnames[:10]:
    print(f"\n{surname} ({len(surname_fails)} failures):")
    for input_name, got, expected in surname_fails[:3]:
        print(f"  {input_name}: got={got} exp={expected}")
