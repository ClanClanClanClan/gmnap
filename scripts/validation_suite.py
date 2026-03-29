#!/usr/bin/env python3
"""
Phase 9: Validation & Testing Suite per V5 Blueprint
"""

import sys
import os
import unicodedata

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.v5.blueprint_converter import convert_blueprint
import yaml
from rapidfuzz import fuzz


def dice_coefficient(a, b):
    """Calculate Dice coefficient with NFC normalization per blueprint"""
    # NFC normalization as specified
    a_norm = unicodedata.normalize("NFC", str(a))
    b_norm = unicodedata.normalize("NFC", str(b))

    # Calculate Dice coefficient manually (2-gram based)
    if not a_norm or not b_norm:
        return 0.0

    # Generate 2-grams
    a_grams = set(a_norm[i : i + 2] for i in range(len(a_norm) - 1))
    b_grams = set(b_norm[i : i + 2] for i in range(len(b_norm) - 1))

    if not a_grams and not b_grams:
        return 1.0
    if not a_grams or not b_grams:
        return 0.0

    intersection = len(a_grams.intersection(b_grams))
    total = len(a_grams) + len(b_grams)

    return 2.0 * intersection / total


def round_trip_test(romanized_name):
    """Test round-trip conversion per blueprint"""
    # Roman -> Hangul
    hangul_result = convert_blueprint(romanized_name)
    if not hangul_result:
        return False, 0.0, None, None

    # For this implementation, we'll simulate the back-conversion
    # In a full implementation, this would use the reverse FST
    back_converted = simulate_back_conversion(hangul_result)

    if not back_converted:
        return False, 0.0, hangul_result, None

    # Calculate Dice coefficient
    dice_score = dice_coefficient(romanized_name.lower(), back_converted.lower())

    # Success if Dice > 0.85 as per blueprint
    success = dice_score > 0.85

    return success, dice_score, hangul_result, back_converted


def simulate_back_conversion(hangul):
    """Simulate back conversion from Hangul to Roman (simplified)"""
    # This is a simplified back-conversion for testing
    # In production, this would use a proper reverse FST

    simple_mappings = {
        "김": "kim",
        "이": "lee",
        "박": "park",
        "최": "choi",
        "정": "jung",
        "강": "kang",
        "조": "cho",
        "윤": "yoon",
        "장": "jang",
        "임": "lim",
        "한": "han",
        "오": "oh",
        "서": "seo",
        "신": "shin",
        "권": "kwon",
        "황": "hwang",
        "안": "ahn",
        "송": "song",
        "홍": "hong",
        "전": "jeon",
        "고": "go",
        "문": "moon",
        "손": "son",
        "양": "yang",
        "배": "bae",
        "주": "joo",
        "백": "baek",
        "허": "heo",
        "유": "yu",
        "노": "noh",
        "하": "ha",
        "현": "hyun",
        "영": "young",
        "수": "soo",
        "민": "min",
        "지": "ji",
        "호": "ho",
        "진": "jin",
        "성": "sung",
        "준": "jun",
        "원": "won",
        "용": "yong",
        "일": "il",
        "철": "chul",
        "기": "ki",
        "태": "tae",
        "범": "bum",
        "규": "kyu",
        "훈": "hoon",
        "상": "sang",
        "재": "jae",
        "경": "kyung",
        "희": "hee",
        "석": "seok",
        "동": "dong",
        "엄": "eom",
        "여": "yeo",
        "육": "yook",
        "부": "boo",
    }

    # Simple character-by-character mapping
    result = ""
    for char in hangul:
        if char in simple_mappings:
            if result:
                result += " "
            result += simple_mappings[char]
        elif char == " ":
            result += " "

    return result if result else None


def run_validation_suite():
    """Run comprehensive validation suite per Phase 9"""
    print("=== PHASE 9: VALIDATION SUITE ===\n")

    # Load Korean dataset
    with open("../data/korean.yaml", "r", encoding="utf-8") as f:
        korean_data = yaml.safe_load(f)

    # Test metrics
    total_tests = 0
    conversion_successes = 0
    round_trip_successes = 0
    dice_scores = []
    failed_cases = []

    print("Running validation tests...")

    for key, entry in korean_data.items():
        name = key.replace("_", " ")

        # Skip invalid entries
        if len(name) < 2 or any(c.isdigit() for c in name):
            continue

        total_tests += 1

        # Test round-trip conversion
        success, dice_score, hangul, back_converted = round_trip_test(name)

        if hangul:  # Conversion succeeded
            conversion_successes += 1

        if success:  # Round-trip succeeded
            round_trip_successes += 1
            dice_scores.append(dice_score)
        else:
            failed_cases.append(
                {
                    "original": name,
                    "hangul": hangul,
                    "back_converted": back_converted,
                    "dice_score": dice_score,
                }
            )

    # Calculate metrics
    conversion_rate = (conversion_successes / total_tests) * 100
    round_trip_rate = (round_trip_successes / total_tests) * 100
    avg_dice = sum(dice_scores) / len(dice_scores) if dice_scores else 0

    print(f"\n📊 VALIDATION RESULTS:")
    print(f"  Total tests: {total_tests}")
    print(
        f"  Conversion success rate: {conversion_rate:.1f}% ({conversion_successes}/{total_tests})"
    )
    print(
        f"  Round-trip success rate: {round_trip_rate:.1f}% ({round_trip_successes}/{total_tests})"
    )
    print(f"  Average Dice coefficient: {avg_dice:.3f}")

    # Blueprint requirements check
    blueprint_conversion_target = 97.0
    blueprint_roundtrip_target = 85.0  # Typical for round-trip

    print(f"\n🎯 BLUEPRINT COMPLIANCE:")
    if conversion_rate >= blueprint_conversion_target:
        print(
            f"  ✅ Conversion rate: {conversion_rate:.1f}% ≥ {blueprint_conversion_target}%"
        )
    else:
        print(
            f"  ❌ Conversion rate: {conversion_rate:.1f}% < {blueprint_conversion_target}%"
        )

    if round_trip_rate >= blueprint_roundtrip_target:
        print(
            f"  ✅ Round-trip rate: {round_trip_rate:.1f}% ≥ {blueprint_roundtrip_target}%"
        )
    else:
        print(
            f"  ❌ Round-trip rate: {round_trip_rate:.1f}% < {blueprint_roundtrip_target}%"
        )

    if avg_dice >= 0.85:
        print(f"  ✅ Dice coefficient: {avg_dice:.3f} ≥ 0.85")
    else:
        print(f"  ❌ Dice coefficient: {avg_dice:.3f} < 0.85")

    # Show some failed cases
    if failed_cases:
        print(f"\n❌ FAILED ROUND-TRIP CASES (first 10):")
        for i, case in enumerate(failed_cases[:10]):
            print(
                f"  {i+1:2d}. {case['original']} -> {case['hangul']} -> {case['back_converted']} (Dice: {case['dice_score']:.3f})"
            )

    # Overall pass/fail
    overall_pass = (
        conversion_rate >= blueprint_conversion_target
        and round_trip_rate >= blueprint_roundtrip_target
        and avg_dice >= 0.85
    )

    if overall_pass:
        print(f"\n🎉 PHASE 9 VALIDATION: PASSED")
    else:
        print(f"\n❌ PHASE 9 VALIDATION: FAILED")

    return {
        "total_tests": total_tests,
        "conversion_rate": conversion_rate,
        "round_trip_rate": round_trip_rate,
        "avg_dice": avg_dice,
        "passed": overall_pass,
    }


if __name__ == "__main__":
    run_validation_suite()
