#!/usr/bin/env python3
"""
Targeted fixes for v7 performance gap based on actual failure analysis
"""

import csv
import pathlib
import sys
import unicodedata
from collections import defaultdict

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
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


def analyze_all_failures():
    """Get complete list of actual failures"""
    print("🔍 COMPLETE FAILURE ANALYSIS")

    data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))

    failures = []
    successes = 0

    for k, v in data.items():
        rr = v.get("CanonicalLatin")
        ko_exp = find_hangul(v.get("AllCommonVariants", []))

        if not rr or not ko_exp:
            continue

        ko = eng2kor(rr)
        if ko != ko_exp:
            failures.append(
                {
                    "name": k,
                    "canonical": rr,
                    "expected_korean": ko_exp,
                    "actual_korean": ko,
                    "issue": "eng_to_kor_mismatch",
                }
            )
            continue

        rr2 = kor2eng(ko, rr) or ""
        dice_score = dice(norm(rr), norm(rr2))

        if dice_score < 0.90:
            failures.append(
                {
                    "name": k,
                    "canonical": rr,
                    "expected_korean": ko_exp,
                    "actual_korean": ko,
                    "roundtrip": rr2,
                    "dice": dice_score,
                    "issue": "low_dice_roundtrip",
                }
            )
            continue

        successes += 1

    total = successes + len(failures)
    print(f"Success: {successes}/{total} ({successes/total*100:.2f}%)")
    print(f"Failures: {len(failures)}/{total} ({len(failures)/total*100:.2f}%)")

    return failures, successes, total


def categorize_roundtrip_failures(failures):
    """Analyze roundtrip failure patterns"""
    print("\\n🎯 ROUNDTRIP FAILURE PATTERNS")

    roundtrip_failures = [f for f in failures if f["issue"] == "low_dice_roundtrip"]

    patterns = defaultdict(list)

    for failure in roundtrip_failures:
        original = failure["canonical"].lower()
        roundtrip = failure["roundtrip"].lower()

        # Identify specific patterns
        if "park" in original and "pak" in roundtrip:
            patterns["park_to_pak"].append(failure)
        elif "jung" in original and "jeong" in roundtrip:
            patterns["jung_to_jeong"].append(failure)
        elif "baek" in original and "baik" in roundtrip:
            patterns["baek_to_baik"].append(failure)
        elif "june" in original and ("jun lee" in roundtrip or "jun " in roundtrip):
            patterns["june_segmentation"].append(failure)
        elif len(roundtrip.split()) > len(original.split()):
            patterns["extra_syllables"].append(failure)
        else:
            patterns["other_vowel_consonant"].append(failure)

    print("Identified failure patterns:")
    for pattern_name, cases in patterns.items():
        print(f"\\n{pattern_name}: {len(cases)} cases")
        for case in cases[:3]:  # Show first 3
            print(
                f"  {case['canonical']} → {case['roundtrip']} (dice: {case['dice']:.3f})"
            )

    return patterns


def apply_targeted_weight_fixes(patterns):
    """Apply specific weight fixes based on failure patterns"""
    print("\\n🔧 APPLYING TARGETED WEIGHT FIXES")

    # Create targeted fixes based on patterns
    fixes = []

    if "park_to_pak" in patterns and len(patterns["park_to_pak"]) > 0:
        fixes.append(
            ("박", "park", "-1.5", f"Fix {len(patterns['park_to_pak'])} park→pak cases")
        )
        fixes.append(("박", "pak", "0.5", "Reduce pak preference"))

    if "jung_to_jeong" in patterns and len(patterns["jung_to_jeong"]) > 0:
        fixes.append(
            (
                "정",
                "jeong",
                "-1.2",
                f"Fix {len(patterns['jung_to_jeong'])} jung→jeong cases",
            )
        )
        fixes.append(("정", "jung", "0.3", "Reduce jung preference"))

    if "baek_to_baik" in patterns and len(patterns["baek_to_baik"]) > 0:
        fixes.append(
            (
                "백",
                "baek",
                "-1.2",
                f"Fix {len(patterns['baek_to_baik'])} baek→baik cases",
            )
        )
        fixes.append(("백", "baik", "0.5", "Reduce baik preference"))

    if "june_segmentation" in patterns and len(patterns["june_segmentation"]) > 0:
        fixes.append(
            (
                "준",
                "june",
                "-1.0",
                f"Fix {len(patterns['june_segmentation'])} June segmentation cases",
            )
        )

    # Read current CSV
    rows = []
    with open("resources/rr_syllable_map.csv", "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    changes_made = 0

    # Apply fixes
    for hangul, roman, new_weight, rationale in fixes:
        print(f"  Applying: {hangul},{roman},{new_weight} - {rationale}")

        # Find and update existing mapping
        found = False
        for i, row in enumerate(rows):
            if len(row) >= 3 and row[0] == hangul and row[1] == roman:
                old_weight = row[2]
                rows[i][2] = new_weight
                print(
                    f"    Updated Line {i+1}: {hangul},{roman},{old_weight} → {hangul},{roman},{new_weight}"
                )
                changes_made += 1
                found = True
                break

        if not found:
            # Add new mapping
            rows.append([hangul, roman, new_weight])
            print(f"    Added new: {hangul},{roman},{new_weight}")
            changes_made += 1

    # Write updated CSV
    if changes_made > 0:
        with open(
            "resources/rr_syllable_map.csv", "w", encoding="utf-8", newline=""
        ) as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

        print(f"\\n✅ Applied {changes_made} targeted weight fixes")
    else:
        print("\\n⚠️  No changes made")

    return changes_made


def test_performance_after_fixes():
    """Test performance after applying targeted fixes"""
    print("\\n📊 TESTING PERFORMANCE AFTER FIXES")

    # Need to rebuild FSTs first
    import subprocess

    print("Rebuilding FSTs...")
    subprocess.run(["python3", "scripts/build_fsts_multi.py"], check=True)

    # Test performance
    failures, successes, total = analyze_all_failures()
    accuracy = successes / total * 100

    print(f"\\nNew performance: {successes}/{total} = {accuracy:.2f}%")

    if accuracy >= 97.0:
        print("✅ ACHIEVED V7 TARGET!")
    else:
        gap = 97.0 - accuracy
        print(f"⚠️  Still {gap:.2f}% short of v7 target")

    return accuracy


def main():
    """Apply targeted fixes to close v7 performance gap"""
    print("🎯 TARGETED FIXES FOR V7 PERFORMANCE COMPLIANCE")
    print("=" * 60)

    # Analyze current failures
    failures, successes, total = analyze_all_failures()

    # Focus on roundtrip failures (main issue)
    patterns = categorize_roundtrip_failures(failures)

    # Apply targeted fixes
    changes = apply_targeted_weight_fixes(patterns)

    if changes > 0:
        # Test new performance
        new_accuracy = test_performance_after_fixes()

        print("\\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Original: {successes}/{total} = {successes/total*100:.2f}%")
        print(f"After fixes: {new_accuracy:.2f}%")
        print(f"Changes applied: {changes}")

        if new_accuracy >= 97.0:
            print("\\n🎉 V7 PERFORMANCE TARGET ACHIEVED!")
        else:
            print(
                f"\\n⚠️ Still {97.0 - new_accuracy:.2f}% short - may need additional analysis"
            )
    else:
        print("\\n❌ No targeted fixes could be applied")


if __name__ == "__main__":
    main()
