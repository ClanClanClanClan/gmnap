#!/usr/bin/env python3
"""
Complete failure extraction for Korean linguistics expert
Extracts all 42 failing cases with detailed analysis for systematic fixes
"""

import json
import pathlib
import sys
import unicodedata
from collections import defaultdict

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))
# from converter import eng2kor, kor2eng


def norm(s):
    """Normalize string for comparison"""
    s = s.replace(",", "").replace("-", " ")
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))


def dice(a, b):
    """Calculate Dice coefficient"""
    a, b = set(zip(a, a[1:])), set(zip(b, b[1:]))
    return 2 * len(a & b) / (len(a) + len(b) or 1)


def find_hangul(variants):
    """Find Hangul variant from list"""
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


def character_by_character_analysis(original, roundtrip):
    """Analyze character-by-character differences"""
    orig_chars = list(
        original.lower().replace(" ", "").replace(",", "").replace("-", "")
    )
    round_chars = list(roundtrip.lower().replace(" ", ""))

    differences = []

    # Simple alignment analysis
    i, j = 0, 0
    while i < len(orig_chars) and j < len(round_chars):
        if orig_chars[i] == round_chars[j]:
            i += 1
            j += 1
        else:
            # Find next matching character
            match_found = False
            for k in range(j + 1, min(j + 4, len(round_chars))):
                if k < len(round_chars) and orig_chars[i] == round_chars[k]:
                    # Extra characters in roundtrip
                    extra = "".join(round_chars[j:k])
                    differences.append(f"Extra '{extra}' before '{orig_chars[i]}'")
                    j = k
                    match_found = True
                    break

            if not match_found:
                for k in range(i + 1, min(i + 4, len(orig_chars))):
                    if (
                        k < len(orig_chars)
                        and j < len(round_chars)
                        and orig_chars[k] == round_chars[j]
                    ):
                        # Missing characters in roundtrip
                        missing = "".join(orig_chars[i:k])
                        differences.append(
                            f"Missing '{missing}' before '{orig_chars[k]}'"
                        )
                        i = k
                        match_found = True
                        break

            if not match_found:
                # Substitution
                differences.append(
                    f"'{orig_chars[i]}' → '{round_chars[j] if j < len(round_chars) else 'END'}'"
                )
                i += 1
                j += 1

    # Handle remaining characters
    if i < len(orig_chars):
        missing = "".join(orig_chars[i:])
        differences.append(f"Missing ending: '{missing}'")

    if j < len(round_chars):
        extra = "".join(round_chars[j:])
        differences.append(f"Extra ending: '{extra}'")

    return differences


def extract_all_failures():
    """Extract complete details for all failing cases"""
    print("🔍 EXTRACTING ALL FAILURE CASES FOR EXPERT ANALYSIS")
    print("=" * 60)

    data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))
    failures = []
    successes = 0

    print(f"Loading test data... Found {len(data)} entries")

    for k, v in data.items():
        rr = v.get("CanonicalLatin")
        ko_exp = find_hangul(v.get("AllCommonVariants", []))

        if not rr or not ko_exp:
            continue

        # Test conversion
        ko = eng2kor(rr)
        if ko != ko_exp:
            failures.append(
                {
                    "id": k,
                    "canonical_english": rr,
                    "expected_korean": ko_exp,
                    "actual_korean": ko,
                    "roundtrip_english": None,
                    "dice_score": None,
                    "issue_type": "conversion_failed",
                    "analysis": f'Conversion failed: "{rr}" → Expected: {ko_exp}, Got: {ko or "None"}',
                    "character_analysis": [],
                    "systematic_pattern": "conversion_failure",
                }
            )
            continue

        # Test roundtrip
        rr2 = kor2eng(ko, rr) or ""
        dice_score = dice(norm(rr), norm(rr2))

        if dice_score < 0.90:
            char_analysis = character_by_character_analysis(rr, rr2)

            # Determine systematic pattern
            pattern = categorize_failure_pattern(rr, rr2, char_analysis)

            failures.append(
                {
                    "id": k,
                    "canonical_english": rr,
                    "expected_korean": ko_exp,
                    "actual_korean": ko,
                    "roundtrip_english": rr2,
                    "dice_score": dice_score,
                    "issue_type": "roundtrip_low_dice",
                    "analysis": f'Low dice: "{rr}" → {ko} → "{rr2}" (dice: {dice_score:.3f})',
                    "character_analysis": char_analysis,
                    "systematic_pattern": pattern,
                }
            )
        else:
            successes += 1

    total = successes + len(failures)
    print(
        f"Analysis complete: {successes}/{total} = {successes/total*100:.2f}% success"
    )
    print(f"Found {len(failures)} failure cases for expert analysis")

    return failures


