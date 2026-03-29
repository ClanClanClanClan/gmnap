#!/usr/bin/env python3
"""
Detailed failure analysis - get complete list of failing cases
"""

import sys

sys.path.append("src")

# from converter import eng2kor, kor2eng
import json


def load_test_data():
    """Load the math test dataset"""
    with open("data/mathematician_names.json", "r") as f:
        return json.load(f)


def analyze_all_failures():
    """Analyze all 42 failing cases in detail"""
    print("🔍 DETAILED FAILURE ANALYSIS")

    data = load_test_data()
    failures = []
    successes = 0

    for i, entry in enumerate(data):
        eng_name = entry["name"]
        expected_kor = entry["korean"]

        # Test conversion
        try:
            converted_kor = eng2kor(eng_name)
            if converted_kor is None:
                failures.append(
                    {
                        "index": i,
                        "name": eng_name,
                        "expected": expected_kor,
                        "converted": None,
                        "issue": "conversion_failed",
                    }
                )
                continue

            # Test roundtrip
            roundtrip_eng = kor2eng(converted_kor, eng_name)
            if roundtrip_eng is None:
                failures.append(
                    {
                        "index": i,
                        "name": eng_name,
                        "expected": expected_kor,
                        "converted": converted_kor,
                        "roundtrip": None,
                        "issue": "roundtrip_failed",
                    }
                )
                continue

            # Check Dice coefficient
            dice = calculate_dice(
                eng_name.lower().replace(" ", ""),
                roundtrip_eng.lower().replace(" ", ""),
            )

            if dice < 0.90:
                failures.append(
                    {
                        "index": i,
                        "name": eng_name,
                        "expected": expected_kor,
                        "converted": converted_kor,
                        "roundtrip": roundtrip_eng,
                        "dice": dice,
                        "issue": "low_dice",
                    }
                )
            else:
                successes += 1

        except Exception as e:
            failures.append(
                {
                    "index": i,
                    "name": eng_name,
                    "expected": expected_kor,
                    "error": str(e),
                    "issue": "exception",
                }
            )

    print(f"Success: {successes}/733 ({successes/733*100:.2f}%)")
    print(f"Failures: {len(failures)}/733 ({len(failures)/733*100:.2f}%)")

    return failures


def calculate_dice(str1, str2):
    """Calculate Dice coefficient"""
    if not str1 or not str2:
        return 0.0

    # Create bigrams
    bigrams1 = set(str1[i : i + 2] for i in range(len(str1) - 1))
    bigrams2 = set(str2[i : i + 2] for i in range(len(str2) - 1))

    if not bigrams1 and not bigrams2:
        return 1.0
    if not bigrams1 or not bigrams2:
        return 0.0

    intersection = len(bigrams1 & bigrams2)
    return 2.0 * intersection / (len(bigrams1) + len(bigrams2))


def categorize_failures(failures):
    """Categorize failures by type and pattern"""
    print("\\n📊 FAILURE CATEGORIZATION")

    categories = {
        "conversion_failed": [],
        "roundtrip_failed": [],
        "low_dice": [],
        "exception": [],
    }

    for failure in failures:
        categories[failure["issue"]].append(failure)

    for category, cases in categories.items():
        print(f"\\n{category}: {len(cases)} cases")
        for case in cases[:5]:  # Show first 5
            if "dice" in case:
                print(
                    f"  {case['name']} → {case['converted']} → {case['roundtrip']} (dice: {case['dice']:.3f})"
                )
            elif "converted" in case:
                print(f"  {case['name']} → {case['converted']} (failed roundtrip)")
            else:
                print(f"  {case['name']} → FAILED")

    return categories


def analyze_low_dice_patterns(low_dice_cases):
    """Analyze patterns in low dice coefficient cases"""
    print("\\n🎯 LOW DICE PATTERN ANALYSIS")

    patterns = {
        "park_pak": 0,
        "jeong_jung": 0,
        "baek_baik": 0,
        "extra_syllables": 0,
        "missing_syllables": 0,
        "vowel_shifts": 0,
        "consonant_shifts": 0,
    }

    for case in low_dice_cases:
        original = case["name"].lower()
        roundtrip = case.get("roundtrip", "").lower()

        # Check specific patterns
        if "park" in original and "pak" in roundtrip:
            patterns["park_pak"] += 1
        elif "jung" in original and "jeong" in roundtrip:
            patterns["jeong_jung"] += 1
        elif "baek" in original and "baik" in roundtrip:
            patterns["baek_baik"] += 1
        elif len(roundtrip.split()) > len(original.split()):
            patterns["extra_syllables"] += 1
        elif len(roundtrip.split()) < len(original.split()):
            patterns["missing_syllables"] += 1

    print("Identified patterns:")
    for pattern, count in patterns.items():
        if count > 0:
            print(f"  {pattern}: {count} cases")

    return patterns


def suggest_specific_fixes(patterns, failures):
    """Suggest specific weight adjustments based on patterns"""
    print("\\n🔧 SPECIFIC FIXES NEEDED")

    fixes = []

    if patterns.get("park_pak", 0) > 0:
        fixes.append(
            {
                "mapping": ("박", "park", "-1.2"),
                "rationale": f"Fix {patterns['park_pak']} park→pak cases",
                "impact": f"+{patterns['park_pak']} cases",
            }
        )

    if patterns.get("jeong_jung", 0) > 0:
        fixes.append(
            {
                "mapping": ("정", "jeong", "-1.0"),
                "rationale": f"Fix {patterns['jeong_jung']} jung→jeong cases",
                "impact": f"+{patterns['jeong_jung']} cases",
            }
        )

    if patterns.get("baek_baik", 0) > 0:
        fixes.append(
            {
                "mapping": ("백", "baek", "-1.0"),
                "rationale": f"Fix {patterns['baek_baik']} baek→baik cases",
                "impact": f"+{patterns['baek_baik']} cases",
            }
        )

    # Look at conversion failures
    conversion_failures = [f for f in failures if f["issue"] == "conversion_failed"]
    if len(conversion_failures) > 0:
        print("\\nConversion failures need new mappings:")
        for case in conversion_failures[:5]:
            print(f"  {case['name']} → {case['expected']}")

    print("\\nRecommended weight adjustments:")
    total_impact = 0
    for fix in fixes:
        hangul, roman, weight = fix["mapping"]
        print(f"  {hangul},{roman},{weight} - {fix['rationale']}")
        total_impact += int(fix["impact"].split("+")[1].split(" ")[0])

    print(f"\\nEstimated impact: +{total_impact} cases")
    projected = (691 + total_impact) / 733 * 100
    print(f"Projected accuracy: {projected:.2f}%")

    return fixes


def main():
    """Run detailed failure analysis"""
    print("🎯 DETAILED FAILURE ANALYSIS FOR V7 COMPLIANCE")
    print("=" * 60)

    failures = analyze_all_failures()
    categories = categorize_failures(failures)

    if "low_dice" in categories:
        patterns = analyze_low_dice_patterns(categories["low_dice"])
        suggest_specific_fixes(patterns, failures)

    print("\\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("Apply the suggested weight adjustments to close the performance gap")


if __name__ == "__main__":
    main()
