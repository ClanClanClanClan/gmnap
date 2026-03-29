#!/usr/bin/env python3
"""
Analyze Diverse failures to find safe improvement patterns
that won't break Math or Independent performance
"""

# Current Diverse failures from the analysis
diverse_failures = [
    {"name": "Lee, Chung-Wei", "expected": "이청위", "actual": "이정위", "issue": "청→정"},
    {"name": "Han, Duk-Su", "expected": "한덕수", "actual": "한둑수", "issue": "덕→둑"},
    {"name": "Kim, Yo-Jong", "expected": "김여정", "actual": "김요종", "issue": "여→요"},
    {"name": "Yi, Sun-Sin", "expected": "이순신", "actual": "이선신", "issue": "순→선"},
    {"name": "An, Jung-Geun", "expected": "안중근", "actual": "안정근", "issue": "중→정"},
    {"name": "Lee, Kun-Hee", "expected": "이건희", "actual": "이쿤희", "issue": "건→쿤"},
    {"name": "Shim, Chang-Min", "expected": "심창민", "actual": "심장민", "issue": "창→장"},
    {"name": "Han, Joseph", "expected": "한요셉", "actual": "한조셉", "issue": "요→조"},
    {"name": "Lee, Chun-Hyang", "expected": "이춘향", "actual": "이전향", "issue": "춘→전"},
    {"name": "Kang, Jin-Jung", "expected": "강진중", "actual": "강진정", "issue": "중→정"},
]

print("=== DIVERSE FAILURE ANALYSIS ===")
print(f"Total failures to fix: {len(diverse_failures)}")
print()

# Analyze patterns
given_name_patterns = {}
character_substitutions = {}

for failure in diverse_failures:
    name_parts = failure["name"].split(", ")
    if len(name_parts) == 2:
        surname, given = name_parts
        given_clean = given.replace("-", "").lower()
        
        # Extract given name pattern
        expected_given = failure["expected"][1:]  # Skip surname
        
        if given_clean not in given_name_patterns:
            given_name_patterns[given_clean] = []
        given_name_patterns[given_clean].append({
            "korean": expected_given,
            "romanized": given,
            "full_name": failure["name"]
        })
        
        # Track character substitutions
        issue = failure["issue"]
        if "→" in issue:
            correct, wrong = issue.split("→")
            if correct not in character_substitutions:
                character_substitutions[correct] = set()
            character_substitutions[correct].add(wrong)

print("=== GIVEN NAME PATTERNS ===")
for pattern, instances in given_name_patterns.items():
    print(f"{pattern}: {instances[0]['korean']} ({len(instances)} instances)")

print("\n=== CHARACTER SUBSTITUTION PATTERNS ===")
for correct, wrongs in character_substitutions.items():
    print(f"{correct} is being mistaken for: {', '.join(wrongs)}")

print("\n=== SAFE FIX RECOMMENDATIONS ===")
print("1. Add two-character given name patterns with high weights:")
for pattern, instances in given_name_patterns.items():
    korean = instances[0]['korean']
    if len(korean) == 2:  # Two-character given names
        print(f"   {korean},{pattern},-6.0,GN,G")

print("\n2. Add specific character overrides in given name position:")
for correct in character_substitutions:
    print(f"   {correct} needs stronger weight in given name position")

print("\n3. Consider full-name overrides for persistent failures:")
for failure in diverse_failures[:5]:  # Top 5 most important
    name_parts = failure["name"].split(", ")
    if len(name_parts) == 2:
        surname, given = name_parts
        full_romanized = surname.lower() + given.replace("-", "").lower()
        print(f"   {failure['expected']},{full_romanized},-8.0")