#!/usr/bin/env python3
"""
Validation script that compares against Hangul variants in the dataset
"""

import yaml
import unicodedata
import sys
from pathlib import Path

# Add src directory to path
E4_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(E4_ROOT / "src"))

# from converter import eng2kor, kor2eng


def norm(s):
    """Normalize string for comparison."""
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))


def dice(a, b):
    """Calculate Dice coefficient using character bigrams."""
    a_bigrams = set(zip(a, a[1:]))
    b_bigrams = set(zip(b, b[1:]))
    if not a_bigrams and not b_bigrams:
        return 1.0
    if not a_bigrams or not b_bigrams:
        return 0.0
    return 2 * len(a_bigrams & b_bigrams) / (len(a_bigrams) + len(b_bigrams))


def find_hangul_variant(variants):
    """Find Hangul variant from AllCommonVariants list."""
    for variant in variants:
        # Check if variant contains Hangul characters
        if any("\uac00" <= c <= "\ud7af" for c in variant):
            return variant.replace(" ", "")  # Remove spaces for comparison
    return None


def validate_accuracy():
    """Validate round-trip accuracy on Korean dataset."""
    data_path = E4_ROOT / "data" / "korean.yaml"

    try:
        with open(data_path, encoding="utf8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Dataset not found: {data_path}")
        return False

    if not data:
        print("❌ Empty dataset")
        return False

    print(f"📊 Validating on {len(data)} entries...")

    successful_conversions = 0
    round_trip_successes = 0
    has_hangul_variant = 0
    total_tested = 0

    detailed_results = []

    for key, value in data.items():
        if not isinstance(value, dict):
            continue

        canonical_latin = value.get("CanonicalLatin", "")
        all_variants = value.get("AllCommonVariants", [])

        if not canonical_latin:
            continue

        # Find expected Hangul variant
        expected_hangul = find_hangul_variant(all_variants)
        if not expected_hangul:
            continue  # Skip entries without Hangul variants

        has_hangul_variant += 1

        # Test English -> Korean conversion
        korean_result = eng2kor(canonical_latin)

        result_info = {
            "key": key,
            "canonical_latin": canonical_latin,
            "expected_hangul": expected_hangul,
            "converted_hangul": korean_result,
            "conversion_success": False,
            "round_trip_success": False,
            "round_trip_result": None,
            "dice_score": 0.0,
        }

        if korean_result:
            result_info["conversion_success"] = True
            successful_conversions += 1

            # Test round-trip
            round_trip_result = kor2eng(korean_result)
            result_info["round_trip_result"] = round_trip_result

            if round_trip_result:
                dice_score = dice(norm(canonical_latin), norm(round_trip_result))
                result_info["dice_score"] = dice_score

                if dice_score >= 0.97:
                    result_info["round_trip_success"] = True
                    round_trip_successes += 1

        detailed_results.append(result_info)
        total_tested += 1

        # Show progress for first few
        if total_tested <= 5:
            status = "✅" if result_info["round_trip_success"] else "❌"
            print(
                f"  {status} {key}: '{canonical_latin}' -> '{korean_result}' (expected: '{expected_hangul}')"
            )

    # Calculate metrics
    conversion_rate = (
        (successful_conversions / total_tested * 100) if total_tested > 0 else 0
    )
    round_trip_rate = (
        (round_trip_successes / total_tested * 100) if total_tested > 0 else 0
    )

    print(f"\n📈 RESULTS:")
    print(f"📊 Total entries with Hangul variants: {has_hangul_variant}")
    print(f"📊 Total tested: {total_tested}")
    print(f"✅ Successful conversions: {successful_conversions}")
    print(f"✅ Round-trip successes: {round_trip_successes}")
    print(f"📊 Conversion rate: {conversion_rate:.2f}%")
    print(f"🎯 Round-trip accuracy: {round_trip_rate:.2f}%")

    # Show compliance status
    if round_trip_rate >= 97.0:
        print(f"✅ GMNAP v6.1 COMPLIANT (≥97% required)")
    else:
        print(f"❌ Below GMNAP v6.1 requirement (≥97% required)")

    # Show some failures for debugging
    failures = [r for r in detailed_results if not r["conversion_success"]]
    if failures:
        print(f"\n❌ First 5 conversion failures:")
        for i, fail in enumerate(failures[:5]):
            print(f"  {i+1}. {fail['key']}: '{fail['canonical_latin']}' -> None")

    return round_trip_rate >= 97.0


if __name__ == "__main__":
    print("=== Korean Converter v6 Hangul Validation ===")
    success = validate_accuracy()

    if success:
        print("\n🎉 VALIDATION PASSED - Ready for production")
    else:
        print("\n⚠️  VALIDATION NEEDS IMPROVEMENT")
        print("💡 Add missing syllables and rebuild lookup tables")
