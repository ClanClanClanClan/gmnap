#!/usr/bin/env python3
"""
Analyze which cases were fixed by Patch B weighted FST
"""
import yaml, sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from converter import eng2kor, kor2eng

# Load test data
with open("data/korean.yaml", encoding="utf8") as f:
    data = yaml.safe_load(f)

# Track improvements
fixed_cases = []
still_failing = []

print("=== ANALYZING PATCH B IMPROVEMENTS ===")
print(f"Testing all {len(data)} cases to find the +10 improvements...\n")

for name, info in data.items():
    if isinstance(info, dict) and "CJK" in info:
        romanized = name.replace("_", ", ")
        actual = eng2kor(romanized)

        if actual:
            roundtrip = kor2eng(actual)

            # Check if this case is now passing
            if (
                roundtrip
                and roundtrip.replace(" ", "").lower()
                == romanized.replace(", ", "").replace(" ", "").lower()
            ):
                # This is a passing case - check if it's one of the improvements
                # (We'd need baseline data to know for sure, but let's check key patterns)
                if any(
                    pattern in name.lower()
                    for pattern in ["cheong", "jeong", "jung", "min", "ho", "jin"]
                ):
                    fixed_cases.append((name, romanized, actual, roundtrip))
        else:
            still_failing.append((name, "eng→kor failed"))

# Print summary of likely improvements
print("=== LIKELY IMPROVEMENTS FROM WEIGHTED FST ===")
print("Cases with weighted syllables that may have improved:\n")

count = 0
for name, rom, kor, rt in sorted(fixed_cases):
    if count < 15:  # Show first 15
        print(f"{name}: {rom} → {kor} → {rt} ✅")
        count += 1

print(f"\nTotal cases with weighted syllables passing: {len(fixed_cases)}")
print(f"Cases still failing eng→kor: {len(still_failing)}")

# Check specific weighted patterns
print("\n=== WEIGHTED PATTERN ANALYSIS ===")
weighted_patterns = {
    "kim": 0,
    "lee": 0,
    "park": 0,
    "jung": 0,
    "jeong": 0,
    "min": 0,
    "ho": 0,
    "jin": 0,
    "jun": 0,
    "cheong": 0,
}

for name in data:
    rom = name.replace("_", ", ")
    actual = eng2kor(rom)
    if actual:
        for pattern in weighted_patterns:
            if pattern in rom.lower():
                weighted_patterns[pattern] += 1

print("Success count for weighted patterns:")
for pattern, count in sorted(weighted_patterns.items(), key=lambda x: -x[1]):
    if count > 0:
        print(f"  {pattern}: {count} cases")
