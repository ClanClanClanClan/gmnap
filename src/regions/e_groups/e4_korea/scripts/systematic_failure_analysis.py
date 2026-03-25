#!/usr/bin/env python3
"""
ULTRACHECK: Systematic failure pattern analysis to identify architectural improvements
Look for consistent patterns that indicate structural issues, not individual cases
"""
import sys

sys.path.append("src")
from converter import eng2kor, kor2eng
import re

print("=== SYSTEMATIC FAILURE PATTERN ANALYSIS ===")
print("Focus: Identify architectural issues, not individual case fixes")
print("Goal: Find systematic improvements without overfitting")
print()

# Load sample of validation failures to analyze patterns
validation_failures = [
    "Park_JungYun → pak jung yun",
    "Kim_RareInitialsBlock → eng→kor failure",
    "Baik_Junghyun → baik jeong hyun",
    "Huh_June → huh jun lee",
    "Um_Jungmin → eng→kor failure",
]

print("=== PATTERN ANALYSIS ===")

# Pattern 1: Surname romanization inconsistencies
surname_issues = []
# Pattern 2: English→Korean conversion failures
eng2kor_failures = []
# Pattern 3: Compound vs character-by-character conflicts
compound_issues = []
# Pattern 4: Context sensitivity problems
context_issues = []

for failure in validation_failures:
    if "eng→kor" in failure:
        eng2kor_failures.append(failure)
        print(f"ENG→KOR FAILURE: {failure}")
    elif "→" in failure:
        name_part = failure.split("→")[0].strip()
        expected_part = failure.split("→")[1].strip()

        # Test the actual conversion
        if ", " in name_part:
            surname, given = name_part.split(", ")
        else:
            surname = name_part.split("_")[0]
            given = name_part.split("_")[1] if "_" in name_part else ""

        test_name = f"{surname}, {given}" if given else surname

        korean_result = eng2kor(test_name)
        if korean_result:
            roundtrip_result = kor2eng(korean_result, test_name)
            if roundtrip_result:
                print(f"ROUNDTRIP ANALYSIS: {test_name}")
                print(f"  Korean: {korean_result}")
                print(f"  Expected: {expected_part}")
                print(f"  Actual: {roundtrip_result}")

                # Identify pattern type
                if roundtrip_result.split()[0] != expected_part.split()[0]:
                    surname_issues.append(
                        (surname, roundtrip_result.split()[0], expected_part.split()[0])
                    )
                    print(f"  → SURNAME PATTERN: {surname}")

                if len(roundtrip_result.split()) != len(expected_part.split()):
                    compound_issues.append((test_name, "segmentation mismatch"))
                    print(f"  → COMPOUND PATTERN: segmentation")

print(f"\n=== SYSTEMATIC PATTERNS IDENTIFIED ===")
print(f"1. Surname romanization issues: {len(set(surname_issues))}")
print(f"2. English→Korean failures: {len(eng2kor_failures)}")
print(f"3. Compound segmentation issues: {len(compound_issues)}")

print(f"\n=== ARCHITECTURAL ISSUES DISCOVERED ===")

# Check for systematic English→Korean issues
print("English→Korean failure analysis:")
for failure in eng2kor_failures:
    test_name = failure.split("→")[0].strip().replace("_", ", ")
    result = eng2kor(test_name)
    print(f"  {test_name} → {result}")

    if result is None:
        print(f"    → MISSING MAPPING in rom2han FST")
    else:
        print(f"    → Conversion works, validation issue?")

print(f"\n=== SYSTEMATIC IMPROVEMENTS NEEDED ===")
print("1. FST Coverage Analysis: Missing rom2han mappings")
print("2. Surname Context Logic: Systematic surname preference rules")
print("3. Compound Processing: Better tokenization vs character-by-char balance")
print("4. Validation Logic: Check for validation script inconsistencies")

print(f"\n=== NON-OVERFITTING SOLUTIONS ===")
print("Focus on:")
print("- Missing character mappings in FST (coverage gaps)")
print("- Systematic context rules (not individual weights)")
print("- Compound detection algorithms (not hardcoded compounds)")
print("- Validation methodology improvements")