def categorize_failure_pattern(original, roundtrip, char_analysis):
    """Categorize failure into systematic pattern"""
    orig_lower = original.lower()
    round_lower = roundtrip.lower()

    # Check for specific patterns
    if "park" in orig_lower and "pak" in round_lower:
        return "consonant_park_pak"
    elif "jung" in orig_lower and "jeong" in round_lower:
        return "vowel_jung_jeong"
    elif "baek" in orig_lower and "baik" in round_lower:
        return "vowel_baek_baik"
    elif "june" in orig_lower and ("jun lee" in round_lower or "jun " in round_lower):
        return "segmentation_june"
    elif any("extra" in analysis.lower() for analysis in char_analysis):
        if any("ee" in analysis or "oo" in analysis for analysis in char_analysis):
            return "vowel_length_extra"
        else:
            return "extra_syllables_general"
    elif any("missing" in analysis.lower() for analysis in char_analysis):
        return "missing_syllables"
    elif len(round_lower.split()) > len(orig_lower.split()):
        return "over_segmentation"
    elif len(round_lower.split()) < len(orig_lower.split()):
        return "under_segmentation"
    else:
        return "other_systematic"


def analyze_systematic_patterns(failures):
    """Analyze systematic patterns across all failures"""
    print("\n📊 SYSTEMATIC PATTERN ANALYSIS")
    print("=" * 60)

    patterns = defaultdict(list)

    for failure in failures:
        pattern = failure["systematic_pattern"]
        patterns[pattern].append(failure)

    print("Pattern distribution:")
    for pattern, cases in sorted(
        patterns.items(), key=lambda x: len(x[1]), reverse=True
    ):
        print(f"\n{pattern}: {len(cases)} cases ({len(cases)/len(failures)*100:.1f}%)")

        # Show top examples
        for case in cases[:3]:
            if case["roundtrip_english"]:
                print(
                    f"  • {case['canonical_english']} → {case['roundtrip_english']} (dice: {case['dice_score']:.3f})"
                )
            else:
                print(f"  • {case['canonical_english']} → CONVERSION FAILED")

    return patterns


