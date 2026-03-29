#!/usr/bin/env python3
"""
Analyze the exact 39 failures at 80.50% accuracy
This will show patterns and suggest targeted fixes
"""

import yaml
import sys

sys.path.append("src")
from converter import eng2kor
from collections import Counter, defaultdict


def load_diverse_data():
    """Load the diverse test dataset"""
    with open("data/korean_diverse_test.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_hangul(variants):
    """Extract Hangul from variants"""
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


def analyze_failures():
    """Analyze all failures in detail"""
    data = load_diverse_data()

    failures = []
    for name, info in data.items():
        # Get expected Hangul
        expected = find_hangul(info.get("AllCommonVariants", []))
        if not expected:
            continue

        # Get canonical Latin
        canonical = info.get("CanonicalLatin", "")
        if not canonical:
            variants = info.get("AllCommonVariants", [])
            # Find a Latin variant
            for v in variants:
                if not any("\uac00" <= c <= "\ud7af" for c in v):
                    canonical = v
                    break

        if not canonical:
            continue

        # Test conversion
        result = eng2kor(canonical)

        if result != expected:
            # Analyze character differences
            char_diffs = []
            if result:
                for i, (e, g) in enumerate(zip(expected, result)):
                    if e != g:
                        char_diffs.append((i, e, g))

            failures.append(
                {
                    "name": name,
                    "input": canonical,
                    "expected": expected,
                    "got": result,
                    "char_diffs": char_diffs,
                    "category": info.get("comment", "Unknown"),
                }
            )

    return failures


def suggest_fixes(failures):
    """Suggest specific fixes based on failure patterns"""
    # Count character substitutions
    char_subs = Counter()
    position_subs = defaultdict(Counter)

    for f in failures:
        for pos, exp, got in f["char_diffs"]:
            char_subs[f"{exp}→{got}"] += 1
            position_subs[pos][f"{exp}→{got}"] += 1

    # Analyze romanization patterns
    roman_patterns = defaultdict(list)
    for f in failures:
        if f["got"]:  # Only if we got some result
            # Try to identify which romanization caused the issue
            input_parts = f["input"].lower().replace(",", "").replace("-", " ").split()
            for part in input_parts:
                for pos, exp, got in f["char_diffs"]:
                    roman_patterns[part].append((exp, got, f["name"]))

    return char_subs, position_subs, roman_patterns


def main():
    print("=== Analyzing 39 Failures at 80.50% Accuracy ===\n")

    failures = analyze_failures()
    print(f"Total failures found: {len(failures)}")

    # Group by category
    by_category = defaultdict(list)
    for f in failures:
        by_category[f["category"]].append(f)

    print("\nFailures by category:")
    for cat, fails in sorted(
        by_category.items(), key=lambda x: len(x[1]), reverse=True
    ):
        print(f"  {cat}: {len(fails)} failures")

    # Analyze patterns
    char_subs, pos_subs, roman_patterns = suggest_fixes(failures)

    print("\n=== Most Common Character Substitutions ===")
    for sub, count in char_subs.most_common(15):
        print(f"  {sub}: {count} occurrences")

    print("\n=== Position-Specific Patterns ===")
    for pos in sorted(pos_subs.keys()):
        print(f"\nPosition {pos}:")
        for sub, count in pos_subs[pos].most_common(3):
            print(f"  {sub}: {count} times")

    print("\n=== Romanization Pattern Analysis ===")
    # Find high-impact romanizations
    impact_romans = []
    for roman, issues in roman_patterns.items():
        unique_subs = set((exp, got) for exp, got, _ in issues)
        if len(issues) >= 2:  # Affects multiple names
            impact_romans.append((roman, len(issues), unique_subs, issues))

    for roman, count, subs, issues in sorted(
        impact_romans, key=lambda x: x[1], reverse=True
    )[:10]:
        print(f"\n'{roman}' affects {count} names:")
        for sub in subs:
            print(f"  Causes {sub[0]}→{sub[1]}")
        print(f"  Examples: {', '.join(set(name for _, _, name in issues[:3]))}")

    print("\n=== Specific Fixes to Try ===")
    print("\n1. High-confidence single syllable fixes:")

    # Identify clear patterns
    clear_fixes = []
    for roman, issues in roman_patterns.items():
        subs = [(exp, got) for exp, got, _ in issues]
        # If all occurrences have the same substitution
        if len(set(subs)) == 1 and len(issues) >= 2:
            exp, got = subs[0]
            clear_fixes.append((roman, exp, got, len(issues)))

    for roman, exp, got, count in sorted(clear_fixes, key=lambda x: x[3], reverse=True):
        print(f"  '{roman}' → {exp} (currently → {got}) - affects {count} names")
        print(f"    echo '{exp},{roman}' >> resources/rr_syllable_map.csv")

    print("\n2. Compound mapping suggestions:")
    # Find common two-syllable patterns
    compound_patterns = defaultdict(list)
    for f in failures:
        input_lower = (
            f["input"].lower().replace(",", "").replace("-", "").replace(" ", "")
        )
        if f["expected"] and len(f["expected"]) >= 2:
            # Look for two-syllable patterns
            for i in range(len(input_lower) - 1):
                two_syl = input_lower[i : i + 4]  # Rough estimate
                if len(two_syl) >= 3:
                    compound_patterns[two_syl].append(f["expected"])

    print("\n=== Sample Failures for Manual Review ===")
    for i, f in enumerate(failures[:10]):
        print(f"\n{i+1}. {f['name']}:")
        print(f"   Input: {f['input']}")
        print(f"   Expected: {f['expected']}")
        print(f"   Got: {f['got']}")
        if f["char_diffs"]:
            print(
                f"   Differences: {', '.join(f'{e}→{g}' for _, e, g in f['char_diffs'])}"
            )


if __name__ == "__main__":
    main()
