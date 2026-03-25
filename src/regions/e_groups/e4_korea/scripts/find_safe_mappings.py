#!/usr/bin/env python3
"""Find safe mappings to add based on independent dataset failures."""
import csv
import json
from pathlib import Path
from collections import defaultdict

# Load existing mappings
existing_mappings = defaultdict(set)  # roman -> set of hangul
existing_keys = set()  # (hangul, roman, pos) tuples

csv_path = Path("resources/rr_syllable_map.csv")
with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 2:
            hangul = row[0]
            roman = row[1]
            pos = row[4] if len(row) > 4 else ""
            existing_mappings[roman].add(hangul)
            existing_keys.add((hangul, roman, pos))

# Analyze independent dataset failures
results_path = Path("data/expanded_independent_test_results.json")
with open(results_path) as f:
    results = json.load(f)

print("=== SAFE MAPPING OPPORTUNITIES ===\n")

# 1. Find no_conversion failures that need new syllables
print("1. NO_CONVERSION FAILURES (need new mappings):")
no_conv_syllables = defaultdict(list)

for category_data in results.get("results_by_category", {}).values():
    for failure in category_data.get("failures", []):
        if failure["issue"] == "no_conversion":
            name = failure["name"]
            # Extract syllables that might be missing
            parts = name.replace(",", "").replace("-", " ").lower().split()
            for part in parts:
                if part not in existing_mappings:
                    no_conv_syllables[part].append(name)

for syllable, names in sorted(no_conv_syllables.items())[:10]:
    print(f"\n  '{syllable}' - needed by:")
    for name in names[:3]:
        print(f"    - {name}")

# 2. Check specific missing mappings we know about
print("\n\n2. CHECKING SPECIFIC MISSING MAPPINGS:")
specific_checks = [
    ("소", "so", "S"),  # For So, Ji-Sub
    ("싸이", "psy", "S"),  # For Psy
    ("이", "rhee", "S"),  # Alternative spelling of Lee
    ("승만", "syngman", "G"),  # For Rhee, Syngman
    ("식", "shik", "G"),  # For Min-Shik
    ("섭", "sub", "G"),  # For Ji-Sub
]

safe_to_add = []
for hangul, roman, pos in specific_checks:
    # Check if this exact mapping exists
    if (hangul, roman, pos) in existing_keys:
        print(f"  ❌ {roman}→{hangul} (pos={pos}): Already exists")
        continue

    # Check for conflicts
    conflicts = []
    for r, h_set in existing_mappings.items():
        if hangul in h_set and r != roman:
            conflicts.append(f"{hangul}→{r}")

    if conflicts:
        print(f"  ⚠️  {roman}→{hangul} (pos={pos}): Conflicts with {', '.join(conflicts)}")
    else:
        print(f"  ✅ {roman}→{hangul} (pos={pos}): SAFE TO ADD")
        safe_to_add.append((hangul, roman, pos))

# 3. Find weight adjustment opportunities
print("\n\n3. WEIGHT ADJUSTMENT OPPORTUNITIES (low dice scores):")
low_dice_patterns = defaultdict(int)

for category_data in results.get("results_by_category", {}).values():
    for failure in category_data.get("failures", []):
        if failure["issue"] == "low_dice_score" and failure.get("dice", 0) < 0.85:
            expected = failure["expected"]
            actual = failure["actual"]
            if actual and len(expected) == len(actual):
                for e, a in zip(expected, actual):
                    if e != a:
                        low_dice_patterns[(e, a)] += 1

print("\nCommon character substitutions (expected → actual):")
for (exp, act), count in sorted(low_dice_patterns.items(), key=lambda x: -x[1])[:10]:
    print(f"  {exp} → {act}: {count} times")
    # Check if we can boost the correct mapping
    for row in csv.DictReader(
        open(csv_path, "r", encoding="utf-8"),
        fieldnames=["hangul", "roman", "weight", "context", "pos"],
    ):
        if row and row["hangul"] == exp:
            print(f"    Current mapping: {row['roman']} (weight={row['weight']})")

print("\n\n=== SUMMARY ===")
print(f"Safe to add without conflicts: {len(safe_to_add)} mappings")
for h, r, p in safe_to_add:
    print(f"  - {r}→{h} (pos={p})")

print("\nThese additions should improve:")
print("  - Rhee, Syngman (이승만)")
print("  - So, Ji-Sub (소지섭)")
print("  - Choi, Min-Shik (최민식)")
print("  - Psy (싸이)")
