#!/usr/bin/env python3
"""
Surgical analysis of remaining eng→kor failures for targeted fixes
"""

import yaml, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
# from converter import eng2kor
from preprocess import tokenise
from segment import segment


def find_hangul(variants):
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


# Load test data
data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))

print("=== SURGICAL ANALYSIS OF ENG→KOR FAILURES ===")

# Collect all current eng→kor failures
failures = []
for k, v in data.items():
    rr = v.get("CanonicalLatin")
    ko_exp = find_hangul(v.get("AllCommonVariants", []))
    if not rr or not ko_exp:
        continue

    ko = eng2kor(rr)
    if ko != ko_exp:
        failures.append(
            {"name": k, "input": rr, "expected": ko_exp, "got": ko, "tokens": list(tokenise(rr))}
        )

print(f"Analyzing {len(failures)} eng→kor failures")

# Categorize failures by type
categories = {
    "none_result": [],  # Complete conversion failure
    "partial_match": [],  # Some characters correct
    "systematic": [],  # Clear pattern issues
    "foreign": [],  # Foreign name elements
    "complex": [],  # Multi-issue cases
}

for f in failures:
    name = f["name"]
    input_rr = f["input"]
    expected = f["expected"]
    got = f["got"]

    if got is None:
        categories["none_result"].append(f)
    elif got == expected:
        continue  # This shouldn't happen, but just in case
    elif len(got) == len(expected):
        # Check if it's a simple character substitution
        diff_count = sum(1 for a, b in zip(got, expected) if a != b)
        if diff_count == 1:
            categories["systematic"].append(f)
        else:
            categories["partial_match"].append(f)
    else:
        # Different lengths indicate more complex issues
        if any(word in input_rr for word in ["Grace", "David", "Linda"]):
            categories["foreign"].append(f)
        else:
            categories["complex"].append(f)

print(f"\n=== FAILURE CATEGORIES ===")
for cat_name, cat_failures in categories.items():
    print(f"{cat_name}: {len(cat_failures)} cases")

# Focus on the most fixable categories first
print(f"\n=== SYSTEMATIC FAILURES (Single character differences) ===")
systematic_patterns = {}
for f in categories["systematic"]:
    got = f["got"]
    expected = f["expected"]

    # Find the differing character
    for i, (g_char, e_char) in enumerate(zip(got, expected)):
        if g_char != e_char:
            pattern = f"{g_char}→{e_char}"
            if pattern not in systematic_patterns:
                systematic_patterns[pattern] = []
            systematic_patterns[pattern].append(f)
            break

print("Most common single-character patterns:")
sorted_patterns = sorted(systematic_patterns.items(), key=lambda x: len(x[1]), reverse=True)
for pattern, cases in sorted_patterns[:10]:
    print(f"  {pattern}: {len(cases)} cases")
    for case in cases[:2]:  # Show first 2 examples
        print(f"    {case['name']}: {case['input']} → got:{case['got']} exp:{case['expected']}")

print(f"\n=== NONE RESULT FAILURES (Complete conversion failures) ===")
none_patterns = {}
for f in categories["none_result"]:
    tokens = f["tokens"]
    for token in tokens:
        segments = segment(token)
        for seg in segments:
            # Test if this segment converts
            seg_result = eng2kor(seg)
            if seg_result is None:
                if seg not in none_patterns:
                    none_patterns[seg] = []
                none_patterns[seg].append(f)

print("Most common missing segments:")
sorted_none = sorted(none_patterns.items(), key=lambda x: len(x[1]), reverse=True)
for seg, cases in sorted_none[:10]:
    print(f"  '{seg}': {len(cases)} cases")
    for case in cases[:2]:
        print(f"    {case['name']}: {case['input']}")

print(f"\n=== SURGICAL FIX RECOMMENDATIONS ===")
print("🎯 HIGH IMPACT, LOW RISK:")

# Recommend specific surgical fixes
high_impact_fixes = []

# 1. Single missing segments that appear frequently
for seg, cases in sorted_none[:5]:
    if len(cases) >= 2:  # Only if it affects multiple cases
        high_impact_fixes.append(
            {
                "type": "missing_segment",
                "segment": seg,
                "cases_affected": len(cases),
                "risk": "LOW - adds new mapping without conflicts",
            }
        )

# 2. Single character systematic patterns
for pattern, cases in sorted_patterns[:3]:
    if len(cases) >= 2:
        g_char, e_char = pattern.split("→")
        high_impact_fixes.append(
            {
                "type": "character_preference",
                "pattern": pattern,
                "cases_affected": len(cases),
                "risk": "MEDIUM - may affect roundtrip quality",
            }
        )

for i, fix in enumerate(high_impact_fixes):
    print(f"{i+1}. {fix['type']}: {fix.get('segment', fix.get('pattern'))}")
    print(f"   Impact: {fix['cases_affected']} cases")
    print(f"   Risk: {fix['risk']}")

print(
    f"\n✨ Total potential quick wins: {sum(f['cases_affected'] for f in high_impact_fixes)} cases"
)
