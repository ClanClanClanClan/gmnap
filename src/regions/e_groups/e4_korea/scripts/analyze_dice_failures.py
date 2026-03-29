#!/usr/bin/env python3
"""Analyze low dice score failures to find weight adjustment opportunities."""

import csv
import json
from collections import Counter, defaultdict

# Load failures
with open("data/expanded_independent_test_results.json") as f:
    data = json.load(f)

# Focus on low dice score failures
dice_failures = [f for f in data["failures"] if f["issue"] == "low_dice_score"]
print(f"Analyzing {len(dice_failures)} low dice score failures\n")

# Analyze character-level differences
char_substitutions = Counter()
for f in dice_failures:
    expected = f["expected"]
    actual = f["actual"]
    if actual and len(expected) == len(actual):
        for e, a in zip(expected, actual):
            if e != a:
                char_substitutions[(e, a)] += 1

print("=== TOP CHARACTER SUBSTITUTIONS ===")
print("(Expected → Actual : Count)")
for (exp, act), count in char_substitutions.most_common(10):
    print(f"{exp} → {act} : {count} times")

# Check current mappings for these characters
print("\n=== CHECKING CURRENT MAPPINGS ===")
mappings = defaultdict(list)
with open("resources/rr_syllable_map.csv", "r", encoding="utf-8") as f:
    for row in csv.reader(f):
        if len(row) >= 2 and not row[0].startswith("#"):
            hangul = row[0]
            roman = row[1]
            weight = float(row[2]) if len(row) > 2 and row[2] else 0.0
            pos = row[4] if len(row) > 4 else ""
            mappings[hangul].append((roman, weight, pos))

# For top substitutions, check what mappings exist
top_errors = [exp for (exp, act), count in char_substitutions.most_common(5)]
for hangul in top_errors:
    if hangul in mappings:
        print(f"\n{hangul} has mappings:")
        for roman, weight, pos in sorted(mappings[hangul], key=lambda x: -x[1]):
            pos_desc = pos or "general"
            print(f"  {roman} (weight={weight}, pos={pos_desc})")

# Specific examples
print("\n=== SPECIFIC FAILURE EXAMPLES ===")
for f in dice_failures[:5]:
    print(f"\n{f['name']}: {f['expected']} → {f['actual']} (dice={f['dice']:.3f})")

    # Show character differences
    if f["actual"] and len(f["expected"]) == len(f["actual"]):
        diffs = []
        for i, (e, a) in enumerate(zip(f["expected"], f["actual"])):
            if e != a:
                diffs.append(f"position {i}: {e}→{a}")
        if diffs:
            print(f"  Differences: {', '.join(diffs)}")

print("\n\n=== WEIGHT ADJUSTMENT RECOMMENDATIONS ===")
print("Based on the analysis, we could:")
print("1. Boost weights for correct mappings that are being overridden")
print("2. Lower weights for mappings causing incorrect substitutions")
print("3. Add position-specific higher-weight variants for problematic characters")
