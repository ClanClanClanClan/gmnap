#!/usr/bin/env python3
"""
Deep analysis of diverse dataset romanization patterns
"""

import yaml, sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
# from converter import eng2kor, kor2eng

print("=== DIVERSE DATASET PATTERN ANALYSIS ===\n")

with open("data/korean_diverse_test.yaml", encoding="utf8") as f:
    diverse_data = yaml.safe_load(f)


def find_hangul(variants):
    for v in variants:
        if isinstance(v, str) and any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


# Analyze romanization patterns in diverse dataset
print("1. ROMANIZATION PATTERN ANALYSIS")
patterns = {}
vowel_issues = []
consonant_issues = []
length_issues = []
segmentation_issues = []

for name, info in diverse_data.items():
    rom = name.replace("_", ", ")
    expected = find_hangul(info.get("AllCommonVariants", []))
    actual = eng2kor(rom)

    if not expected:
        continue

    if actual != expected:
        # Analyze the specific issue
        if actual is None:
            patterns.setdefault("None_failures", []).append((name, rom, expected))
        elif len(actual) != len(expected):
            length_issues.append(
                (name, rom, expected, actual, len(expected), len(actual))
            )
        else:
            # Character-by-character analysis
            for i, (exp_char, act_char) in enumerate(zip(expected, actual)):
                if exp_char != act_char:
                    issue = f"{act_char}→{exp_char}"
                    patterns.setdefault(f"char_sub_{i}", []).append((name, issue, rom))

                    # Check if it's a vowel issue
                    vowels = [
                        "ㅏ",
                        "ㅓ",
                        "ㅗ",
                        "ㅜ",
                        "ㅡ",
                        "ㅣ",
                        "ㅑ",
                        "ㅕ",
                        "ㅛ",
                        "ㅠ",
                    ]
                    if any(v in exp_char for v in vowels) or any(
                        v in act_char for v in vowels
                    ):
                        vowel_issues.append((name, rom, exp_char, act_char, i))

print("2. CRITICAL MISSING SYLLABLES")
none_failures = []
for name, info in diverse_data.items():
    rom = name.replace("_", ", ")
    expected = find_hangul(info.get("AllCommonVariants", []))
    actual = eng2kor(rom)

    if actual is None and expected:
        none_failures.append((name, rom, expected))

print(f"Total None failures: {len(none_failures)}")
print("First 10:")
for name, rom, exp in none_failures[:10]:
    print(f"  {rom} → None (should be {exp})")

# Extract specific syllables that are missing
missing_syllables = set()
for name, rom, expected in none_failures:
    # Try to identify which part caused the None
    parts = rom.split(", ")
    for part in parts:
        if eng2kor(part) is None:
            missing_syllables.add(part.lower())

print(f"\nMissing syllable patterns: {sorted(missing_syllables)}")

print("\n3. VOWEL MAPPING ISSUES")
print(f"Total vowel issues: {len(vowel_issues)}")
vowel_map = {}
for name, rom, exp_char, act_char, pos in vowel_issues[:20]:
    key = f"{act_char}→{exp_char}"
    vowel_map.setdefault(key, []).append(name)

for issue, names in sorted(vowel_map.items()):
    print(f"  {issue}: {len(names)} cases ({names[0] if names else ''})")

print("\n4. LENGTH MISMATCH ANALYSIS")
print(f"Total length issues: {len(length_issues)}")
for name, rom, expected, actual, exp_len, act_len in length_issues[:10]:
    print(f"  {name}: {rom}")
    print(f"    Expected: {expected} ({exp_len} chars)")
    print(f"    Actual: {actual} ({act_len} chars)")

    # Try to identify segmentation issues
    if act_len > exp_len:
        print(f"    Issue: Over-segmentation")
    else:
        print(f"    Issue: Under-segmentation")

# Specific pattern extraction for fixes
print("\n5. TARGETED FIXES NEEDED")

# Common romanization variants in diverse dataset
diverse_patterns = [
    "yuna",
    "heui",
    "suzy",
    "duksoo",
    "yojong",
    "sunsin",
    "sejong",
    "junggeun",
    "kunhee",
    "gildong",
    "chunhyang",
    "yeongja",
]

print("Missing patterns that need mapping:")
for pattern in diverse_patterns:
    if eng2kor(pattern) is None:
        print(f"  {pattern} → missing")
    else:
        result = eng2kor(pattern)
        print(f"  {pattern} → {result} (exists)")

# Check if diverse dataset uses different romanization system
print("\n6. ROMANIZATION SYSTEM DIFFERENCES")
print("Diverse dataset may use different conventions:")
print("- McCune-Reischauer vs Revised Romanization")
print("- Different vowel representations (yu vs yoo, eu vs eo)")
print("- Different consonant representations (k vs g, p vs b)")
