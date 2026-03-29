#!/usr/bin/env python3
"""
Analyze roundtrip quality issues and their patterns
"""

import pathlib
import sys
import unicodedata

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
# from converter import eng2kor, kor2eng


def norm(s):
    s = s.replace(",", "").replace("-", " ")
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))


def dice(a, b):
    a, b = set(zip(a, a[1:])), set(zip(b, b[1:]))
    return 2 * len(a & b) / (len(a) + len(b) or 1)


def find_hangul(variants):
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


# Load test data
data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))

print("=== ROUNDTRIP QUALITY ANALYSIS ===")

roundtrip_issues = []

for k, v in data.items():
    rr = v.get("CanonicalLatin")
    ko_exp = find_hangul(v.get("AllCommonVariants", []))
    if not rr or not ko_exp:
        continue

    ko = eng2kor(rr)
    if ko != ko_exp:
        continue  # Skip eng→kor failures, focus on roundtrip

    # Check roundtrip quality
    rr2 = kor2eng(ko, rr) or ""
    dice_score = dice(norm(rr), norm(rr2))

    if dice_score < 0.97:
        roundtrip_issues.append(
            {"name": k, "input": rr, "korean": ko, "output": rr2, "dice": dice_score}
        )

# Sort by dice score (worst first)
roundtrip_issues.sort(key=lambda x: x["dice"])

print(f"Total roundtrip issues: {len(roundtrip_issues)}")
print("\n=== WORST ROUNDTRIP CASES (Top 15) ===")

for i, issue in enumerate(roundtrip_issues[:15]):
    print(f"{i+1:2d}. {issue['name']} (dice: {issue['dice']:.3f})")
    print(f"    {issue['input']} → {issue['korean']} → {issue['output']}")

    # Analyze the differences
    input_parts = issue["input"].lower().replace(",", "").replace("-", " ").split()
    output_parts = issue["output"].lower().split() if issue["output"] else []

    differences = []
    for j, (inp, out) in enumerate(zip(input_parts, output_parts)):
        if inp != out:
            differences.append(f"{inp}→{out}")

    if differences:
        print(f"    Differences: {', '.join(differences)}")
    print()

# Analyze patterns
print("=== ROUNDTRIP ISSUE PATTERNS ===")
romanization_changes = {}
for issue in roundtrip_issues:
    input_parts = issue["input"].lower().replace(",", "").replace("-", " ").split()
    output_parts = issue["output"].lower().split() if issue["output"] else []

    for inp, out in zip(input_parts, output_parts):
        if inp != out:
            change = f"{inp}→{out}"
            if change not in romanization_changes:
                romanization_changes[change] = 0
            romanization_changes[change] += 1

# Sort by frequency
sorted_changes = sorted(romanization_changes.items(), key=lambda x: x[1], reverse=True)
print("Most common romanization changes:")
for change, count in sorted_changes[:10]:
    print(f"  {change}: {count} occurrences")