def generate_expert_recommendations(patterns):
    """Generate specific recommendations for each pattern"""
    print("\n🎯 EXPERT RECOMMENDATIONS BY PATTERN")
    print("=" * 60)

    recommendations = []

    for pattern, cases in sorted(
        patterns.items(), key=lambda x: len(x[1]), reverse=True
    ):
        rec = {
            "pattern": pattern,
            "case_count": len(cases),
            "priority": (
                "HIGH" if len(cases) >= 5 else "MEDIUM" if len(cases) >= 2 else "LOW"
            ),
            "examples": [],
            "suggested_fixes": [],
            "estimated_impact": len(cases),
        }

        # Add examples
        for case in cases[:3]:
            rec["examples"].append(
                {
                    "name": case["id"],
                    "issue": case["analysis"],
                    "char_analysis": case["character_analysis"],
                }
            )

        # Generate specific fix recommendations
        if pattern == "vowel_length_extra":
            rec["suggested_fixes"] = [
                "Check ㅣ (i) mappings - may be producing 'ee' instead of 'i'",
                "Review ㅓ (eo) mappings for vowel length consistency",
                "Examine compound vowel handling in FST weights",
            ]
        elif pattern == "consonant_park_pak":
            rec["suggested_fixes"] = [
                "Strengthen 박→'park' weight (already attempted, may need more)",
                "Further weaken 박→'pak' preference",
                "Check if other surnames have similar issues (백, 석, etc.)",
            ]
        elif pattern == "extra_syllables_general":
            rec["suggested_fixes"] = [
                "Review character-by-character processing in kor2eng function",
                "Check for over-segmentation in syllable boundaries",
                "Examine space insertion logic between Korean characters",
            ]
        elif pattern == "conversion_failed":
            rec["suggested_fixes"] = [
                "Add missing character mappings to CSV",
                "Check for encoding issues in Korean characters",
                "Review FST coverage for uncommon name elements",
            ]
        elif pattern == "segmentation_june":
            rec["suggested_fixes"] = [
                "Fix 준→'june' mapping weight (already attempted)",
                "Check compound name segmentation logic",
                "Review multi-syllable name boundary detection",
            ]
        else:
            rec["suggested_fixes"] = [
                f"Manual analysis needed for {pattern} cases",
                "Check character mappings for specific examples",
                "Review romanization standard alignment",
            ]

        recommendations.append(rec)

    # Display recommendations
    for rec in recommendations:
        print(f"\n{rec['pattern'].upper()} - {rec['priority']} PRIORITY")
        print(
            f"Cases: {rec['case_count']} | Estimated Impact: +{rec['estimated_impact']} cases"
        )

        print("Examples:")
        for ex in rec["examples"]:
            print(f"  • {ex['name']}: {ex['issue']}")
            for char_issue in ex["char_analysis"][:2]:  # Show first 2 character issues
                print(f"    - {char_issue}")

        print("Suggested Fixes:")
        for fix in rec["suggested_fixes"]:
            print(f"  → {fix}")

    return recommendations


def save_expert_analysis(failures, patterns, recommendations):
    """Save complete analysis for expert review"""
    analysis = {
        "timestamp": "2025-07-31T08:00:00Z",
        "summary": {
            "total_failures": len(failures),
            "target_fixes_needed": 19,  # For 97% compliance
            "performance_gap": "2.73%",
        },
        "failures": failures,
        "patterns": {pattern: len(cases) for pattern, cases in patterns.items()},
        "recommendations": recommendations,
    }

    with open("expert_failure_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    print("\n💾 Complete analysis saved to: expert_failure_analysis.json")
    print(
        f"📊 Total data points: {len(failures)} failures across {len(patterns)} patterns"
    )


def main():
    """Run complete failure extraction and analysis"""
    print("🎯 KOREAN LINGUISTICS EXPERT - FAILURE ANALYSIS")
    print("Objective: Extract all failure cases for systematic linguistic fixes")
    print("=" * 80)

    # Extract all failures
    failures = extract_all_failures()

    if not failures:
        print("❌ No failures found - something may be wrong with the analysis")
        return

    # Analyze patterns
    patterns = analyze_systematic_patterns(failures)

    # Generate recommendations
    recommendations = generate_expert_recommendations(patterns)

    # Save complete analysis
    save_expert_analysis(failures, patterns, recommendations)

    print("\n" + "=" * 80)
    print("🎯 EXPERT ANALYSIS COMPLETE")
    print("=" * 80)
    print("Ready for linguistic expert review:")
    print(f"  • {len(failures)} failure cases analyzed")
    print(f"  • {len(patterns)} systematic patterns identified")
    print("  • Complete technical recommendations provided")
    print("  • Analysis saved to expert_failure_analysis.json")

    print(
        f"\nNext step: Apply linguistic expertise to top {min(5, len(patterns))} patterns"
    )
    print("Expected result: Close 2.73% performance gap to achieve ≥97% v7 compliance")


if __name__ == "__main__":
    main()
